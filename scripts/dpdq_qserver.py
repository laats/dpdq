#!/usr/bin/env python
################################################################################
#
# File:         queryserver.py
# RCS:          $Header: $
# Description:  Encrypted query server, by default echo. Handles multiple clients
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 16:05:34 2013
# Modified:     Mon Jun 24 12:05:27 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# dpdq_qserver.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# dpdq_qserver.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dpdq_qserver.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['ServerFactory']

from dpdq.qp.qprotos import init_factory, Address


if __name__ == "__main__":    
    import sys
    import argparse as ap
    import logging    
    from dpdq.qp.processors_fs import processors
    from dpdq.gpgutils import findfp
    from dpdq import Version
    import os
    import gnupg
    from twisted.internet import reactor

    from dpdq.qp.qprotos import load_mod
    from logging import info


    parser = ap.ArgumentParser(description=('Query processing server (version: ' + Version + ').' +
                                            '\nThis program allows clients to request information about datasets in ' +
                                            'the database it is connected to. As these requests potentially carry privacy ' +
                                            'risk, a risk accountant is queried for adherence to the current risk policy ' +
                                            'before serving the information to the client.'))
    parser.add_argument("database_url", type=str, 
                        help = 'The RFC 1738 style url pointing to the database.'
        ' The format is dialect+driver://username:password@host:port/database.')
    parser.add_argument("-k", "--key", type=str, default='QueryServer',
                        help = 'the key identity of the query server user (default: "%(default)s").')
    parser.add_argument("-g", "--gpghome", type=str, default='.',
                        help = 'the folder in which to find key ring files (default: "%(default)s").')
    parser.add_argument('-p', "--query_server_port", type=int, default=8123,
                        help = 'the ip address port the query processing server will listen to client requests on (default: %(default)d).')
    parser.add_argument("-S", "--risk_server_key", type=str, default='RiskAccountant',
                        help = 'the key identity for the risk accountant server user (default: "%(default)s").')
    parser.add_argument("-A", "--risk_server_address", type=str, default='localhost',
                        help = 'the risk accountant server address (default: "%(default)s").')
    parser.add_argument("-P", "--risk_server_port", type=int, default=8124,
                        help = 'the port the risk accountant server listens on (default: %(default)d).')
    parser.add_argument("-l", "--logfile", type=str, default='query.log',
                        help = 'the file that information about the state of the query processing server'
        ' and communications with both clients and the risk accountant is written to (default: "%(default)s").')
    parser.add_argument("-q", "--querymodule", type=str, default=None,
                        help = 'a python module that contains additional query type processors (default: "%(default)s").')
    parser.add_argument('-v', "--version", action='store_true',
                        help = 'display version number and exit.')
    parser.add_argument("--allow_alias", action='store_true',
                        help = 'Allow connecting clients to query on behalf of another user. ' 
                        'This should only be allowed if the client is trusted, e.g., implements external'
                        ' identification and authentication.')
    parser.add_argument("--allow_echo", action='store_true',
                        help = 'Allow echo requests.' 
                        ' Useful for debugging clients.')


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)

    logging.basicConfig(filename=args.logfile,
                        level=logging.INFO,
                        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')

    try:
        if args.querymodule != None:
            module = load_mod(args.querymodule)
            processors.update(module.processors)
            info('added query types: ' + ' '.join(module.processors.keys()))
    except Exception as e:
        print 'Failed to load query types on startup:', str(e)
        print 'cwd: ', os.getcwd()

 
    try:
        gpg = gnupg.GPG(gnupghome=args.gpghome)
        print "Starting! "
        print "gpghome:", args.gpghome
        print "me:", args.key
        print "port:", args.query_server_port
        print "risk accountant:", args.risk_server_key
        print "risk accountant address", (args.risk_server_address +
                                          ':' + str(args.risk_server_port))

        ra_address = Address(args.risk_server_address, args.risk_server_port)
        factory = init_factory(gpg, # initialized gpg
                               args.key,  # my name
                               args.risk_server_key, # risk accountants name
                               args.database_url,   # database ulr
                               processors, # list of processors
                               ra_address, # the address of the RA
                               args.allow_alias, 
                               args.allow_echo, 
                               args.querymodule) 

    except Exception as e:
        sys.stderr.write('Initialization error: ' + str(e) + '\n')
        sys.exit(1)
        
    reactor.listenTCP(args.query_server_port, factory)
    reactor.run()
