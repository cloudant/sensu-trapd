import os
import sys
import simplejson as json

from sensu.snmp.log import log

class Trap(object):
    def __init__(self, oid, name, props):
        self.oid = oid
        self.name = name
        if props is None:
            props = dict()
        self.properties = props

    def __str__(self):
        return "<Trap %s>" % (self.name)

