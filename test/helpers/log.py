import sys
import logging

log = logging.getLogger('sensu-trapd.tests')

def configure_log(log, log_level="DEBUG"):
    # Clear existing log handlers
    log.handlers = []

    # Configure Log Formatting
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')

    # Configure Log Handler
    streamhandler = logging.StreamHandler(sys.stdout)
    streamhandler.setFormatter(formatter)
    log.addHandler(streamhandler)

    # Configure Logging Level
    try:
        log.setLevel(getattr(logging, log_level))
    except AttributeError:
        log.warn("Unknown logging level: %s" % (log_level))
        log.setLevel(logging.INFO)

