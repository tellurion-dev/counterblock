#! /usr/bin/env python
"""
counterblockd server
"""

#import before importing other modules
import gevent
from gevent import monkey; monkey.patch_all()

import sys
import os
import argparse
import json
import logging
import datetime
import time
import tempfile

from counterblock.lib import config, log, blockfeed, util, module, database
from counterblock.lib.processor import messages, caughtup, startup #to kick off processors
from counterblock.lib.processor import StartUpProcessor

logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments.
    parser = argparse.ArgumentParser(prog='counterblockd', description='Counterwallet daemon. Works with counterpartyd')

    #args
    parser.add_argument('-V', '--version', action='version', version="counterblockd v%s" % config.VERSION)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False, help='sets log level to DEBUG instead of WARNING')
    parser.add_argument('--reparse', action='store_true', default=False, help='force full re-initialization of the counterblockd database')
    parser.add_argument('--testnet', action='store_true', default=False, help='use Bitcoin testnet addresses and block numbers')
    
    parser.add_argument('--config-file', help='the location of the configuration file')
    parser.add_argument('--log-file', help='the location of the log file')
    parser.add_argument('--tx-log-file', help='the location of the transaction log file')
    parser.add_argument('--pid-file', help='the location of the pid file')

    #THINGS WE CONNECT TO
    parser.add_argument('--backend-connect', help='the hostname or IP of the backend bitcoind JSON-RPC server')
    parser.add_argument('--backend-port', type=int, help='the backend JSON-RPC port to connect to')
    parser.add_argument('--backend-user', help='the username used to communicate with backend over JSON-RPC')
    parser.add_argument('--backend-password', help='the password used to communicate with backend over JSON-RPC')

    parser.add_argument('--counterparty-connect', help='the hostname of the counterpartyd JSON-RPC server')
    parser.add_argument('--counterparty-port', type=int, help='the port used to communicate with counterpartyd over JSON-RPC')
    parser.add_argument('--counterparty-user', help='the username used to communicate with counterpartyd over JSON-RPC')
    parser.add_argument('--counterparty-password', help='the password used to communicate with counterpartyd over JSON-RPC')

    parser.add_argument('--mongodb-connect', help='the hostname of the mongodb server to connect to')
    parser.add_argument('--mongodb-port', type=int, help='the port used to communicate with mongodb')
    parser.add_argument('--mongodb-database', help='the mongodb database to connect to')
    parser.add_argument('--mongodb-user', help='the optional username used to communicate with mongodb')
    parser.add_argument('--mongodb-password', help='the optional password used to communicate with mongodb')

    parser.add_argument('--redis-enable-apicache', action='store_true', default=False, help='set to true to enable caching of API requests')
    parser.add_argument('--redis-connect', help='the hostname of the redis server to use for caching (if enabled')
    parser.add_argument('--redis-port', type=int, help='the port used to connect to the redis server for caching (if enabled)')
    parser.add_argument('--redis-database', type=int, help='the redis database ID (int) used to connect to the redis server for caching (if enabled)')

    #COUNTERBLOCK API
    parser.add_argument('--rpc-host', help='the IP of the interface to bind to for providing JSON-RPC API access (0.0.0.0 for all interfaces)')
    parser.add_argument('--rpc-port', type=int, help='port on which to provide the counterblockd JSON-RPC API')
    parser.add_argument('--rpc-allow-cors', action='store_true', default=True, help='Allow ajax cross domain request')

    #actions
    subparsers = parser.add_subparsers(dest='action', help='the action to be taken')
    parser_server = subparsers.add_parser('server', help='Run Counterblockd')
    parser_enmod = subparsers.add_parser('enmod', help='Enable a module')
    parser_enmod.add_argument('module_path', type=str, help='Full Path of module to Enable relative to Counterblockd directory')
    parser_dismod = subparsers.add_parser('dismod', help='Disable a module')
    parser_dismod.add_argument('module_path', type=str, help='Path of module to Disable relative to Counterblockd directory')
    parser_listmod = subparsers.add_parser('listmod', help='Display Module Config')
    parser_rollback = subparsers.add_parser('rollback', help='Rollback to a specific block number')
    parser_rollback.add_argument('block_index', type=int, help='Block index to roll back to')

    #default to server arg
    if len(sys.argv) < 2: sys.argv.append('server')
    if not [i for i in sys.argv if i in ('server', 'enmod', 'dismod', 'listmod', 'rollback')]:
        sys.argv.append('server')

    args = parser.parse_args()

    config.init(args)
    log.set_up(args.verbose)
    
    #Log unhandled errors.
    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("Unhandled Exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.excepthook = handle_exception    

    #Create/update pid file
    pid = str(os.getpid())
    pidf = open(config.PID, 'w')
    pidf.write(pid)
    pidf.close()    

    #load any 3rd party modules
    module.load_all()

    #Handle arguments
    if args.action == 'enmod':
        module.toggle(args.module_path, True)
        sys.exit(0)
    elif args.action == 'dismod': 
        module.toggle(args.module_path, False)
        sys.exit(0)
    elif args.action == 'listmod':
        module.list_all()
        sys.exit(0)
    elif args.action == 'rollback':
        assert args.block_index >= 1
        startup.init_mongo()
        database.rollback(args.block_index)
        sys.exit(0)
        
    logger.info("counterblock Version %s starting ..." % config.VERSION)
    
    #Run Startup Functions
    StartUpProcessor.run_active_functions()

if __name__ == '__main__':
    main()
