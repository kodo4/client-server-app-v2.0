import argparse
import sys
import json
import socket
import time
import threading
from metaclass import ClientVerify
from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.client_log_config
from decos import log
from database.client_db import ClientDatabase

LOGGER = logging.getLogger('client')

sock_lock = threading.Lock()
database_lock = threading.Lock()


class ClientSender(threading.Thread, metaclass=ClientVerify):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    # функция создаёт словарь с сообщением о выходе.
    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    # Функция запрашиваем кому отправить сообщение и само сообщение,
    # отправляет полученные данные на сервер
    def create_message(self):
        """Функция запрашивает текст сообщения и возвращает его.
        Так же завершает работу при вводе подобной комманды"""
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        with database_lock:
            if not self.database.check_user(to_user):
                LOGGER.error(f'Попытка отправить сообщение '
                             f'незарегистрированному получаетлю: {to_user}')
                return
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)
        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
            except Exception as e:
                print(e)
                LOGGER.critical('Потеряно соединение с сервером. На этапе '
                                'создания сообщения')
                exit(1)


    def run(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет
        сообщения"""
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except Exception as e:
                        print(e)
                        pass
                print('Завершение соединения.')
                LOGGER.info('Завершения работы по команде пользователя')
                # Задержка необходима, чтобы успело уйти сообщение о выходе
                time.sleep(1)
                break
            elif command == 'contacts':
                with database_lock:
                    contact_list = self.database.get_contacts()
                for contact in contact_list:
                    print(contact)
            elif command == 'edit':
                self.edit_contacts()
            elif command == 'history':
                self.print_history()
            else:
                print('Команда не распознана, попробуйте снова.')

    def print_help(self):
        """Функция вывода справочной информации"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - '
                    'просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=
                                                         self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} '
                          f'от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=
                                                         self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} '
                          f'от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]}, '
                          f'пользователю {message[1]}'
                          f'от {message[3]}:\n{message[2]}')

    def edit_contacts(self):
        ans = input('Для удаления введите del, для добавления add:')
        if ans == 'del':
            edit = input('Введите имя удаляемого контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    LOGGER.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            edit = input('Введите имя создаваемого контака: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except Exception as e:
                        LOGGER.error(f'Не удалость отпавить информацию на '
                                     f'сервер {e}.')


class ClientReader(threading.Thread, metaclass=ClientVerify):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        while True:
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)
                except OSError as err:
                    if err.errno:
                        LOGGER.critical(f'Потеряно соединение с сервером.')
                        break
                except (ConnectionError,
                        ConnectionAbortedError,
                        ConnectionResetError,
                        json.JSONDecodeError):
                    LOGGER.critical(f'Потеряно соединение с сервером.')
                    break
                else:
                    if ACTION in message and message[ACTION] == MESSAGE \
                            and SENDER in message \
                            and DESTINATION in message \
                            and MESSAGE_TEXT in message \
                            and message[DESTINATION] == self.account_name:
                        print(f'\n Получено сообщение от пользователя '
                              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER],
                                                           self.account_name,
                                                           message[MESSAGE_TEXT])
                            except Exception as e:
                                print(e)
                                LOGGER.error('Ошибка взаимодействия с базой данных')

                        LOGGER.info(f'Получено сообщение от пользователя '
                                    f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')


@log
def create_presence(account_name):
    """
    Функция генерирует запрос о присутствии клиента
    :param account_name:
    :return:
    """
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя '
                 f'{account_name}')
    return out


@log
def process_ans(message):
    """Функция разбирает ответ сервера"""
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            LOGGER.debug(f'Получен ответ от сервера {message}')
            return '200: OK'
        LOGGER.debug(f'Получен ответ от сервера {message}')
        return f'400: {message[ERROR]}'
    LOGGER.error(f'Ошибка полученного ответа от сервера {message}')
    raise ValueError


@log
def arg_parser():
    """Создаём парсер аргументов коммандной строки
    и читаем параметры, возвращаем 3 параметра"""
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if server_port < 1023 or server_port > 65536:
        LOGGER.critical(f'Порт {server_port} недопустим')
        sys.exit(1)

    return server_address, server_port, client_name


def contacts_list_request(sock, name):
    LOGGER.debug(f'Запрос контакт листа для пользователя {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    LOGGER.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    LOGGER.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ValueError


def add_contact(sock, username, contact):
    LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise Exception
    print('Удачное создание контакта.')


def user_list_request(sock, username):
    LOGGER.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise Exception


def remove_contact(sock, username, contact):
    LOGGER.debug(f'Удаление контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise Exception
    print('Удачное удаление')


def database_load(sock, database, username):
    try:
        users_list = user_list_request(sock, username)
    except Exception as e:
        LOGGER.error(f'Ошибка запроса списка известных пользователей {e}')
    else:
        database.add_users(users_list)

    try:
        contacts_list = contacts_list_request(sock, username)
    except Exception as e:
        LOGGER.error(f'Ошибка запроса списка пользователей {e}')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    """Загружаем параметры командной строки"""
    server_address, server_port, client_name = arg_parser()

    print(f'Консольный месенджер. Клиентский модуль. Имя пользователя:'
          f'{client_name}')
    if not client_name:
        client_name = input('Введите имя пользователя: ')

    LOGGER.info(f'Запущен клиент с параметрами: {server_address}, '
                f'{server_port}, {client_name}')

    # Инициализация сокета и обмен
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.settimeout(1)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_ans(get_message(transport))
        LOGGER.info(f'Установлено соединение с сервером {answer}')
        print('Установлено соединение с сервером')
    except (ValueError, json.JSONDecodeError):
        LOGGER.error('Не удалось декодировать сообщение сервера')
        sys.exit(1)
    except (ConnectionRefusedError, ConnectionError):
        LOGGER.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    else:
        # Инициализация БД
        database = ClientDatabase(client_name)
        database_load(transport, database, client_name)
        # Если соединение с сервером установлено корректно,

        # затем запускаем отправку сообщений и взимодействия с пользовтелем
        user_interface = ClientSender(client_name, transport, database)
        user_interface.daemon = True
        user_interface.start()

        # запускаем клиентский процесс приёма сообщений
        receiver = ClientReader(client_name, transport, database)
        receiver.daemon = True
        receiver.start()


        LOGGER.info('Запущены процессы')
        # основной цикл, если один из потоков завершён,
        # то значит или потеряно соединение или пользователь
        # ввел exit. Поскольку все события обрабатываются в потоках,
        # достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
