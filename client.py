import argparse
import sys
import json
import socket
import time
import threading
from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.client_log_config
from decos import log

LOGGER = logging.getLogger('client')


@log
def create_exit_message(account_name):
    """Функция создаёт словарь с сообщение о выходе"""
    return {
        ACTION: EXIT,
        TIME: time.time(),
        ACCOUNT_NAME: account_name
    }


@log
def message_from_server(sock, my_username):
    """Функция обработчик сообщений поступающих с сервера"""
    while True:
        try:
            message = get_message(sock)
            if ACTION in message and message[ACTION] == MESSAGE and \
                    SENDER in message and DESTINATION in message\
                    and MESSAGE_TEXT in message and message[DESTINATION] == \
                    my_username:
                print(f'Получено сообщение от пользователя '
                      f'{message[SENDER]}: \n{message[MESSAGE_TEXT]}')
                LOGGER.info(f'Получено сообщение от пользователя '
                      f'{message[SENDER]}: \n{message[MESSAGE_TEXT]}')
            else:
                LOGGER.error(f'Получено некорректное сообщение с сервера: '
                             f'{message}')
        except (OSError, ConnectionError, ConnectionAbortedError,
                ConnectionResetError, json.JSONDecodeError):
            LOGGER.critical(f'Потеряно соединение с сервером')
            break


@log
def create_message(sock, account_name='Guest'):
    """Функция запрашивает текст сообщения и возвращает его.
    Так же завершает работу при вводе подобной комманды"""
    to_user = input('Введите получателя сообщения: ')
    message = input('Введите сообщение для отправки: ')
    message_dict = {
        ACTION: MESSAGE,
        SENDER: account_name,
        DESTINATION: to_user,
        TIME: time.time(),
        MESSAGE_TEXT: message
    }
    LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    try:
        send_message(sock, message_dict)
        LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
    except Exception as e:
        print(e)
        LOGGER.critical('Потеряно соединение с сервером.')
        sys.exit(1)


@log
def user_interective(sock, username):
    """Функция взаимодействия с пользователем, запрашивает команды, отправляет
    сообщения"""
    print_help()
    while True:
        command = input('Введите команду: ')
        if command == 'message':
            create_message(sock, username)
        elif command == 'help':
            print_help()
        elif command == 'exit':
            send_message(sock, create_exit_message(username))
            print('Завершение соединения.')
            LOGGER.info('Завершения работы по команде пользователя')
            # Задержка необходима, чтобы успело уйти сообщение о выходе
            time.sleep(0.5)
            break
        else:
            print('Команда не распознана, попробуйте снова.')


@log
def create_presence(account_name='Guest'):
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


def print_help():
    """Функция вывода справочной информации"""
    print('Поддерживаемые команды:')
    print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
    print('help - вывести подсказки по командам')
    print('exit - выход из программы')


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
        # Если соединение с сервером установлено корректно,
        # запускаем клиентский процесс приёма сообщений
        receiver = threading.Thread(target=message_from_server,
                                    args=(transport, client_name))
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взимодействия с пользовтелем
        user_interface = threading.Thread(target=user_interective, args=(
            transport, client_name))
        user_interface.daemon = True
        user_interface.start()
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
