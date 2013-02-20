
from sensu.snmp.event import TrapEvent
from sensu.snmp.log import log

class TrapHandler(object):
    def __init__(self, trap, name, output, handlers, severity, arguments):
        self.trap = trap
        self.name = name
        self.output = output
        self.handlers = handlers
        self.severity = severity
        self.arguments = arguments

    def _build_default_substitutions(self, trap):
        """
        build substitution list from trap properties
        """
        substitutions = dict()
        substitutions['oid'] = str(trap.oid)
        substitutions['trap'] = trap.trap
        for k,v in trap.properties.items():
            substitutions[k] = v 
        return substitutions

    def _build_substitutions(self, trap):
        """
        build substitution list from trap arguments and using handler
        """
        substitutions = self._build_default_substitutions(trap)
        for trap_argument_name, token in self.arguments.items():
            if trap_argument_name in trap.arguments:
                substitutions[token] = str(trap.arguments[trap_argument_name])
        return substitutions

    def _do_substitutions(self, pattern, substitutions):
        return pattern.format(**substitutions)

    def process_trap(self, trap):
        substitutions = self._build_substitutions(trap)
        return TrapEvent(self._do_substitutions(self.name, substitutions),
                         self._do_substitutions(self.output, substitutions),
                         self.severity,
                         self.handlers) 

    @classmethod
    def parse(cls, trap_handler_config):
        trap_handler_args = trap_handler_config['arguments'] if 'arguments' in trap_handler_config else None
        # Initialize trap handler
        trap_handler = TrapHandler(trap_handler_config['trap'],
                                   trap_handler_config['name'],
                                   trap_handler_config['output'], 
                                   trap_handler_config['handlers'],
                                   trap_handler_config['severity'],
                                   trap_handler_args)
        return trap_handler

