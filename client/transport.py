import sys
import json
import socket
import time
import threading

from common.errors import ServerError

sys.path.append(('../'))
from PyQt5.QtCore import pyqtSignal, QObject
from common.variables import *
from common.utils import get_message, send_message
import logging


LOGGER = logging.getLogger('client')

sock_lock = threading.Lock()


# Тарнспорт отвечающий за взаимодействие клиента и сервера
class ClientTransport(threading.Thread, QObject):
    # Сигнал нового сообщения и потери соедининения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        # Конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # База данных, имя пользователя, сокет
        self.database = database
        self.username = username
        self.transport = None
        # Установка соединения
        self.connection_init(port, ip_address)

        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                LOGGER.critical(f'Потеряно соединение с сервером {err}')
            LOGGER.error('Timeout соединения при обновлении списков '
                         'пользователей')
        # Флаг продолжения работы транспорта
        self.running = True

    def connection_init(self, port, ip):
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)

        connected = False
        for i in range(5):
            LOGGER.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)
        if not connected:
            LOGGER.critical('Не удалось подключится к серверу')

        LOGGER.debug('Установлено соединение с сервером')

        # Отправляем серверу приветствие
        try:
            with sock_lock:
                send_message(self.transport, self.create_presence())
                self.process_ans(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            LOGGER.critical('Потеряно соединение с сервером')
        LOGGER.info(f'Установлено соединение с сервером')

    def create_presence(self):
        """
        Функция генерирует запрос о присутствии клиента
        :param account_name:
        :return:
        """
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username
            }
        }
        LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя '
                     f'{self.username}')
        return out

    def process_ans(self, message):
        """Функция разбирает ответ сервера"""
        LOGGER.debug(f'Получен ответ от сервера {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            else:
                LOGGER.error(f'Ошибка полученного ответа от сервера {message}')
                raise ValueError
        elif ACTION in message and message[ACTION] == MESSAGE and \
                SENDER in message and DESTINATION in message and \
                MESSAGE_TEXT in message and \
                message[DESTINATION] == self.username:
            LOGGER.debug(f'Получено сообщение от пользователя: '
                         f'{message[SENDER]} - {message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER], 'in',
                                       message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])

    def contacts_list_update(self):
        LOGGER.debug(f'Запрос контакт листа для пользователя {self.username}')
        req = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        LOGGER.debug(f'Сформирован запрос {req}')
        with sock_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        LOGGER.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            LOGGER.error('Не удалось обновить список контактов.')

    def user_list_update(self):
        LOGGER.debug(f'Запрос списка известных пользователей {self.username}')
        req = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with sock_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            self.database.add_users(ans[LIST_INFO])
        else:
            LOGGER.error('Не удалось обновить список известных пользователей')

    def add_contact(self, contact):
        LOGGER.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with sock_lock:
            send_message(self.transport, req)
            self.process_ans(get_message(self.transport))

    def remove_contact(self, contact):
        LOGGER.debug(f'Удаление контакта {contact}')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with sock_lock:
            send_message(self.transport, req)
            self.process_ans(get_message(self.transport))

    def transport_shutdown(self):
        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with sock_lock:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        LOGGER.debug('Транспорт завершает работу')
        time.sleep(0.5)

    def send_message(self, to, message):
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
            send_message(self.transport, message_dict)
            self.process_ans(get_message(self.transport))
            LOGGER.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        LOGGER.debug('Запущен процесс - приёмник сообщений с сервера')
        while self.running:
            time.sleep(1)
            with sock_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        LOGGER.critical(f'Потеряно соединение с сервером')
                        self.running = False
                        self.connection_lost.emit()
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    LOGGER.debug(f'Потеряно соединение с сервером')
                    self.running = False
                    self.connection_lost.emit()
                else:
                    LOGGER.debug(f'Принято сообщение с сервера: {message}')
                    self.process_ans(message)
                finally:
                    self.transport.settimeout(5)
