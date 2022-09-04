import binascii
import os
import select
import socket
import threading
import hmac
import logging

from descriptors import VerifyPort
from common.variables import *
from common.utils import get_message, send_message
from decos import login_required

LOGGER = logging.getLogger('server')


class MessageProcessor(threading.Thread):
    port = VerifyPort()

    def __init__(self, listen_address, listen_port, database):
        self.addr = listen_address
        self.port = listen_port
        self.database = database

        self.sock = None

        self.clients = []

        self.listen_sockets = None
        self.error_sockets = None

        self.running = True

        self.names = {}

        super().__init__()

    def run(self):

        self.init_socket()

        while self.running:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError as err:
                pass
            else:
                LOGGER.info(f'Установлено соединение с ПК {client_address}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []

            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = select.select(self.clients, self.clients, [], 0)
            except OSError as err:
                LOGGER.error(f'Ошибка работы с сокетами: {err.errno}')

            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except OSError:
                        LOGGER.info(
                            f'Клиент {client_with_message.getpeername()} '
                            f'отключился от сервера.')
                        self.remove_client(client_with_message)

    def remove_client(self, client):
        """обработка клиента с которым утеряна связь.
        ищет клиента и удаляет его из списка и БД"""
        LOGGER.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

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
        self.sock.listen(MAX_CONNECTIONS)

    def process_message(self, message):
        """Отправка сообщения клиенту"""
        if message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] in \
                self.listen_sockets:
            try:
                send_message(self.names[message[DESTINATION]], message)
                LOGGER.info(f'Отправлено сообщение пользователю '
                            f'{message[DESTINATION]} от пользователя '
                            f'{message[SENDER]}')
            except OSError:
                self.remove_client(message[DESTINATION])
        elif message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] not in \
                self.listen_sockets:
            LOGGER.error(f'Связь с клиентом {message[DESTINATION]} была '
                         f'потеряна. Соединение закрыто, доставка невозможна.')
            self.remove_client(self.names[message[DESTINATION]])
        else:
            LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере,'
                f'отправка сообщения невозможна')

    @login_required
    def process_client_message(self, message, client):
        """
        Обработчик сообщений от клиентов, принимает словарь -
        сообщение от клиента, проверяет корректность,
        возвращает словарь-ответ для клиента
        """
        print('autorizer')
        LOGGER.info(f'Разбор сообщения от клиента: {message}')
        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:
            self.autorize_user(message, client)

        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and \
                self.names[message[SENDER]] == client:
            if message[DESTINATION] in self.names:
                self.database.process_message(message[SENDER],
                                              message[DESTINATION])
                self.process_message(message)
                try:
                    send_message(client, RESPONSE_200)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не в сети'
                try:
                    send_message(client, response)
                except OSError:
                    pass
            return
        # Запрос о выходе
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in \
                message and self.names[message[ACCOUNT_NAME]] == client:
            self.remove_client(client)

        # запрос контактов
        elif ACTION in message and message[ACTION] == GET_CONTACTS and \
                USER in message and self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        # добавление контактов
        elif ACTION in message and message[ACTION] == ADD_CONTACT and \
                ACCOUNT_NAME in message and USER in message and \
                self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        # удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and \
                ACCOUNT_NAME in message and USER in message and \
                self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        # известные контакты
        elif ACTION in message and message[ACTION] == USERS_REQUEST and \
                ACCOUNT_NAME in message and \
                self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user
                                   in self.database.users_list()]
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        # Запрос публичного ключа пользователя
        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST and \
                ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            if response[DATA]:
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Нет публичного ключа для данного ' \
                                  'пользователя'
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

    def autorize_user(self, message, sock):
        """реализация авторизации пользователей"""
        LOGGER.debug(f'Начало авторизации {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято'
            try:
                LOGGER.debug(f'Имя пользователя занято, сообщение{response}')
                send_message(sock, response)
            except OSError:
                LOGGER.debug('OS Error')
                pass
            self.clients.remove(sock)
            sock.close()
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован'
            try:
                LOGGER.debug(f'Пользователя нет в бд, {response}')
                send_message(sock, response)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            LOGGER.debug('Проверка пароля')
            # Словарь для ключа
            message_auth = RESPONSE_511
            # набор байтов в представлении hex
            random_str = binascii.hexlify(os.urandom(64))
            # декодируем, создаём хэш пороля и сохраняем в БД
            message_auth[DATA] = random_str.decode('ascii')
            hash = hmac.new(self.database.get_hash(message[USER][ACCOUNT_NAME]),
                             random_str, 'MD5')
            digest = hash.digest()
            LOGGER.debug(f'Сообщения авторизации, {message_auth}')
            try:
                send_message(sock, message_auth)
                ans = get_message(sock)
            except OSError as err:
                LOGGER.debug('Ошибка авторизации: ', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])
            # если ответ корректный, то сохраняем его в список пользователей
            if RESPONSE in ans and ans[RESPONSE] == 511 and \
                    hmac.compare_digest(digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                # Добавляем пользователя в список активных пользователей и
                # если поменялся ключ то обновляем в БД
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль'
                try:
                    send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        """отправка сервисных сообщений 205"""
        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])
