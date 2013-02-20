import socket

from sensu.snmp.log import log


def get_hostname_from_address(addr):
    try:
        hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(addr)
        # parse hostname
        hostname_parts = hostname.split('.')
        if len(hostname_parts) <= 2:
            return hostname, None 
        else:
            pass
    except socket.herror:
        return addr, addr
