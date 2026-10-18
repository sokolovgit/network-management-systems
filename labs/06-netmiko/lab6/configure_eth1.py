#!/usr/bin/python3

from datetime import datetime
from netmiko import ConnectHandler
from netmiko.linux import LinuxSSH


device_conf = {
    'device_type': 'linux',
    'host': '10.10.0.2',
    'username': 'root',
    'password': '12345',
    'port': 22,
    'session_log': f"{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.txt",
    'auth_timeout': 30
}

connection: LinuxSSH = ConnectHandler(**device_conf)
connection.send_command('ip link add eth1 type dummy')

output: str = connection.send_command('ip link show eth1')
if 'does not exist' in output:
    print('Error: could not create eth1')
    exit(1)

connection.send_command('ip addr add 10.11.0.2/24 dev eth1')
output: str = connection.send_command('ip addr show eth1')
if '10.11.0.2' not in output:
    print('Error: could not set 10.11.0.2 to the eth1')
    exit(1)

output: str = connection.send_command('cat /proc/sys/net/ipv4/icmp_echo_ignore_all')
if '0' in output:
    print('Info: ICMP is enabled. Disabling ...')
    connection.send_command('bash -c "echo 1 > /proc/sys/net/ipv4/icmp_echo_ignore_all"')
    output: str = connection.send_command('cat /proc/sys/net/ipv4/icmp_echo_ignore_all')
    if '0' in output:
        print('Error: Could not disable ICMP')
        exit(1)

print('Host is configured')
