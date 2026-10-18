#!/usr/bin/python3.8
"""Передача файлу по SCTP: метадані потоком 0, вміст потоком 1."""

import hashlib
import json
import os
import socket
import sys

import sctp

PORT = 5000
CHUNK = 16384
META, DATA = 0, 1
USAGE = """usage: sctpcp.py recv [port]
       sctpcp.py send host[:port] file"""


def recv_msg(conn):
    # велике повідомлення ядро віддає частинами, остання позначена MSG_EOR
    parts = []
    while True:
        _, flags, part, notif = conn.sctp_recv(CHUNK)
        parts.append(part)
        if flags & socket.MSG_EOR or not part:
            return b"".join(parts), notif.stream


def send(target, path):
    host, _, port = target.partition(":")
    size = os.path.getsize(path)
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    sock = sctp.sctpsocket_tcp(socket.AF_INET)
    sock.initparams.num_ostreams = 2
    sock.connect((host, int(port or PORT)))
    meta = {"name": os.path.basename(path), "size": size, "sha256": digest}
    sock.sctp_send(json.dumps(meta).encode(), stream=META)
    sent = 0
    with open(path, "rb") as f:
        while block := f.read(CHUNK):
            sock.sctp_send(block, stream=DATA)
            sent += 1
    reply = sock.sctp_recv(1024)[2].decode()
    sock.close()
    print(f"sent {meta['name']}: {size} bytes in {sent} messages, "
          f"server: {reply}")


def recv(port):
    server = sctp.sctpsocket_tcp(socket.AF_INET)
    server.initparams.num_ostreams = 2
    server.bind(("0.0.0.0", port))
    server.listen(1)
    print(f"waiting on {port}/sctp")
    conn, addr = server.accept()
    # без цієї підписки ядро не повідомляє номер потоку
    conn.events.data_io = True
    conn.events.flush()
    msg, stream = recv_msg(conn)
    meta = json.loads(msg)
    print(f"{addr[0]} sends {meta['name']} ({meta['size']} bytes), "
          f"metadata on stream {stream}")
    h = hashlib.sha256()
    got = msgs = 0
    streams = set()
    with open(meta["name"], "wb") as f:
        while got < meta["size"]:
            block, stream = recv_msg(conn)
            streams.add(stream)
            f.write(block)
            h.update(block)
            got += len(block)
            msgs += 1
    ok = h.hexdigest() == meta["sha256"]
    conn.sctp_send(b"OK" if ok else b"CHECKSUM MISMATCH", stream=META)
    conn.close()
    data_streams = ", ".join(map(str, sorted(streams)))
    print(f"saved {meta['name']}: {got} bytes in {msgs} messages "
          f"on stream {data_streams}, sha256 {'ok' if ok else 'mismatch'}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "recv":
        recv(int(sys.argv[2]) if len(sys.argv) > 2 else PORT)
    elif len(sys.argv) == 4 and sys.argv[1] == "send":
        send(sys.argv[2], sys.argv[3])
    else:
        sys.exit(USAGE)
