#!/usr/bin/python3.8
import socket
import sctp

server = sctp.sctpsocket_tcp(socket.AF_INET)
server.bind(("0.0.0.0", 12345))
server.listen(1)
print("Server listening...")
connection, address = server.accept()
print(f"Connected by: {address}")

while True:
    data = connection.recv(1024)
    if not data:
        break
    print(f"Received: {data.decode('utf-8')}")
    connection.send(data)
connection.close()
