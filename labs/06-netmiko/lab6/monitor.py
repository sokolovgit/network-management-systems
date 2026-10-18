#!/usr/bin/python3
"""Моніторинг вузла через Netmiko: навантаження, пам'ять, трафік eth0."""
import sys
import time
from datetime import datetime

from netmiko import ConnectHandler

HOST = '10.10.0.2'
INTERVAL = float(sys.argv[1]) if len(sys.argv) > 1 else 3
COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 5
S = '/sys/class/net/eth0/statistics'
# час беремо з вузла: send_command триває близько секунди, і sleep не дає точного інтервалу
CMD = (f'echo $(date +%s.%N) $(cut -d" " -f1,4 /proc/loadavg) '
       f'$(awk \'/MemTotal|MemAvailable/ {{print $2}}\' /proc/meminfo) '
       f'$(cat {S}/rx_bytes {S}/tx_bytes)')


def connect():
    return ConnectHandler(device_type='linux', host=HOST, username='root', password='12345',
                          conn_timeout=3, timeout=5)


print('час       стан         load1  процеси  пам\'ять, %   RX, KiB/s   TX, KiB/s')
conn, prev = None, None
for i in range(COUNT + 1):
    now = datetime.now().strftime('%H:%M:%S')
    try:
        conn = conn or connect()
        t, load, procs, total, avail, rx, tx = conn.send_command(CMD).split()
    except Exception:
        print(f'{now}  UNREACHABLE')
        conn, prev = None, None
    else:
        t, rx, tx = float(t), int(rx), int(tx)
        if prev:
            dt = 1024 * (t - prev[0])
            mem = 100 * (1 - int(avail) / int(total))
            print(f'{now}  {"OK":<11}  {load:>5}  {procs:>7}  {mem:>10.1f}  '
                  f'{(rx - prev[1]) / dt:>10.1f}  {(tx - prev[2]) / dt:>10.1f}')
        prev = t, rx, tx
    if i < COUNT:
        time.sleep(INTERVAL)
