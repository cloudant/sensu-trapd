import os
import sys

from sensu.snmp.log import log

class Trap(object):

    def __init__(self, oid, arguments, **properties):
        self.oid = oid
        self.arguments = arguments
        self.properties = properties

    def __repr__(self):
        return "<Trap oid:'%r' >" % (self.oid)
