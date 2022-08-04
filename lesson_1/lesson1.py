import ipaddress
import platform
import time
from subprocess import Popen, PIPE
from threading import Thread
from tabulate import tabulate

OUT = [('Reachable', 'Unreachable'), ]


def host_ping(ip_address):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    args = ['ping', param, '1', ip_address]
    reply = Popen(args, stdout=PIPE, stderr=PIPE)
    code = reply.wait()
    if code == 0:
        OUT.append((ip_address, ''))
    else:
        OUT.append(('', ip_address))


def host_range_ping(ip, amount):
    ipv4 = ipaddress.ip_address(ip)
    for i in range(amount):
        ip = ipv4 + i
        ip = str(ip)
        thr = Thread(target=host_ping, args=(ip, ))
        thr.start()


def host_range_ping_tab():
    ip = input('Введите первоночальный адрес: ')
    amount = int(input('Сколько адресов проверяем? '))
    host_range_ping(ip, amount)
    print('Началась проверка ip адрессов.')
    for i in range(5, 0, -1):
        print(f'До конца проверки осталось секунд: {i}')
        time.sleep(1)
    print(tabulate(OUT, headers='firstrow', tablefmt='pipe'))


host_range_ping_tab()
