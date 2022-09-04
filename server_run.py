import argparse
import configparser
import os
import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from common.variables import *
import logs.server_log_config
from decos import log
from database.server_db import ServerStorage
from server.core import MessageProcessor
from server.main_window import MainWindow

LOGGER = logging.getLogger('server')


@log
def arg_parser(default_port, default_address):
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('--no_gui', action='store_true')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    gui_flag = namespace.no_gui
    LOGGER.debug('Аргумнты успешно загружены')
    return listen_address, listen_port, gui_flag


@log
def config_load():
    # Делаем парсинг файла ini
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/{"server_dist+++.ini"}')
    # Если файл загрузился то запускаем сервер с настройками из файла, иначе
    # значени по умолчанию
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_db.db3')
        return config


@log
def main():
    """Основная функция"""
    config = config_load()

    # Загрузка параметров из командной строки, если нет параметров, запуск со
    # значениями по умолчанию
    listen_address, listen_port, gui_flag = arg_parser(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))

    server = MessageProcessor(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    if gui_flag:
        while True:
            command = input('Введите exit для завершения работы сервера.')
            if command == 'exit':
                server.running = False
                server.join()
                break
    else:
        server_app = QApplication(sys.argv)
        server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        main_window = MainWindow(database, server, config)

        server_app.exec_()

        server.running = False


if __name__ == '__main__':
    main()
