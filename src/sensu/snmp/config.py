from copy import deepcopy
import simplejson as json

DEFAULT_CONFIG = {
        "daemon": {
            "log_file":     "sensu-trapd.log",
            "log_level":    "INFO",
            "pid_file":     "sensu-trapd.pid",
            "user":         "nobody",
            "group":        "nogroup",
            "trap_file":    "conf/traps.json"
        },
        "dispatcher": {
            "host":             "127.0.0.1",
            "port":             3030,
            "timeout":          5,
            "backoff":          10,
            "check_response":   False,
            "events_log":       "sensu-trapd-events.log"
        },
        "mibs": {
            "paths": [],
            "mibs":  []
        },
        "snmp": {
            "transport": {
                "listen_address":   "127.0.0.1",
                "listen_port":      1610,
                "udp": {
                    "enabled": True
                },
                "tcp": {
                    "enabled": False
                }
            },
            "auth": {
                "version2": {
                    "enabled": False,
                },
                "version3": {
                    "enabled": False,
                    "users": {
                    }
                }
            }
        }
    }

def load_config(configfile):
    fh = open(configfile)
    try:
        config = _merge_config(DEFAULT_CONFIG, json.load(fh))
        return config
    finally:
        fh.close()

def _merge_config(a, b):
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
            result[k] = _merge_config(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result
