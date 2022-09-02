import argparse
import os.path
import sys
import json
import socket
import time
import threading
from Crypto.PublicKey import RSA
from client.transport import ClientTransport
from client.main_window import ClientWindow
from client.start_dialog import UserNameDialog
from common.variables import *
import logging
import logs.client_log_config
from decos import log
from database.client_db import ClientDatabase
from PyQt5.QtWidgets import QApplication, QMessageBox

from errors import ServerError

LOGGER = logging.getLogger('client')

@log
def arg_parser():
    """Создаём парсер аргументов коммандной строки
    и читаем параметры, возвращаем 3 параметра"""
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_password = namespace.password

    if server_port < 1023 or server_port > 65536:
        LOGGER.critical(f'Порт {server_port} недопустим')
        sys.exit(1)

    return server_address, server_port, client_name, client_password


if __name__ == '__main__':
    # Загрузка параметров
    server_address, server_port, client_name, client_password = arg_parser()
    LOGGER.debug('аргументы загружены')
    # Создаем клиентское приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке, то запросим его
    start_dialog = UserNameDialog()
    if not client_name or not client_password:
        client_app.exec_()
        # Если пользователь ввёд имя и нажал ОК, то сохраняем ведённое и
        # удаляем объект. Инача выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_password = start_dialog.client_passwd.text()
            LOGGER.debug(f'использован для входа {client_name}, '
                         f'{client_password}')
        else:
            exit(0)

    LOGGER.info(
        f'Запущен клиент с параметрами: адрес сервера - {server_address},'
        f'порт - {server_port}, имя пользователя - {client_name}')

    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())
    LOGGER.debug('Ключи успешно загружены')
    # Создаём объект базы данных
    database = ClientDatabase(client_name)
    try:
        transport = ClientTransport(server_port,
                                    server_address,
                                    database,
                                    client_name,
                                    client_password,
                                    keys)
        LOGGER.debug(f'Сервер готов')
    except ServerError as error:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    del start_dialog

    # Создаём GUI
    main_window = ClientWindow(database, transport, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат клиента {client_name}')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()
