from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, \
    QLabel, qApp


# Стартовое окно с вводом имени
class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False

        self.setWindowTitle('Привет!')
        self.setFixedSize(250, 120)

        self.label = QLabel('Введите имя пользователя:', self)
        self.label.move(10, 10)
        self.label.setFixedSize(230, 20)

        self.client_name = QLineEdit(self)
        self.client_name.move(10, 30)
        self.client_name.setFixedSize(230, 20)

        self.label_passwd = QLabel('Введите пароль:', self)
        self.label_passwd.setFixedSize(150, 15)
        self.label_passwd.move(10, 55)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(150, 15)
        self.client_passwd.move(10, 75)
        self.client_passwd.setEchoMode(QLineEdit.Password)

        self.btn_ok = QPushButton('Начать', self)
        self.btn_ok.move(50, 95)
        self.btn_ok.clicked.connect(self.click)

        self.btn_cancel = QPushButton('Отмена', self)
        self.btn_cancel.move(130, 95)
        self.btn_cancel.clicked.connect(qApp.exit)

        self.show()

    # Функция обработки нажатия кнопки "Начать"
    def click(self):
        if self.client_name.text() and self.client_passwd.text():
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
