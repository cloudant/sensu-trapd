import os
import sys
import time
import simplejson as json

from sensu.snmp.log import log
from sensu.snmp.handler import TrapHandler
from sensu.snmp.receiver import TrapReceiverThread
from sensu.snmp.dispatcher import TrapEventDispatcherThread

class SensuSNMPServer(object):

    def __init__(self, config):
        self._config = config
        self._run = False

        # Initialize TrapReceiverThread
        self._trap_receiver_thread = TrapReceiverThread(self._config, self._handle_trap)

        # Initialize TrapEventDispatcher
        self._trap_event_dispatcher_thread = TrapEventDispatcherThread(self._config)

        # Configure Trap Handlers
        self._trap_handlers = self._configure_trap_handlers(self._config['daemon']['trap_file'])

        log.debug("SensuSNMPServer: Initialized")

    def _configure_trap_handlers(self, trap_file):
        log.debug("SesnuSNMPServer: Parsing trap handler file: %s" % (trap_file))
        trap_handlers = dict()
        try:
            fh = open(trap_file, 'r')
            trap_file_data = json.load(fh)
            for trap_handler_id, trap_handler_config in trap_file_data.items():
                # Parse TrapHandler
                trap_handler = TrapHandler.parse(trap_handler_config)
                trap_handlers[trap_handler_id] = trap_handler
                log.debug("SensuSNMPServer: Parsed trap handler: %s" % (trap_handler_id))
        finally:
            fh.close()
        return trap_handlers

    def _dispatch_trap_event(self, trap_event):
        self._trap_event_dispatcher_thread.dispatch(trap_event)

    def _handle_trap(self, trap):
        log.info("SensuSNMPServer: Received Trap: %s" % (trap.trap))
        # Load trap handler
        trap_handler = None
        for trap_handler_id, th in self._trap_handlers.items():
            if th.trap == trap.trap:
                log.debug("SensuSNMPServer: Trap Handler found: %s" % (trap_handler_id))
                trap_handler = th

        if trap_handler is None:
            log.warning("No trap handler defined for %s" % (trap.trap))
            return


        event = trap_handler.process_trap(trap)
        self._dispatch_trap_event(event)

    def stop(self):
        if not self._run:
            return
        self._run = False

        # Stop TrapReceiverThread
        self._trap_receiver_thread.stop()

        # Stop TrapEventDispatcherThread
        self._trap_event_dispatcher_thread.stop()

    def run(self):
        log.debug("SensuSNMPServer: started")
        self._run = True

        # Start TrapReceiverThread
        self._trap_receiver_thread.start()

        # Start TrapEventDispatcherThread
        self._trap_event_dispatcher_thread.start()

        while self._run:
            time.sleep(1)

        # Wait for our threads to stop
        self._trap_receiver_thread.join()
        self._trap_event_dispatcher_thread.join()
        log.debug("SensuSNMPServer: exiting")
