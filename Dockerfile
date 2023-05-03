FROM kathara/base:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
	isc-dhcp-server \
	isc-dhcp-relay \
	openssh-server \
	openresolv \
	squid \
	dnsmasq \
	bind9 bind9utils
