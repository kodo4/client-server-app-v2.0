import sys
import logging
import socket
import logs.server_log_config
import logs.client_log_config

# метод определения модуля, источника запуска.
# Метод find () возвращает индекс первого вхождения искомой подстроки,
# если он найден в данной строке.
# Если его не найдено, - возвращает -1.

if sys.argv[0].find('client') == -1:
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('client')

def log(func_to_log):
    """Функция-декоратор"""
    def log_saver(*args, **kwargs):
        LOGGER.debug(
            f'Была вызвана функция {func_to_log.__name__} c параметрами {args} , {kwargs}. '
            f'Вызов из модуля {func_to_log.__module__}')
        ret = func_to_log(*args, **kwargs)
        return ret

    return log_saver


def login_required(func):
    """
    Проверка что клент авторизирован на сервере.
    проверяет передаваемые объекты сокета за исключением передачи
    словаря на авторизацию. Если клиент не авторизован выдаёт исключение
    """

    def checker(*args, **kwargs):
        from server.core import MessageProcessor
        from common.variables import ACTION, PRESENCE

        if isinstance(args[0], MessageProcessor):
            found = False
            for arg in args:
                if isinstance(arg, socket.socket):
                    for client in args[0].names:
                        print(client)
                        if args[0].names[client] == arg:
                            found = True

            for arg in args:
                if isinstance(arg, dict):
                    if ACTION in arg and arg[ACTION] == PRESENCE:
                        found = True
            if not found:
                raise TypeError
        return func(*args, **kwargs)
    return checker
