from PyQt5.QtWidgets import QDialog, QPushButton, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class StatWindow(QDialog):
    """Окно статистики пользователей"""
    def __init__(self, database):
        super().__init__()

        self.database = database
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

        self.create_stat_model()

    def create_stat_model(self):
        # Список записей из базы
        hist_list = self.database.message_history()

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
        self.history_table.setModel(list_table)
        self.history_table.resizeColumnsToContents()
        self.history_table.resizeRowsToContents()
