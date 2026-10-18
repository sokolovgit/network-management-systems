#!/usr/bin/python3
"""Налаштування eth1 на host1 з перевірками через парсер ip show."""
from netmiko import ConnectHandler
from ipparse import parse_ip

ADDR = '10.11.0.2/24'

conn = ConnectHandler(device_type='linux', host='10.10.0.2', username='root', password='12345')


def eth1():
    return parse_ip(conn.send_command('ip addr show')).get('eth1')


if eth1() is None:
    print('Info: eth1 is absent. Creating ...')
    conn.send_command('ip link add eth1 type dummy')
if eth1() is None:
    exit('Error: could not create eth1')
if ADDR not in eth1()['inet']:
    print(f'Info: adding {ADDR} ...')
    conn.send_command(f'ip addr add {ADDR} dev eth1')
if 'UP' not in eth1()['flags']:
    print('Info: eth1 is down. Bringing up ...')
    conn.send_command('ip link set eth1 up')

iface = eth1()
if ADDR not in iface['inet'] or 'UP' not in iface['flags']:
    exit(f'Error: eth1 is not configured: {iface}')
print(f'eth1 is configured: {", ".join(iface["inet"])}, mtu {iface["mtu"]}, {iface["mac"]}')
