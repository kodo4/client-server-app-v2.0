import dis

import pprint


class ServerVerifier(type):
    def __init__(cls, clsname, bases, clsdict):

        methods = []
        methods_2 = []
        attrs = []

        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_METHOD':
                        if i.argval not in methods_2:
                            methods_2.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        if 'connect' in methods:
            raise TypeError('Есть connect  в серверной части')

        if not ('AF_INET' in attrs and 'SOCK_STREAM' in attrs):
            raise TypeError('Некорректно инициализирован сокет сервера')

        super().__init__(clsname, bases, clsdict)


class ClientVerify(type):
    def __init__(cls, clsname, bases, clsdict):

        methods = []
        methods_2 = []
        attrs = []

        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    if i.opname == 'LOAD_METHOD':
                        if i.argval not in methods_2:
                            methods_2.append(i.argval)
                    if i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)

        if 'accept' in methods or 'listen' in methods:
            raise TypeError('В классе есть запрещёные методы ')
        if not 'sock' in attrs:
            raise TypeError('Не верное соединение')

        super().__init__(clsname, bases, clsdict)
