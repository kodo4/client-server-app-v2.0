import sys
import json
import socket
import time
from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.client_log_config

LOGGER = logging.getLogger('client')


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
    LOGGER.debug(f'Сформировано {PRESENCE} сообщение')
    return out


def proccess_ans(message):
    """Функция разбирает ответ сервера"""
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            LOGGER.debug(f'Получен ответ от сервера {message}')
            return '200: OK'
        LOGGER.debug(f'Получен ответ от сервера {message}')
        return f'400: {message[ERROR]}'
    LOGGER.error(f'Ошибка полученного ответа от сервера {message}')
    raise ValueError



def main():
    """Загружаем параметры командной строки"""
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if server_port < 1024 or server_port > 65535:
            LOGGER.error(f'Ошибка подключения к серверу')
            raise ValueError
    except IndexError:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
        LOGGER.debug(f'Выбраны порт и ip по умолчанию {server_address}:'
                     f'{server_port}')
    except ValueError:
        LOGGER.error('В качестве порта может быть указано только число в '
                     'диапазоне от 1024 до 65535')
        sys.exit(1)

    # Инициализация сокета и обмен

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.connect((server_address, server_port))
    message_to_server = create_presence()
    send_message(transport, message_to_server)
    try:
        answer = proccess_ans(get_message(transport))
        LOGGER.info(f'получен ответ {answer}')
    except (ValueError, json.JSONDecodeError):
        LOGGER.error('Не удалось декодировать сообщение сервера')


if __name__ == '__main__':
    main()
