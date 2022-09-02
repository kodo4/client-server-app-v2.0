import base64

from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, QEvent, Qt
import sys
import json
import logging
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA

from common.errors import ServerError

sys.path.append('../')
from client.main_window_conv import Ui_MainClientWindow
from client.add_contact import AddContactDialog
from client.del_contact import DelContactDialog
from database.client_db import ClientDatabase
from client.transport import ClientTransport
from client.start_dialog import UserNameDialog
from common.variables import *

LOGGER =logging.getLogger('client')


# Класс основного окна
class ClientWindow(QMainWindow):
    def __init__(self, database, transport, keys):
        super().__init__()
        # БД и сокет
        self.database = database
        self.transport = transport

        # дешифровщик сообщений с предзагруженным ключом
        self.decrypter = PKCS1_OAEP.new(keys)

        # Загрузка конфигурации окна
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # Кнопка выхода
        self.ui.menu_exit.triggered.connect(qApp.exit)

        # Кнопка отправки сообщения
        self.ui.btn_send.clicked.connect(self.send_message)

        # Кнопка добавления контактов
        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)

        # Кнопка удаления контакта
        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        # Дополнительные атрибуты
        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.current_chat_key = None
        self.encryptor = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(Qt.
                                                           ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)

        # Двоейное нажатие по списку контактов отправляется в обработчик
        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    # Деактировать поля ввода
    def set_disabled_input(self):
        # Надписать - получатель.
        self.ui.label_new_message.setText('Для выбора получателя дважды '
                                          'кликните на нем в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        # Поле ввода и кнопка отправки неактивны до выбора получателя
        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

        self.encryptor = None
        self.current_chat = None
        self.current_chat_key = None

    # метод заполнения истории сообщений
    def history_list_update(self):
        # Получаем историю сортированную по дате
        list_messages = sorted(self.database.get_history(self.current_chat),
                               key=lambda item: item[3])
        # Если модель не создана, создадим.
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)
        # Очистим от старых записей
        self.history_model.clear()
        # Берём не более 20 последних записей.
        length = len(list_messages)
        start_index = 0
        if length > 20:
            start_index = length - 20
        # Заполнение истории, разделение входящих и исходящих выравниванием
        # и разным фоном.
        # Записи в обратном порядке, выбираем их с конца и не более 20
        for i in range(start_index, length):
            item = list_messages[i]
            if item[1] == 'in':
                print(item[0])
                mess = QStandardItem(f'Входящее от '
                                     f'{item[3].replace(microsecond=0)}:'
                                     f'\n {item[2]}')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(255, 213, 213)))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
            else:
                mess = QStandardItem(f'Исходящее от '
                                     f'{item[3].replace(microsecond=0)}:'
                                     f'\n {item[2]}')
                mess.setEditable(False)
                mess.setTextAlignment(Qt.AlignRight)
                mess.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(mess)
        self.ui.list_messages.scrollToBottom()

    # Функция обработчик двойного клика
    def select_active_user(self):
        # Выбираем пользователя и помещаем в QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        # Вызываем основную функцию
        self.set_active_user()

    # Устанавливаем активного собеседника
    def set_active_user(self):
        # активируем чат с собеседником
        try:
            self.current_chat_key = self.transport.key_request(
                self.current_chat)
            LOGGER.debug(f'Загружен открытый ключ для {self.current_chat}')
            if self.current_chat_key:
                self.encryptor = PKCS1_OAEP.new(
                    RSA.import_key(self.current_chat_key))
        except OSError:
            self.current_chat_key = None
            self.encryptor = None
            LOGGER.debug(f'Не удалось получить ключ для {self.current_chat}')
        if not self.current_chat_key:
            self.messages.warning(
                self, 'Ошибка', 'Для выбранного пользователя нет ключа '
                                'шифрования')
            return

        # Ставим надпись и активируем кнопки
        self.ui.label_new_message.setText(f'Введите сообщение для '
                                          f'{self.current_chat}')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)

        # Заполняем окно историей сообщений
        self.history_list_update()

    # Обновление контакт-листа
    def clients_list_update(self):
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    # Добавление контакта
    def add_contact_window(self):
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(lambda: self.add_contact_action(
                                                                select_dialog))
        select_dialog.show()

    # Функция обработчик добавления, сообщает серверу, обновляет таблицу и
    # список контактов
    def add_contact_action(self, item):
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    # Добавление контакта в БД
    def add_contact(self, new_contact):
        try:
            self.transport.add_contact(new_contact)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение '
                                                       'с сервером')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            LOGGER.info(f'Успешно добавлен контакт {new_contact}')
            self.messages.information(self, 'Успех', 'Контакт успешно '
                                                     'добавлен')

    # Удаление контакта
    def delete_contact_window(self):
        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(lambda:
                                             self.delete_contact(remove_dialog))
        remove_dialog.show()

    # Функция обработчик удаления контакта, сообщает на сервер, обноваляет
    # таблицу контактов
    def delete_contact(self, item):
        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединения с '
                                                       'сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            LOGGER.info(f'Успешно удалён контакт {selected}')
            self.messages.information(self, 'Успех', 'Контакт успешно удалён')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    # Функция отправки сообщения пользователю
    def send_message(self):
        # проверяем текств поле, должно быть не пустое затем забираем
        # сообщение и поле очищаем
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        # Шифруем сообщение ключом получателя
        message_text_encrypted = self.encryptor.encrypt(
            message_text.encode('utf-8'))
        message_text_encrypted_base64 = base64.b64encode(
            message_text_encrypted)
        try:
            self.transport.send_message(self.current_chat,
                                message_text_encrypted_base64.decode('ascii'))
            pass
        except ServerError as err:
            self.messages.critical(self, 'Ошибка', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с '
                                                       'сервером')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Ошибка', 'Потеряно соединение с '
                                                   'сервером')
            self.close()
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            LOGGER.debug(f'Отправлено сообщение для {self.current_chat}:'
                         f'{message_text}')
            self.history_list_update()

    # Слот приёма нового сообщения
    @pyqtSlot(dict)
    def message(self, message):
        """
        Обработка входящих сообщений, выполняем дешифровку
        и сохранение в истории сообщений. Запрашивает пользователя если
        пришло не от текущего собеседника. При необходимости меняет
        собеседника
        """
        # Получаем строку байтов
        encrypted_message = base64.b64decode(message[MESSAGE_TEXT])
        # Декодируем строку, при ошибке выдаём сообщение и завершаем функцию
        try:
            decrypted_message = self.decrypter.decrypt(encrypted_message)
        except (ValueError, TypeError):
            self.messages.warning(
                self, 'Ошибка', 'Не удалось декодировать сообщение')
            return
        # Сохраняем сообщение в БД и обновляем историю сообщений или открывае
        # новый чат
        self.database.save_message(
            self.current_chat,
            'in',
            decrypted_message.decode('utf-8'))
        sender = message[SENDER]

        if sender == self.current_chat:
            self.history_list_update()
        else:
            # Проверим есть ли такой пользователь у нас в контактах:
            if self.database.check_contact(sender):
                # Если есть, спрашиваем о желании открыть с ним чат и
                # открываем при желании
                if self.messages.question(self, 'Новое сообщение',
                                      f'Получено новое сообщение от {sender}, '
                                      f'открыть чат с ним?', QMessageBox.Yes,
                                      QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.database.save_message(
                        self.current_chat,
                        'in',
                        decrypted_message.decode('utf-8'))
                    self.set_active_user()
            else:
                print('NO')
                # Раз нет, спрашиваем хотим ли добваить юзера в контакты.
                if self.messages.question(self, 'Новое сообщение',
                          f'Получено новое сообщение от {sender}.\n'
                          f'Данного пользователя нет в вашем контакт-листе.\n'
                          f'Добавить в контакты и открыть чат с ним?',
                          QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.database.save_message(
                        self.current_chat,
                        'in',
                        decrypted_message.decode('utf-8'))
                    self.set_active_user()

    # Слот потери соединения
    # Выдаёт сообщение об ошибке и завершает работу приложеия
    @pyqtSlot()
    def connection_lost(self):
        self.messages.warning(self, 'Сбой соединения', 'Потеряно соединение с '
                                                       'сервером.')
        self.close()

    @pyqtSlot()
    def sig_205(self):
        """Обновление баз данных по команде сервера"""
        if self.current_chat and not self.database.check_user(
                self.current_chat):
            self.messages.warning(self, 'Сочувствую', 'К сожалению собеседник '
                                                      'был удалён с сервера')
            self.set_disabled_input()
            self.current_chat = None
        self.clients_list_update()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)
