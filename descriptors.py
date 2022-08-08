import logging
from logs import server_log_config
LOGGER = logging.getLogger('server')
from common.variables import DEFAULT_PORT


class VerifyPort:

    def __set__(self, instance, value):
        if not 1023 < value < 65535:
            LOGGER.critical(
                f'Попытка запуска сервера с указанием неподходящего порта '
                f'{value}. Допустимы адреса с 1024 до 65535'
                f'сервер будет запущен с порта 7777'
            )
            instance.__dict__[self.name] = DEFAULT_PORT

        instance.__dict__[self.name] =value

    def __set_name__(self, owner, name):
        self.name = name
