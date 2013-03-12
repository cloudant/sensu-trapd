import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sensu.snmp.mib import MibResolver

# helpers
from helpers.log import log

class MibResolverTestCase(unittest.TestCase):

    def setUp(self):
        self.mibs = MibResolver()

    def tearDown(self):
        del self.mibs

    def test_load_mib_source(self):
        pass

    def test_load_mib(self):
        pass

    def test_lookup(self):
        snmp_trap_oid = (1, 3, 6, 1, 6, 3, 1, 1, 4, 1)
        self.assertEquals(self.mibs.lookup('SNMPv2-MIB', 'snmpTrapOID'), snmp_trap_oid)

    def test_lookup_oid(self):
        snmp_trap_oid = (1, 3, 6, 1, 6, 3, 1, 1, 4, 1)
        self.assertEquals(self.mibs.lookup_oid(snmp_trap_oid), ('SNMPv2-MIB', 'snmpTrapOID'))

    def test_lookup_oid_unknown(self):
        unknown_oid = (1, 2, 3, 4, 5, 6)
        #self.assertRaises(NoSuchObjectError, self.mibs.lookup_oid, unknown_oid)

if __name__ == "__main__":
    unittest.main()
