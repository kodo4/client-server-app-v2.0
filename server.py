import argparse
import select
import socket
import sys
import json
import time

from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.server_log_config
from decos import log

LOGGER = logging.getLogger('server')


def arg_parser():
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    if not 1023 < listen_port < 65536:
        LOGGER.critical(
            f'Попытка запуска сервера с указанием неподходящего порта '
            f'{listen_port}. Допустимы адреса с 1024 до 65535'
        )
        sys.exit(1)

    return listen_address, listen_port


class Server:
    def __init__(self, listen_address, listen_port):
        self.addr = listen_address
        self.port = listen_port

        self.clients = []
        self.messages = []
        self.names = {}

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

    def main(self):
        self.init_socket()

        while True:
            # Ждём подключения, если тайсайт вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError as err:
                print(err.errno)
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
                            self.messages, client_with_message,
                            self.clients, self.names)
                    except:
                        LOGGER.info(
                            f'Клиент {client_with_message.getpeername()} '
                            f'отключился от сервера.')
                        self.clients.remove(client_with_message)
            for i in self.messages:
                try:
                    self.process_message(i, self.names, send_data_lst)
                except Exception:
                    LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]}'
                                f'была потеряна.')
                    self.clients.remove(self.names[i[DESTINATION]])
                    del self.names[i[DESTINATION]]
            self.messages.clear()

    def process_message(self, message, names, listen_socks):
        """Функция адресной отправки сообщения определённому клиенту. Принимает
        словарь сообщение, список зарегистрированых пользователей и слушающие
        сокеты. Ничего не возвращает."""
        if message[DESTINATION] in names and names[message[DESTINATION]] in \
                listen_socks:
            send_message(names[message[DESTINATION]], message)
            LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]}'
                        f'от пользователя {message[SENDER]}')
        elif message[DESTINATION] in names and names[message[DESTINATION]] not in \
                listen_socks:
            raise ConnectionError
        else:
            LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере,'
                f'отправка сообщения невозможна')
        LOGGER.info(f'Разбор сообщения от клиента: {message}')

    def process_client_message(self, message, messages_list, client, clients, names):
        """
        Обработчик сообщений от клиентов, принимает словарь -
        сообщение от клиента, проверяет корректность,
        возвращает словарь-ответ для клиента
        """
        LOGGER.info(f'Разбор сообщения от клиента: {message}')
        if ACTION in message and message[
            ACTION] == PRESENCE and TIME in message \
                and USER in message:
            if message[USER][ACCOUNT_NAME] not in names.keys():
                names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                clients.remove(client)
                client.close()
            return
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:

            messages_list.append(message)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in \
                message:
            clients.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            return
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def main():
    """
    Загрузка параметров командной строки, если нет параметров,
    то задаём значения по умолчанию.
    Сначала обрабатываем порт:
    server.py -p 8888 -a 127.0.0.1
    """
    listen_address, listen_port = arg_parser()

    server = Server(listen_address, listen_port)
    server.main()


if __name__ == '__main__':
    main()
