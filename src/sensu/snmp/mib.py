import pysnmp.smi.builder
import pysnmp.smi.view
import pysnmp.entity.rfc3413.mibvar
import pysnmp.proto.rfc1902

from sensu.snmp.log import log

class MibResolver(object):

    DEFAULT_MIB_PATHS = []
    DEFAULT_MIB_LIST = ['SNMPv2-MIB', 'SNMP-COMMUNITY-MIB']

    def __init__(self, mib_paths=None, mib_list=None):
        if mib_paths is None:
            mib_paths = []
        if mib_list is None:
            mib_list = []

        # Initialize mib MibBuilder
        self._mib_builder = pysnmp.smi.builder.MibBuilder()

        # Configure MIB sources
        self._mib_sources = self._mib_builder.getMibSources()

        # Load default mib dirs
        for path in self.DEFAULT_MIB_PATHS + mib_paths:
            self.load_mib_dir(path)
        # Load default mibs
        for mib in self.DEFAULT_MIB_LIST + mib_list:
            self.load_mib(mib)

        # Initialize MibViewController
        self._mib_view = pysnmp.smi.view.MibViewController(self._mib_builder)
        log.debug("MibResolver: Initialized")

    def load_mib_dir(self, path):
        self._mib_sources += (pysnmp.smi.builder.DirMibSource(path),)
        log.debug("MibResolver: Loaded MIB source: %s" % path)
        self._mib_builder.setMibSources(*self._mib_sources)

    def load_mib(self, mib):
        self._mib_builder.loadModules(mib, )
        log.debug("MibResolver: Loaded MIB: %s" % mib)

    def lookup(self, module, symbol):
        name = ((module,symbol),)
        oid,suffix = pysnmp.entity.rfc3413.mibvar.mibNameToOid(self._mib_view, name)
        return pysnmp.proto.rfc1902.ObjectName(oid)

    def lookup_oid(self, oid):
        (symbol, module), indices = pysnmp.entity.rfc3413.mibvar.oidToMibName(self._mib_view, oid)
        return (module, symbol)

    def lookup_value(self, module, symbol, value):
        return pysnmp.entity.rfc3413.mibvar.cloneFromMibValue(self._mib_view, module, symbol, value)
