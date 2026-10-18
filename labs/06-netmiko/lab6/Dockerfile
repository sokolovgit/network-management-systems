FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y vim iproute2 iputils-ping \
                                         nmap net-tools ethtool ifupdown \
                                         netcat iptables tcpdump bridge-utils \
                                         arping systemd

RUN apt-get install -y python3-pip

RUN apt-get install -y openssh-server
RUN echo 'root:12345' | chpasswd
RUN sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config

RUN pip3 install -U pip && pip3 install NetMiko==3.4.0 cryptography==3.4.8

ENTRYPOINT ["/usr/sbin/init"]
