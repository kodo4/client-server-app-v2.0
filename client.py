import argparse
import sys
import json
import socket
import time
from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.client_log_config
from decos import log

LOGGER = logging.getLogger('client')


@log
def message_from_server(message):
    """Функция обработчик сообщений поступающих с сервера"""
    if ACTION in message and message[ACTION] == MESSAGE and \
        SENDER in message and MESSAGE_TEXT in message:
        print(f'Получено сообщение от пользователя '
              f'{message[SENDER]}: \n{message[MESSAGE_TEXT]}')
        LOGGER.info(f'Получено сообщение от пользователя '
              f'{message[SENDER]}: \n{message[MESSAGE_TEXT]}')
    else:
        LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')


@log
def create_message(sock, account_name='Guest'):
    """Функция запрашивает текст сообщения и возвращает его.
    Так же завершает работу при вводе подобной комманды"""
    message = input('Введите сообщение для отправки или "!!!" для завершения '
                    'работы: ')
    if message == '!!!':
        sock.close()
        LOGGER.info('Завершение работы по команде пользователя')
        sys.exit(1)
    message_dict = {
        ACTION: MESSAGE,
        TIME: time.time(),
        ACCOUNT_NAME: account_name,
        MESSAGE_TEXT: message
    }
    LOGGER.debug(f'Сформирован словарь сообщение для сервера: {message_dict}')
    return message_dict


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
    parser.add_argument('-m', '--mode', default='listen', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_mode = namespace.mode

    if server_port < 1024 or server_port > 65535:
        LOGGER.critical(f'Порт {server_port} недопустим')
        sys.exit(1)

    if client_mode not in ('listen', 'send'):
        LOGGER.critical(f'Указан недопустимый режим работы {client_mode}')
        sys.exit(1)
    return server_address, server_port, client_mode


def main():
    """Загружаем параметры командной строки"""
    server_address, server_port, client_mode = arg_parser()

    LOGGER.info(f'Запущен клиент с параметрами: {server_address}, '
                f'{server_port}, {client_mode}')
    # Инициализация сокета и обмен
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence())
        answer = process_ans(get_message(transport))
        LOGGER.info(f'Установлено соединение с сервером {answer}')
        print('Установлено соединение с сервером')
    except (ValueError, json.JSONDecodeError):
        LOGGER.error('Не удалось декодировать сообщение сервера')
    else:
        # Если соединение с сервером установлено корректно,
        # начинаем обмен с ним, согласно режиму
        # основной цикл программы
        if client_mode == 'send':
            print('Режим работы - отправка сообщений.')
        else:
            print('Режим работы - приём сообщений')

        while True:
            # Режим работы отправки сообщений
            if client_mode == 'send':
                try:
                    send_message(transport, create_message(transport))
                except (ConnectionError, ConnectionResetError,
                        ConnectionAbortedError):
                    LOGGER.error(f'Соединение с сервером {server_address} '
                                 f'было потеряно')
                    sys.exit(1)
            if client_mode == 'listen':
                try:
                    message_from_server(get_message(transport))
                except (ConnectionError, ConnectionResetError,
                        ConnectionAbortedError):
                    LOGGER.error(f'Соединение с сервером {server_address} '
                                 f'было потеряно')
                    sys.exit(1)


if __name__ == '__main__':
    main()
