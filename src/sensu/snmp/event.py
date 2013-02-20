import os
import sys
import simplejson as json

class TrapEvent(object):
    def __init__(self):
        pass

    def to_json(self):
        return json.dumps({'foo':'bar'})
