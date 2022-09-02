from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QTimer
from server.stat_window import StatWindow
from server.config_window import ConfigWindow
from server.add_user import RegisterUser
from server.remove_user import DelUserDialog

# Класс основного окна
class MainWindow(QMainWindow):

    def __init__(self, database, server, config):
        super().__init__()

        # БД сервера
        self.database = database

        self.server_thread = server
        self.config = config

        # Кнопки
        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        self.refresh_btn = QAction('Обновить список', self)
        self.config_btn = QAction('Настройки сервера', self)
        self.register_btn = QAction('Регистрация пользователя', self)
        self.remove_btn = QAction('Удаление пользователя', self)
        self.show_history_btn = QAction('История клиентов', self)

        self.statusBar()
        self.statusBar().showMessage('Сервер работает')

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_btn)
        self.toolbar.addAction(self.show_history_btn)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.register_btn)
        self.toolbar.addAction(self.remove_btn)

        # Окно
        self.setFixedSize(800, 600)
        self.setWindowTitle('Серверное меню')

        self.label = QLabel('Список подключенных пользователей:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        self.timer = QTimer()
        self.timer.timeout.connect(self.create_users_model)
        self.timer.start(1000)

        self.refresh_btn.triggered.connect(self.create_users_model)
        self.show_history_btn.triggered.connect(self.show_statistics)
        self.config_btn.triggered.connect(self.server_config)
        self.register_btn.triggered.connect(self.reg_user)
        self.remove_btn.triggered.connect(self.rem_user)

        self.show()

    def create_users_model(self):
        """Заполняем таблицу активных пользователей"""
        list_users = self.database.active_users_list()
        list = QStandardItemModel()
        list.setHorizontalHeaderLabels(
            ['Имя Клиента', 'IP Адрес', 'Порт', 'Время-подключения'])
        for row in list_users:
            user, ip, port, time = row
            user = QStandardItem(user)
            user.setEditable(False)
            ip = QStandardItem(ip)
            ip.setEditable(False)
            port = QStandardItem(str(port))
            port.setEditable(False)

            time = QStandardItem(str(time.replace(microsecond=0)))
            time.setEditable(False)
            list.appendRow([user, ip, port, time])
        self.active_clients_table.setModel(list)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def show_statistics(self):
        """создаём окно со статистикой клиентов"""
        global stat_window
        stat_window = StatWindow(self.database)
        stat_window.show()

    def server_config(self):
        """создаём окно со статистикой клиентов"""
        global config_window
        config_window = ConfigWindow(self.config)

    def reg_user(self):
        """создаём окно регистрации пользователя"""
        global reg_window
        reg_window = RegisterUser(self.database, self.server_thread)
        reg_window.show()

    def rem_user(self):
        """создаём окно удаления пользователя"""
        global rem_window
        rem_window = DelUserDialog(self.database, self.server_thread)
        rem_window.show()
