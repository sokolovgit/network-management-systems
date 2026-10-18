#!/usr/bin/env python3
"""Обробник pass для snmpd: значення об'єктів SOKOLOV-LAB4-MIB."""
import shutil
import sys

BASE = ".1.3.6.1.4.1.99999.1"


def tcp_established():
    n = 0
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path) as f:
                n += sum(1 for line in f.readlines()[1:] if line.split()[3] == "01")
        except OSError:
            pass
    return n


def mem_available():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    return 0


def root_used_percent():
    du = shutil.disk_usage("/")
    return round(du.used * 100 / du.total)


OBJECTS = {
    1: ("string", lambda: "Sokolov Oleksandr, IP-33"),
    2: ("gauge", tcp_established),
    3: ("gauge", mem_available),
    4: ("integer", root_used_percent),
}


def suffix(oid):
    return oid[len(BASE) + 1:].split(".") if oid.startswith(BASE + ".") else []


def reply(n):
    kind, fn = OBJECTS[n]
    print(f"{BASE}.{n}.0\n{kind}\n{fn()}")


def main():
    if len(sys.argv) < 3:
        return
    mode, oid = sys.argv[1], sys.argv[2]
    parts = suffix(oid)
    if mode == "-g":
        if len(parts) == 2 and parts[1] == "0" and parts[0].isdigit() and int(parts[0]) in OBJECTS:
            reply(int(parts[0]))
    elif mode == "-n":
        if not oid.startswith(BASE) or oid == BASE:
            reply(1)
            return
        n = int(parts[0]) if parts and parts[0].isdigit() else 0
        nxt = n if len(parts) == 1 else n + 1
        if nxt in OBJECTS:
            reply(nxt)
    elif mode == "-s":
        print("not-writable")


main()
