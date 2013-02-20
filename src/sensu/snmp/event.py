import os
import sys
import simplejson as json

class TrapEvent(object):
    def __init__(self, name, output, status, handlers):
        self.name = name
        self.output = output
        self.status = status
        self.handlers = handlers

    def to_json(self):
        return json.dumps({'name':self.name, 'output': self.output, 'status': self.status, 'handlers': self.handlers})

    def __str__(self):
        return "<TrapEvent name:'%s' status:%d >" % (self.name, self.status)
