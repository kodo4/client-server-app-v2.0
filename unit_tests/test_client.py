import sys
import os
import unittest
sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, \
    ACTION, PRESENCE
from client import create_presence, proccess_ans


class TestCase(unittest.TestCase):
    """Класс с тестами"""

    def test_def_presense(self):
        """Тест корректного запроса"""
        test = create_presence()
        test[TIME] = 1.1
        self.assertEqual(test, {ACTION: PRESENCE, TIME: 1.1, USER:
            {ACCOUNT_NAME: 'Guest'}})

    def test_200_ans(self):
        """Тест корректного разбора ответа 200"""
        self.assertEqual(proccess_ans({RESPONSE: 200}), '200: OK')

    def test_400_ans(self):
        """Тест корректного разбора 400"""
        self.assertRaises(ValueError, proccess_ans, {ERROR: 'Bad Request'})


if __name__ == '__main__':
    unittest.main()
