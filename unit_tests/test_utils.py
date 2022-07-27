import sys
import os
import unittest
import json
sys.path.insert(0, os.path.join(os.getcwd(), '..'))
from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, \
    ACTION, PRESENCE, ENCODING
from common.utils import get_message, send_message


class TestSocket:
    """Тестовый класс для тестирования отправки и получения,
    при создании требует словарь, который будет прогоняться
    через тестовую функцию"""
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        """Тестовая функция отправки, корректно кодирует сообщение,
        так-же сохранет то, что должно быть отправлено в сокет.
        message_to_send - то, что отправляем в сокет"""
        json_test_message = json.dumps(self.test_dict)
        # кодирует сообщение
        self.encoded_message = json_test_message.encode(ENCODING)
        # сохраняем что должно было быть отправлено в сокет
        self.received_message = message_to_send

    def recv(self, max_len):
        """Получаем данные из сокета"""
        json_test_message = json.dumps(self.test_dict)
        return json_test_message.encode(ENCODING)


class TestUtils(unittest.TestCase):
    """Тестовый класс, собственно выполняющий тестирование"""

    test_dict_send = {
        ACTION: PRESENCE,
        TIME: 111111.111111,
        USER: {
            ACCOUNT_NAME: 'test_test'
        }
    }
    test_dict_recv_ok = {RESPONSE: 200}
    test_dict_recv_err = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    def test_send_message_true(self):
        """Тестируем корректность работы функции отправки,
        создадим тестовый сокет и проверим корректность отправки словаря
        """
        # экземпляр тестового словаря, хранит собственно тестовый словарь
        test_socket = TestSocket(self.test_dict_send)
        # вызов тестируемой функции, результаты будут сохранены в тестовом сокете
        send_message(test_socket, self.test_dict_send)
        # Проверка корректности кодирования словаря.
        # Сравниваем результат кодирования и результат от тестируемой функции
        self.assertEqual(test_socket.encoded_message,
                         test_socket.received_message)

    def test_send_message_with_error(self):
        """Тестируем корректность работы функции отправки,
        создадим тестовый сокет и проверим корректность отправки словаря
        """
        # экземпляр тестового словаря, хранит собственно тестовый словарь
        test_socket = TestSocket(self.test_dict_send)
        # вызов тестируемой функции, результаты будут сохранены в тестовом
        # сокете
        send_message(test_socket, self.test_dict_send)
        # допольнительно, проверим генерацию исключения, при не словаря на входе,
        # и здесь использован следующий формат asserRaises:
        # <<self.assertRaises(TypeError, test_function, args)>>
        self.assertRaises(TypeError, send_message, test_socket,
                          "wrong_dictionary")

    def test_get_message_ok(self):
        """Тест функции приёма сообщения"""

        test_sock_ok = TestSocket(self.test_dict_recv_ok)
        # тест корректной расшифровки корректного словаря
        self.assertEqual(get_message(test_sock_ok), self.test_dict_recv_ok)

    def test_get_message_error(self):
        """Тест функции приёма сообщения"""
        test_sock_err = TestSocket(self.test_dict_recv_err)
        # тест корректной расшифровки ошибочного словаря
        self.assertEqual(get_message(test_sock_err), self.test_dict_recv_err)


if __name__ == '__main__':
    unittest.main()
