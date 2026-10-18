"""Парсер виводу ip addr show / ip link show."""
import re

HEADER = re.compile(r'^(\d+): ([^:@]+)(?:@\S+)?: <([^>]*)> (.*)$')
LINK = re.compile(r'^\s+link/(\S+)(?: (\S+))?')
INET = re.compile(r'^\s+(inet6?) (\S+)')


def parse_ip(output: str) -> dict:
    ifaces = {}
    iface = None
    for line in output.splitlines():
        if m := HEADER.match(line):
            opts = m.group(4).split()
            iface = ifaces[m.group(2)] = {
                'index': int(m.group(1)),
                'flags': m.group(3).split(','),
                'mtu': int(opts[opts.index('mtu') + 1]),
                'state': opts[opts.index('state') + 1],
                'type': None, 'mac': None, 'inet': [], 'inet6': [],
            }
        elif iface is None:
            continue
        elif m := LINK.match(line):
            iface['type'], iface['mac'] = m.groups()
        elif m := INET.match(line):
            iface[m.group(1)].append(m.group(2))
    return ifaces
