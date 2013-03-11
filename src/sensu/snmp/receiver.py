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

from sensu.snmp.log import log as LOG
from sensu.snmp.trap import Trap
from sensu.snmp.util import *

class TrapReceiverThread(threading.Thread):
    def __init__(self, config, mibs, callback):
        # Initialize threading.Thread
        threading.Thread.__init__(self, name=self.__class__.__name__)
        # Initialize TrapReceiver
        self._trap_receiver = TrapReceiver(config, mibs, callback)

    def stop(self):
        if self._trap_receiver._snmp_engine.transportDispatcher.jobsArePending():
            self._trap_receiver._snmp_engine.transportDispatcher.jobFinished(1) 

    def run(self):
        LOG.debug("%s: Started" % (self.name))
        self._trap_receiver.run()
        LOG.debug("%s: Exiting" % (self.name))

class TrapReceiver(object):

    SNMPV3_AUTH_PROTOCOLS = {"MD5": pysnmp.entity.config.usmHMACMD5AuthProtocol}
    SNMPV3_PRIV_PROTOCOLS = {"DES": pysnmp.entity.config.usmDESPrivProtocol, "none": None}

    def __init__(self, config, mibs, callback):
        self._config = config
        self._mibs = mibs
        self._callback = callback

        # Create SNMP engine with autogenernated engineID and pre-bound to socket transport dispatcher
        self._snmp_engine = pysnmp.entity.engine.SnmpEngine()
        LOG.debug("TrapReceiver: Initialized SNMP Engine")

        # Configure transport UDP over IPv4
        if config['snmp']['transport']['udp']['enabled']:
            self._configure_udp_transport(config['snmp']['transport']['listen_address'], int(config['snmp']['transport']['listen_port']))

        # Configure transport TCP over IPv4
        if config['snmp']['transport']['tcp']['enabled']:
            # TODO: Implement TCP transport
            pass

        # Configure SNMPv2 if enabled
        if bool(self._config['snmp']['auth']['version2']['enabled']):
            self._configure_snmp_v2(self._config['snmp']['auth']['version2']['community'])

        # Configure SNMPv3 if enabled
        if bool(self._config['snmp']['auth']['version3']['enabled']):
            # TODO: configure SNMPv3 users from config file
            self._configure_snmp_v3(self._config['snmp']['auth']['version3']['users'])

        LOG.debug("TrapReceiver: Initialized")

    def _configure_udp_transport(self, listen_address, listen_port):
        pysnmp.entity.config.addSocketTransport(self._snmp_engine, udp.domainName,
            udp.UdpTransport().openServerMode((listen_address, listen_port)))
        LOG.info("TrapReceiver: Initialized SNMP UDP Transport on %s:%s" % (listen_address, listen_port))

    def _configure_snmp_v2(self, community):
        # v1/2 setup
        pysnmp.entity.config.addV1System(self._snmp_engine, 'sensu-trapd-agent', community)
        LOG.debug("TrapReceiver: Initialized SNMPv1 Auth")

    def _configure_snmp_v3(self, users):
        # configure snmp v3 users
        for user in users:
            auth = users[user]['authentication']
            priv = users[user]['privacy']

            auth_protocol = self.SNMPV3_AUTH_PROTOCOLS[auth['protocol']]
            priv_protocol = self.SNMPV3_PRIV_PROTOCOLS[priv['protocol']]

            if priv_protocol:
                pysnmp.entity.config.addV3User(self._snmp_engine, user,
                    auth_protocol, auth['password'],
                    priv_protocol, priv['password'])
                LOG.debug("TrapReceiver: Added SNMPv3 user: %s auth: %s, priv: %s" % (user, auth['protocol'], priv['protocol']))
            else:
                pysnmp.entity.config.addV3User(self._snmp_engine, user,
                    auth_protocol, auth['password'])
                LOG.debug("TrapReceiver: Added SNMPv3 user: %s auth: %s, priv: none" % (user, auth['protocol']))

        LOG.debug("TrapReceiver: Initialized SNMPv3 Auth")

    def _create_trap(self, trap_oid, trap_arguments, trap_properties):
        # initialize trap
        return Trap(trap_oid, trap_arguments, **trap_properties)

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
            LOG.debug("TrapReceiver: Notification received from %s" % (trap_source[0]))

            # read all the varBinds
            for oid, val in varBinds:
                # translate OID to mib symbol/modname
                (module, symbol) = self._mibs.lookup_oid(oid)

                if module == "SNMPv2-MIB" and symbol == "snmpTrapOID":
                    # the SNMPv2-MIB::snmpTrapOID value is the trap oid
                    trap_oid = val
                    # load the mib symbol/modname for the trap oid
                    (trap_symbol_name, trap_mod_name) = self._mibs.lookup_oid(trap_oid)
                else:
                    # all other values should be converted to mib symbol/modname and put in the trap_data dict
                    trap_arg_oid = oid
                    # convert value
                    trap_arg_value = self._mibs.lookup_value(module, symbol, val)
                    trap_args[trap_arg_oid] = trap_arg_value

            # get trap source info
            trap_source_address,trap_source_port = trap_source
            trap_source_hostname,trap_source_domain = get_hostname_from_address(trap_source_address)

            # set trap propreties
            trap_properties = dict()
            trap_properties['hostname'] = trap_source_hostname
            trap_properties['ipaddress'] = trap_source_address
            trap_properties['domain'] = trap_source_domain

            # create trap
            trap = self._create_trap(trap_oid, trap_args, trap_properties)

            # now that everything has been parsed, trigger the callback
            self._callback(trap)

        except Exception, ex:
            LOG.exception("Error handling SNMP notification")

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
