from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, \
    QLabel, qApp


# Стартовое окно с вводом имени
class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False

        self.setWindowTitle('Привет!')
        self.setFixedSize(250, 93)

        self.label = QLabel('Введите имя пользователя:', self)
        self.label.move(10, 10)
        self.label.setFixedSize(230, 20)

        self.client_name = QLineEdit(self)
        self.client_name.move(10, 30)
        self.client_name.setFixedSize(230, 20)

        self.btn_ok = QPushButton('Начать', self)
        self.btn_ok.move(50, 60)
        self.btn_ok.clicked.connect(self.click)

        self.btn_cancel = QPushButton('Отмена', self)
        self.btn_cancel.move(130, 60)
        self.btn_cancel.clicked.connect(qApp.exit)

        self.show()

    # Функция обработки нажатия кнопки "Начать"
    def click(self):
        if self.client_name.text():
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
