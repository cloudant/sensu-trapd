from sensu.snmp.log import log

class TrapHandler(object):
    def __init__(self, name, output, handlers, severity, tokens):
        self.name = name
        self.output = output
        self.handlers = handlers
        self.severity = severity
        self.tokens = tokens

    def _build_substitutions(self, trap):
        substitutions = dict()
        #substitutions['hostname'] = trap.source_hostname
        #substitutions['ipaddress'] = trap.source_ipaddress

        # build map of trap properties:token
        trap_properties_token_map = dict(zip(self.tokens.values(), self.tokens.keys()))
        for trap_prop_name, trap_prop_value in trap.properties.items():
            if trap_prop_name in trap_properties_token_map:
                token = trap_properties_token_map[trap_prop_name]
                substitutions[token] = str(trap_prop_value)
            else:
                substitutions[trap_prop_name] = str(trap_prop_value) 

        return substitutions

    def handle(self, trap):
        log.info("Received Trap: %s" % (trap))

        # prepare trap data substitions
        print self._build_substitutions(trap)

