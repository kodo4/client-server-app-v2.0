import argparse
import sys
import json
import socket
import time
import threading
from client.transport import ClientTransport
from client.main_window import ClientWindow
from client.start_dialog import UserNameDialog
from common.variables import *
import logging
import logs.client_log_config
from decos import log
from database.client_db import ClientDatabase
from PyQt5.QtWidgets import QApplication

LOGGER = logging.getLogger('client')

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


if __name__ == '__main__':
    # Загрузка параметров
    server_address, server_port, client_name = arg_parser()

    # Создаем клиентское приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке, то запросим его
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        # Если пользователь ввёд имя и нажал ОК, то сохраняем ведённое и
        # удаляем объект. Инача выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    LOGGER.info(
        f'Запущен клиент с параметрами: адрес сервера - {server_address},'
        f'порт - {server_port}, имя пользователя - {client_name}')

    # Создаём объект базы данных
    database = ClientDatabase(client_name)

    transport = ClientTransport(server_port, server_address, database,
                                    client_name)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат клиента {client_name}')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()
