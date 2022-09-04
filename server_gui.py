import sys
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, \
    QTableView, QDialog, QPushButton, QLineEdit, QFileDialog, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


# GUI - Создание таблицы QModel, для отображения в окне программы.
def gui_create_model(database):
    list_users = database.active_users_list()
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(['Иия Клиента', 'IP Адрес', 'Порт',
                                          'Время подключения'])
    for row in list_users:
        user, ip, port, time = row
        user = QStandardItem(user)
        user.setEditable(False)
        ip = QStandardItem(ip)
        ip.setEditable(False)
        port = QStandardItem(port)
        port.setEditable(False)
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)
        list_table.appendRow([user, ip, port, time])
    return list_table


# GUI - Функция реализующая заполнение таблицы историей сообщений.
def create_stat_model(database):
    # Список записей из базы
    hist_list = database.message_history()

    # Объект модели данных
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(
        ['Имя клиента', 'Последний раз входил', 'Сообщений отправлено',
         'Сообщений получено'])
    for row in hist_list:
        user, last_seen, sent, recvd = row
        user = QStandardItem(user)
        user.setEditable(False)
        last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
        last_seen.setEditable(False)
        sent = QStandardItem(str(sent))
        sent.setEditable(False)
        recvd = QStandardItem(str(recvd))
        recvd.setEditable(False)
        list_table.appendRow([user, last_seen, sent, recvd])
    return list_table


# Класс основного окна
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Кнопки
        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        self.refresh_btn = QAction('Обновить список', self)
        self.show_history_btn = QAction('История клиентов', self)
        self.config_btn = QAction('Настройки сервера', self)

        self.statusBar()

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_btn)
        self.toolbar.addAction(self.show_history_btn)
        self.toolbar.addAction(self.config_btn)

        # Окно
        self.setFixedSize(800, 600)
        self.setWindowTitle('Серверное меню')

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 55)
        self.active_clients_table.setFixedSize(780, 400)

        self.show()


class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_btn = QPushButton('Закрыть', self)
        self.close_btn.move(250, 650)
        self.close_btn.clicked.connect(self.close)

        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(580, 620)

        self.show()


class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Окно
        self.setFixedSize(400, 300)
        self.setWindowTitle('Настройки сервера')

        self.db_path_label = QLabel('Путь до файла базы данных: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        self.db_path_select = QPushButton('Обзор...', self)
        self.db_path_select.move(275, 28)

        def open_file_dialog():
            global dialog
            dialog = QFileDialog(self)
            path = dialog.getExistingDirectory()
            path = path.replace('/', '\\')
            self.db_path.insert(path)

        self.db_path_select.clicked.connect(open_file_dialog)

        self.db_file_label = QLabel('Имя файла базы данных: ', self)
        self.db_file_label.move(10, 68)
        self.db_file_label.setFixedSize(180, 15)

        self.db_file = QLineEdit(self)
        self.db_file.move(200, 66)
        self.db_file.setFixedSize(150, 20)

        self.port_label = QLabel('Номер порта для соединения: ', self)
        self.port_label.move(10, 108)
        self.port_label.setFixedSize(180, 15)

        self.port = QLineEdit(self)
        self.port.move(200, 108)
        self.port.setFixedSize(150, 20)

        self.ip_label = QLabel('С какого IP принимаем соединения: ', self)
        self.ip_label.move(10, 148)
        self.ip_label.setFixedSize(180, 15)

        self.ip_label_note = QLabel(' оставьте это поле пустым, чтобы \n'
                                    'принимать соединение с любых адресов.' ,
                                    self)
        self.ip_label_note.move(10, 168)
        self.ip_label_note.setFixedSize(500, 30)

        self.ip = QLineEdit(self)
        self.ip.move(200, 148)
        self.ip.setFixedSize(150, 20)

        self.save_btn = QPushButton('Сохранить', self)
        self.save_btn.move(190, 220)

        self.close_btn = QPushButton('Закрыть', self)
        self.close_btn.move(275, 220)
        self.close_btn.clicked.connect(self.close)

        self.show()


if __name__ == '__main__':
    # app = QApplication(sys.argv)
    # main_window = MainWindow()
    # main_window.statusBar().showMessage('Test Statusbar')
    # test_list = QStandardItemModel(main_window)
    # test_list.setHorizontalHeaderLabels(['Имя Клиента', 'IP Адрес', 'Порт',
    #                                      'Время подключения'])
    # test_list.appendRow(
    #     [QStandardItem('test1'), QStandardItem('192.168.0.5'),
    #      QStandardItem('23544'), QStandardItem('09:10:21')])
    # test_list.appendRow(
    #     [QStandardItem('test2'), QStandardItem('192.168.0.8'),
    #      QStandardItem('67678'), QStandardItem('10:15:21')])
    # main_window.active_clients_table.setModel(test_list)
    # main_window.active_clients_table.resizeColumnsToContents()
    # app.exec_()

    # app = QApplication(sys.argv)
    # window = HistoryWindow()
    # test_list = QStandardItemModel(window)
    # test_list.setHorizontalHeaderLabels(['Имя Клиента', 'Последний раз входил',
    #                                      'Отправлено','Получено'])
    # test_list.appendRow(
    #     [QStandardItem('test1'), QStandardItem('Fri Dec 12 16:20:34 2020'),
    #      QStandardItem('5'), QStandardItem('10')])
    # test_list.appendRow(
    #     [QStandardItem('test2'), QStandardItem('Fri Dec 10 10:30:34 2021'),
    #      QStandardItem('15'), QStandardItem('7')])
    # window.history_table.setModel(test_list)
    # window.history_table.resizeColumnsToContents()
    # app.exec_()

    app = QApplication(sys.argv)
    dial = ConfigWindow()

    app.exec_()
