import simplejson as json

import pysnmp.entity.engine
import pysnmp.entity.config
import pysnmp.smi.builder
import pysnmp.smi.view
import pysnmp.entity.rfc3413.mibvar

from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto.api import v2c

from sensu.snmp.trap import Trap
from sensu.snmp.handler import TrapHandler
from sensu.snmp.log import log

class Server(object):

    DEFAULT_MIB_DIRS = []
    DEFAULT_MIB_LIST = ['SNMPv2-MIB']

    def __init__(self, config):
        self._config = config

        # Create SNMP engine with autogenernated engineID and pre-bound to socket transport dispatcher
        self._snmp_engine = pysnmp.entity.engine.SnmpEngine()
        log.debug("Initialized SNMP Engine")

        # Configure transport UDP over IPv4
        self._snmp_listen_address = config['snmp']['listen_address']
        self._snmp_listen_port = int(config['snmp']['listen_port'])
        pysnmp.entity.config.addSocketTransport(self._snmp_engine, udp.domainName,
            udp.UdpTransport().openServerMode((self._snmp_listen_address, self._snmp_listen_port)))
        log.debug("Initialized SNMP Transport: %s:%s" % (self._snmp_listen_address, self._snmp_listen_port))

        # Configure SNMPv2 if enabled
        if bool(self._config['snmp']['version2']['enabled']):
            self._configure_snmp_v2(self._config['snmp']['version2']['community'])

        # Configure SNMPv3 if enabled
        if bool(self._config['snmp']['version3']['enabled']):
            # TODO: configure SNMPv3 users from config file
            self._configure_snmp_v3('authkey1', 'privkey1')

        # Configure SNMP Mibs
        self._configure_mibs(self._config['snmp']['mib_dir'], self._config['snmp']['mibs'])

        # Configure Trap Handlers
        self._trap_handlers = self._configure_trap_handlers(self._config['traps']['trap_file'])

        log.debug("Initialized Server")

    def _configure_trap_handlers(self, trap_file):
        log.debug("Parsing trap handler file: %s" % (trap_file))
        trap_handlers = dict()
        try:
            fh = open(trap_file, 'r')
            trap_file_data = json.load(fh)
            for trap_handler_name, trap_handler_config in trap_file_data.items():
                trap = trap_handler_config['trap'] if 'trap' in trap_handler_config else 'default'
                trap_handlers[trap] = self._parse_trap_handler(trap_handler_name, trap_handler_config)
                log.debug("Parsed trap handler: %s" % (trap_handler_name))
        finally:
            fh.close()
        return trap_handlers

    def _parse_trap_handler(self, trap_handler_name, trap_handler_config):
        trap_handler_tokens = trap_handler_config['tokens'] if 'tokens' in trap_handler_config else None
        # Initialize trap handler
        trap_handler = TrapHandler(trap_handler_name, 
                                   trap_handler_config['output'], 
                                   trap_handler_config['handlers'],
                                   trap_handler_config['severity'],
                                   trap_handler_tokens)
        return trap_handler

    def _configure_snmp_v2(self, community):
        # v1/2 setup
        pysnmp.entity.config.addV1System(self._snmp_engine, 'sensu-snmp-agent', community)
        log.debug("Initialized SNMPv1 Auth")

    def _configure_snmp_v3(self, authkey, privkey):
        # SNMPv3/USM setup
        # user: usr-md5-des, auth: MD5, priv DES
        pysnmp.entity.config.addV3User(
            self._snmp_engine, 'usr-md5-des',
            pysnmp.entity.config.usmHMACMD5AuthProtocol, authkey,
            pysnmp.entity.config.usmDESPrivProtocol, privkey)
        log.debug("Initialized SNMPv3 Auth")

    def _configure_mibs(self, mib_dir, mib_list):
        self._snmp_mib_builder = pysnmp.smi.builder.MibBuilder()
        self._snmp_mib_builder.importSymbols("MibScalar")

        # Configure MIB paths
        self._snmp_mib_sources = self._snmp_mib_builder.getMibSources()
        for path in self.DEFAULT_MIB_DIRS + [mib_dir]:
            self._snmp_mib_sources += (pysnmp.smi.builder.DirMibSource(path),)
            log.debug("Added MIB source: %s" % path)
        self._snmp_mib_builder.setMibSources(*self._snmp_mib_sources)

        for mib in mib_list + self.DEFAULT_MIB_LIST:
            self._snmp_mib_builder.loadModules(mib, )
            log.debug("Loaded MIB: %s" % mib)
        self._snmp_mib_view = pysnmp.smi.view.MibViewController(self._snmp_mib_builder)

    def _load_trap_handler(self, trap_name):
        if trap_name in self._trap_handlers:
            return self._trap_handlers[trap_name]
        return self._trap_handlers['default']

    def handle_trap(self, trap):
        trap_handler = self._load_trap_handler(trap.name)
        trap_handler.handle(trap)

    def _notification_callback(self, snmp_engine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
        """
        Callback function for receiving notifications
        """
        trap_oid = None
        trap_name = None
        trap_args = dict()

        try:
            # get the source address for this notification
            transportDomain, trap_source = snmp_engine.msgAndPduDsp.getTransportInfo(stateReference)
            log.debug("Notification received from %s" % (trap_source[0]))

            # read all the varBinds
            for oid, val in varBinds:
                # translate OID to mib symbol/modname
                (symbol_name, mod_name), indices = pysnmp.entity.rfc3413.mibvar.oidToMibName(self._snmp_mib_view, oid)

                if mod_name == "SNMPv2-MIB" and symbol_name == "snmpTrapOID":
                    # the SNMPv2-MIB::snmpTrapOID value is the trap oid
                    trap_oid = val
                    # load the mib symbol/modname for the trap oid
                    (trap_symbol_name, trap_mod_name), trap_indices = pysnmp.entity.rfc3413.mibvar.oidToMibName(self._snmp_mib_view, trap_oid)
                    trap_name = "%s::%s" % (trap_mod_name, trap_symbol_name)
                else:
                    # all other values should be converted to mib symbol/modname and put in the trap_data dict
                    trap_arg_oid = oid
                    trap_arg_name = "%s::%s" % (mod_name, symbol_name)
                    # convert value
                    trap_arg_value = pysnmp.entity.rfc3413.mibvar.cloneFromMibValue(self._snmp_mib_view, mod_name, symbol_name, val)
                    trap_args[trap_arg_name] = trap_arg_value

            trap_args['address'] = trap_source[0]

            # initialize trap
            trap = Trap(trap_oid, trap_name, trap_args)

            # now that everything has been parsed, forward to the trap handler
            self.handle_trap(trap)

        except Exception, ex:
            log.exception("Error handling SNMP notification")

    def run(self):
        # Register SNMP Application at the SNMP engine
        ntfrcv.NotificationReceiver(self._snmp_engine, self._notification_callback)

        self._snmp_engine.transportDispatcher.jobStarted(1) # this job would never finish

        # Run I/O dispatcher which would receive queries and send confirmations
        try:
            self._snmp_engine.transportDispatcher.runDispatcher()
        except:
            self._snmp_engine.transportDispatcher.closeDispatcher()
            raise
