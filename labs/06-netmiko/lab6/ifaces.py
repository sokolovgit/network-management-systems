#!/usr/bin/python3
"""Таблиця інтерфейсів вузла за виводом ip addr show."""
import sys

from netmiko import ConnectHandler
from ipparse import parse_ip

host = sys.argv[1] if len(sys.argv) > 1 else '10.10.0.2'
conn = ConnectHandler(device_type='linux', host=host, username='root', password='12345')
ifaces = parse_ip(conn.send_command('ip addr show'))
conn.disconnect()

print(f'{"#":>3}  {"інтерфейс":<10} {"стан":<8} {"MTU":>5}  {"MAC":<17}  IPv4')
for name, i in ifaces.items():
    up = 'UP' if 'UP' in i['flags'] else 'DOWN'
    print(f'{i["index"]:>3}  {name:<10} {up:<8} {i["mtu"]:>5}  {i["mac"] or "-":<17}  '
          f'{", ".join(i["inet"]) or "-"}')
