# sensu-trapd
* * *

Sensu Trap Daemon

sensu-trapd is a SNMP trap receiver that translates SNMP traps to Sensu events.
It is designed to listen for SNMP traps and dispatch Sensu events based on a
preconfigured set of mappings (see Configuration).

# Requirements
* * *

pysnmp >= 4.2.4

# Installation
* * *

Sensu-trapd can be installed from source using its Makefile:

```
make install
```

Sensu-trapd can also be packaged to deb's (and hopefully RPMs at some point):

```
make deb
```

For more installation information see the Makefile.

# Configuration
* * *

### Converting MIBs for PySNMP

For sensu-trapd to translate a trap, it must have a corresponding MIB defining
that trap loaded. PySNMP (which sensu-trapd uses as a trap receiver), requires
that MIBs be converted into a special format before being loaded into
sensu-trapd. Fortunately, PySNMP provides a utility to do this:

Note: Make you have PySNMP installed, and the "build-pysnmp-mib" is in your path.

```
build-pysnmp-mib -o /some/destination/path/CLOUDANT-CLOUSEAU-MIB.py /some/source/path/CLOUDANT-CLOUSEAU-MIB.txt
```

These MIBs will be automatically loaded by sensu-trapd if they are put into
a directory listed in the sensu-trapd config file under the mibs/paths section,
and also in the in the mibs/mibs section (See Example Configuration).

### Configuring Daemon

Sensu-trapd is configured using the conf/config.json file. Additionally, some
configuration can be specified on the command line. See the help for more info.

### Configuring Traps

Traps are configured using the conf/traps.json (unless another file is specified
in conf/config.json).

### Basic Trap Configuration
```
"some-unique-name-for-trap-handler": {
    "trap": {
        "type": ["SOME-AWESOME-MIB", "someTrapObject"],
        "args": {
            "first": ["SOME-AWESOME-MIB", "someTrapArgument"]
            "second": ["SOME-AWESOME-MIB", "someOtherTrapArgument"]
        }
    },
    "event": {
        "name": "{hostname} Some Check Name",
        "output": "{first}",
        "handlers": ["some-handler", "another-handler"],
        "severity": "CRITICAL"
    }
}
```

In the example above, I've configured sensu-trapd to handle the
SOME-AWESOME-MIB::someTrapObject trap. This trap has two trap arguments that
get mapped to names "first" and "second". These mappings can then be used for
substitutions in the event that it sent to Sensu.

In the event section of the trap configuration, you must specific a check name.
This will be used by Sensu as the name of the check, so make it meaningful.

Additionally, you can specify the output of the check, handlers, and severity of
the event. 

Note: If a trap as optional arguments, you must specify a trap handler for
each trap both with and without arguments.

### Example Basic Trap Configuration
```
"cloudant-generic-trap-handler": {
    "trap": {
        "type": ["CLOUDANT-PLATFORM-MIB", "cloudantGenericTrap"],
        "args": {
            "message": ["CLOUDANT-PLATFORM-MIB","cloudantTrapMessage"]
        }
    },
    "event": {
        "name": "{hostname} Cloudant Generic Event",
        "output": "{message}",
        "handlers": ["debug"],
        "severity": "CRITICAL"
    }
}
```

### Example Advanced Trap Configuration

In this example, note that I've mapped two traps to the same event. This allows
events to recover/resolve when an UP trap is received after a corresponding DOWN
trap is received.

```
"cloudant-loadbalancer-server-up": {
    "trap": {
        "type": ["CLOUDANT-LOADBALANCER-MIB", "cloudantLoadBalancerServerUp"],
        "args": {
            "message": ["CLOUDANT-PLATFORM-MIB","cloudantTrapMessage"]
        }
    },
    "event": {
        "name": "Load Balancer Server Down",
        "output": "{hostname} reports {message}",
        "handlers": ["default"],
        "severity": "OK"
    }
},
"cloudant-loadbalancer-server-down": {
    "trap": {
        "type": ["CLOUDANT-LOADBALANCER-MIB", "cloudantLoadBalancerServerDown"],
        "args": {
            "message": ["CLOUDANT-PLATFORM-MIB","cloudantTrapMessage"]
        }
    },
    "event": {
        "name": "Load Balancer Server Down",
        "output": "{hostname} reports {message}",
        "handlers": ["default"],
        "severity": "WARNING"
    }
}
```

### Example Configuration
```
{
    "daemon": {
        "log_file":     "/var/log/sensu/sensu-trapd.log",
        "log_level":    "DEBUG",
        "user":         "sensu",
        "group":        "sensu",
        "trap_file":    "/opt/sensu-trapd/conf/traps.json"
    },
    "dispatcher": {
        "host":             "localhost",
        "port":             3030,
        "timeout":          5,
        "events_log":       "/var/log/sensu/sensu-trapd-events.log"
    },
    "mibs": {
        "paths": ["/opt/sensu-trapd/conf/mibs"],
        "mibs": ["CLOUDANT-REG-MIB",
                 "CLOUDANT-PLATFORM-MIB",
                 "CLOUDANT-DBCORE-MIB",
                 "CLOUDANT-LOADBALANCER-MIB"]
    },
    "snmp": {
        "transport": {
            "listen_address":   "127.0.0.1",
            "listen_port":      1161,
            "udp": {
                "enabled": true
            },
            "tcp": {
                "enabled": true
            }
        },
        "auth": {
            "version2": {
                "enabled":      true,
                "community":    "supersecretcommunity"
            },
            "version3": {
                "enabled":      true,
                "users": {
                    "test-user": {
                        "authentication": {
                            "protocol": "MD5",
                            "password": "myAuthSecret"
                        },
                        "privacy": {
                            "protocol": "DES",
                            "password": "myPrivSecret"
                        }
                    }
                }
            }
        }
    }
}
```
