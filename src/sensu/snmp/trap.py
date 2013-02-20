import os
import sys

from sensu.snmp.log import log

class Trap(object):
    def __init__(self, oid, name, arguments, **kwargs):
        self.oid = oid
        self.name = name
        self.arguments = arguments
        self.properties = kwargs

    def __str__(self):
        return "<Trap %s>" % (self.name)
