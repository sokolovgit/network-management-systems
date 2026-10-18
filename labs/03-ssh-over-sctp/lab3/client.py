#!/usr/bin/python3.8
import socket
import sctp

client = sctp.sctpsocket_tcp(socket.AF_INET)
client.connect(("10.10.0.2", 12345))

message = "Hello, server!"
client.send(message.encode("utf-8"))

response = client.recv(1024)
print(f"Server Response: {response.decode('utf-8')}")

client.close()
