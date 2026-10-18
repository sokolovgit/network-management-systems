FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y vim iproute2 iputils-ping \
                                         nmap net-tools ethtool ifupdown \
                                         netcat iptables tcpdump bridge-utils \
                                         arping systemd

RUN apt-get install -y python3-pip

RUN apt-get install -y openssh-server
RUN echo 'root:12345' | chpasswd

RUN apt-get install -y software-properties-common network-manager

ENTRYPOINT ["/usr/sbin/init"]
