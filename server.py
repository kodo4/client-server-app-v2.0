import socket
import sys
import json
from common.variables import *
from common.utils import get_message, send_message
import logging
import logs.server_log_config
from decos import log

LOGGER = logging.getLogger('server')


@log
def process_client_message(message):
    """
    Обработчик сообщений от клиентов, принимает словарь -
    сообщение от клиента, проверяет корректность,
    возвращает словарь-ответ для клиента
    :param message:
    :return:
    """
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
        LOGGER.debug(f'Получен верный {PRESENCE} от клиента')
        return {RESPONSE: 200}
    LOGGER.debug(f'Получен неверный {PRESENCE} от клиента: {message}')
    return {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }


def main():
    """
    Загрузка параметров командной строки, если нет параметров,
    то задаём значения по умолчанию.
    Сначала обрабатываем порт:
    server.py -p 8888 -a 127.0.0.1
    """

    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = DEFAULT_PORT
        if listen_port < 1024 or listen_port > 65535:
            raise ValueError
    except IndexError:
        print('После параметра - "p" необходимо указать номер порта.')
        sys.exit(1)
    except ValueError:
        print('Номер порта может быть указан только в диапазоне от 1024 до '
              '65535')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-a') + 1]
        else:
            listen_address = DEFAULT_IP_ADDRESS
    except IndexError:
        print('После параметра - "a" необходимо указать адрес, который будет '
              'слушать сервер.')
        sys.exit(1)

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))

    # Слушаем порт
    transport.listen(MAX_CONNECTIONS)

    while True:
        client, client_address = transport.accept()
        try:
            message_from_client = get_message(client)
            LOGGER.debug(f'сообщение от клиента: {message_from_client}')
            response = process_client_message(message_from_client)
            send_message(client, response)
            client.close()
        except (ValueError, json.JSONDecodeError):
            LOGGER.error('Принято некорректное сообщение от клиента.')
            client.close()


if __name__ == '__main__':
    main()
