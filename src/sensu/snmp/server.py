import os
import sys
import time
import simplejson as json

from sensu.snmp.log import log
from sensu.snmp.handler import TrapHandler
from sensu.snmp.receiver import TrapReceiverThread
from sensu.snmp.dispatcher import TrapEventDispatcherThread

class Server(object):

    def __init__(self, config):
        self._config = config
        self._run = False

        # Initialize TrapReceiverThread
        self._trap_receiver_thread = TrapReceiverThread(self._config, self._handle_trap)

        # Initialize TrapEventDispatcher
        self._trap_event_dispatcher_thread = TrapEventDispatcherThread(self._config)

        # Configure Trap Handlers
        self._trap_handlers = self._configure_trap_handlers(self._config['daemon']['trap_file'])

        log.debug("Initialized Server")

    def _configure_trap_handlers(self, trap_file):
        log.debug("Parsing trap handler file: %s" % (trap_file))
        trap_handlers = dict()
        try:
            fh = open(trap_file, 'r')
            trap_file_data = json.load(fh)
            for trap_handler_name, trap_handler_config in trap_file_data.items():
                trap = trap_handler_config['trap'] if 'trap' in trap_handler_config else 'default'
                trap_handlers[trap] = TrapHandler.parse(trap_handler_name, trap_handler_config)
                log.debug("Parsed trap handler: %s" % (trap_handler_name))
        finally:
            fh.close()
        return trap_handlers

    def _dispatch_trap_event(self, trap_event):
        self._trap_event_dispatcher_thread.dispatch(trap_event)

    def _handle_trap(self, trap):
        # Load trap handler
        trap_handler = None
        if trap.name in self._trap_handlers:
            trap_handler = self._trap_handlers[trap.name]
        else:
            trap_handler = self._trap_handlers['default']
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
        log.debug("Server started")
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
        log.debug("Server exiting")
