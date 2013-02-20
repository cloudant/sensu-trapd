import os
import sys
import threading
import pysnmp.entity.engine
import pysnmp.entity.config
import pysnmp.smi.builder
import pysnmp.smi.view
import pysnmp.entity.rfc3413.mibvar
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto.api import v2c

#from sensu.snmp.handler import TrapHandler
#from sensu.snmp.dispatcher import Dispatcher

from sensu.snmp.log import log
from sensu.snmp.trap import Trap
from sensu.snmp.util import get_hostname_from_address

class TrapReceiverThread(threading.Thread):
    def __init__(self, config, callback):
        # Initialize threading.Thread
        threading.Thread.__init__(self, name=self.__class__.__name__)
        # Initialize TrapReceiver
        self._trap_receiver = TrapReceiver(config, callback)

    def stop(self):
        if self._trap_receiver._snmp_engine.transportDispatcher.jobsArePending():
            self._trap_receiver._snmp_engine.transportDispatcher.jobFinished(1) 

    def run(self):
        log.debug("%s started" % (self.name))
        self._trap_receiver.run()
        log.debug("%s exiting" % (self.name))

class TrapReceiver(object):

    DEFAULT_MIB_DIRS = []
    DEFAULT_MIB_LIST = ['SNMPv2-MIB']

    def __init__(self, config, callback):

        self._config = config
        self._callback = callback

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

        log.debug("Initialized TrapReceiver")

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

    def _create_trap(self, trap_oid, trap_name, trap_source, trap_arguments, trap_properties=None):
        if trap_properties is None:
            trap_properties = dict()
        # get trap source info
        trap_source_address,trap_source_port = trap_source
        trap_source_hostname,trap_source_domain = get_hostname_from_address(trap_source_address)
        # build trap propreties
        trap_properties['hostname'] = trap_source_hostname
        trap_properties['ipaddress'] = trap_source_address
        trap_properties['domain'] = trap_source_domain

        # initialize trap
        trap = Trap(trap_oid, trap_name, trap_arguments, **trap_properties)
        return trap

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

            # create trap
            trap = self._create_trap(trap_oid, trap_name, trap_source, trap_args)

            # now that everything has been parsed, forward to the callback 
            self._callback(trap)

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
