FROM kathara/base:latest

RUN apt-get update && apt-get install -y \
	isc-dhcp-server \
	openssh-server \
	openresolv
