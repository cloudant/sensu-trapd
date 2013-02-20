import os
import sys

from sensu.snmp.log import log

class Trap(object):
    def __init__(self, oid, trap, arguments, **kwargs):
        self.oid = oid
        self.trap = trap
        self.arguments = arguments
        self.properties = kwargs

    def __str__(self):
        return "<Trap %s>" % (self.trap)
