import argparse
import select
import socket
import sys
import json
import threading
import time

from descriptors import VerifyPort
from metaclass import ServerVerifier
from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.server_log_config
from decos import log
from database.server_db import ServerStorage

LOGGER = logging.getLogger('server')


def arg_parser():
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port


class Server(threading.Thread, metaclass=ServerVerifier):
    port = VerifyPort()

    def __init__(self, listen_address, listen_port, database):
        self.addr = listen_address
        self.port = listen_port
        self.database = database

        self.clients = []
        self.messages = []
        self.names = {}

        super().__init__()

    def init_socket(self):
        LOGGER.info(f'Запущен сервер, порт для подключений: {self.port},'
                    f'адрес с которого принимается подключения: {self.addr}'
                    f'Если адрес не указан, принимаются соединения с любых адресов'
                    )
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen()

    def run(self):
        self.init_socket()

        while True:
            # Ждём подключения, если тайсайт вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError as err:
                pass
            else:
                LOGGER.info(f'Установлено соединение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []

            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(
                        self.clients,
                        self.clients,
                        [], 0)
            except OSError:
                pass

            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(
                            get_message(client_with_message),
                            client_with_message)
                    except:
                        LOGGER.info(
                            f'Клиент {client_with_message.getpeername()} '
                            f'отключился от сервера.')
                        self.clients.remove(client_with_message)
            for i in self.messages:
                try:
                    self.process_message(i, send_data_lst)
                except Exception:
                    LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]}'
                                f'была потеряна.')
                    self.clients.remove(self.names[i[DESTINATION]])
                    del self.names[i[DESTINATION]]
            self.messages.clear()

    def process_message(self, message, listen_socks):
        """Функция адресной отправки сообщения определённому клиенту. Принимает
        словарь сообщение, список зарегистрированых пользователей и слушающие
        сокеты. Ничего не возвращает."""
        if message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] in \
                listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]}'
                        f'от пользователя {message[SENDER]}')
        elif message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] not in \
                listen_socks:
            raise ConnectionError
        else:
            LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере,'
                f'отправка сообщения невозможна')
        LOGGER.info(f'Разбор сообщения от клиента: {message}')

    def process_client_message(self, message, client):
        """
        Обработчик сообщений от клиентов, принимает словарь -
        сообщение от клиента, проверяет корректность,
        возвращает словарь-ответ для клиента
        """
        LOGGER.info(f'Разбор сообщения от клиента: {message}')
        if ACTION in message and message[
            ACTION] == PRESENCE and TIME in message \
                and USER in message:
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME],
                                         client_ip, client_port)
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in \
                message:
            LOGGER.info(f'До выхода {self.names}')
            LOGGER.info(f'Пользователь {message[ACCOUNT_NAME]} запросил выход')
            try:
                self.database.user_logout(message[ACCOUNT_NAME])
            except TypeError:
                print(f'Не удалось удалить из БД')
            else:
                LOGGER.info(f'Пользователь {message[ACCOUNT_NAME]} удалён из бд')
                self.clients.remove(self.names[message[ACCOUNT_NAME]])
                self.names[message[ACCOUNT_NAME]].close()
                del self.names[message[ACCOUNT_NAME]]
                LOGGER.info(f'После выхода {self.names}')
            return
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def help_text():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('history - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    """
    Загрузка параметров командной строки, если нет параметров,
    то задаём значения по умолчанию.
    Сначала обрабатываем порт:
    server.py -p 8888 -a 127.0.0.1
    """
    listen_address, listen_port = arg_parser()

    database = ServerStorage()

    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    help_text()

    while True:
        command = input('Введите команду: ')

        if command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен по "ip:port" - '
                      f'"{user[1]}:{user[2]}", подсоединился в {user[3]}')
        elif command == 'history':
            name = input('Введите имя пользователя для просмотра истории.'
                         'Если имя не выбрано, выведется весь список пользователей')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь {user[0]}, подключен по "ip:port" - '
                      f'"{user[2]}:{user[3]}", время входа: {user[1]}')
        elif command == 'exit':
            break
        elif command == 'help':
            help_text()
        else:
            print('Комманда не распознана')
            help_text()


if __name__ == '__main__':
    main()
