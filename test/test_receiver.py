import time
import os
import sys
import unittest
import logging
from mock import Mock
from mock import patch

from pysnmp.entity.rfc3413.oneliner import ntforg

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sensu.snmp.mib import MibResolver
from sensu.snmp.receiver import TrapReceiverThread

# helpers
from helpers.log import log, configure_log

class TrapReceiverTestCase(unittest.TestCase):

    def setUp(self):
        self.config = {
                "snmp": {
                    "transport": {
                        "listen_address": "127.0.0.1",
                        "listen_port": 1620,
                        "udp": {
                            "enabled": True
                        },
                        "tcp": {
                            "enabled": False 
                        }
                    },
                    "auth": {
                        "version2": {
                            "community": "public",
                            "enabled": True
                        },
                        "version3": {
                            "enabled": True,
                            "users": {
                            }
                        }
                    }
                }
            }
        self.mibs = MibResolver()
        self.traps = []
        self.trap_receiver_thread = TrapReceiverThread(self.config, self.mibs, self._trap_receiver_callback)
        self.trap_receiver_thread.setDaemon(1)
        self.trap_receiver_thread.start()

    def tearDown(self):
        self.traps = []
        self.trap_receiver_thread.stop()
        self.trap_receiver_thread.join()

    def send_trap(self, notification_trap, notification_args=None):
        if notification_args is None:
            notification_args = dict()
        return self.send_notification('trap', notification_trap, notification_args)

    def send_inform(self, notification_trap, notification_args=None):
        if notification_args is None:
            notification_args = dict()
        return self.send_notification('inform', notification_trap, notification_args)

    def send_notification(self, notify_type, notification_trap, notification_args):
        agent_host = self.config['snmp']['transport']['listen_address']
        agent_port = self.config['snmp']['transport']['listen_port']
        community = self.config['snmp']['auth']['version2']['community']

        # Initialize Notification Originator
        notifier = ntforg.NotificationOriginator()

        # Build Tarp Argument List
        varbinds = []
        for varName, val in notification_args.items():
            varbinds.append( (ntforg.MibVariable(*varName), val) )

        # Send Notification
        error = notifier.sendNotification(ntforg.CommunityData(community),
                    ntforg.UdpTransportTarget((agent_host, agent_port)),
                    notify_type,
                    ntforg.MibVariable(*notification_trap),
                    *varbinds)

        # Check if Notification was successfully sent
        if error:
            self.fail('Notification not sent: %s' % error)

        log.debug("Sent Trap: %s:%d %r" % (agent_host, agent_port, notification_trap))

        # stupid hack for race condition
        time.sleep(1)

    def _trap_receiver_callback(self, trap):
        self.traps.append(trap)
        log.debug("Recevied Trap: %r" % (trap))

    def assertTrapReceived(self, notification_trap, notification_args=None):
        if notification_args is None:
            notification_args = dict()
        result = False
        for trap in self.traps:
            if notification_trap == self.mibs.lookup_oid(trap.oid):
                for notification_arg_type, val in notification_args.items():
                    notification_arg_oid = self.mibs.lookup(*notification_arg_type)
                    self.assertTrue(notification_arg_oid in trap.arguments)
                    self.assertTrue(trap.arguments[notification_arg_oid] == val)
                result = True
        self.assertTrue(result, "trap not received (yet?)")

    def test_receive_trap(self):
        # send a trap
        self.send_trap(('SNMPv2-MIB', 'coldStart'), {('SNMPv2-MIB', 'sysName'): "whatup"})
        # make sure we got it
        self.assertTrapReceived(('SNMPv2-MIB', 'coldStart'), {('SNMPv2-MIB', 'sysName'): "whatup"})

if __name__ == "__main__":
    configure_log(logging.getLogger('sensu-trapd'))
    unittest.main()
