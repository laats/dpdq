#!/usr/bin/env python
################################################################################
#
# File:         riskserver.py
# RCS:          $Header: $
# Description:
#               Info about users:
#                 indexed by fp
#                 [total threshold (tt), per query threshold (qt),
#                 history = [(increment, time)]]
#               query types
#                 0. check user, eps => res = (eps + sum(increment) < tt) and
#                                             (eps < qt)
#                                       if res: add (eps, now) to history
#                                       else: return res
#                    restriction: server
#                 1. get user => sum, tt, qt
#                    restriction: server, user
#                 Errors:
#                         0. None
#                         1. credentials failed 
#                         2. malformed query
#                         3. internal error
#                 
# Author:       Staal Vinterbo
# Created:      Thu Apr 11 16:26:37 2013
# Modified:     Mon Jun 24 09:46:45 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# dpdq_rserver.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# dpdq_rserver.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dpdq_rserver.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################



if __name__ == "__main__":    
    import sys
    import argparse as ap
    import logging
    from twisted.internet import reactor
    import gnupg

    from dpdq import Version
    from dpdq.ra.policy import policy, policies
    from dpdq.ra.rproto import init_factory

    parser = ap.ArgumentParser(description=('Risk Accounting Server (version: ' + Version +').\n' +
                                            "This program answers requests about users' privacy risk history and " +
                                            "whether a user is allowed to incur further risk according to the current risk policy."))
    parser.add_argument("database_url", type=str, 
                    help = 'The RFC 1738 style url pointing to the risk database.'
    ' The format is dialect+driver://username:password@host:port/database.')
    parser.add_argument("-k", "--key", type=str, default='RiskAccountant',
                        help = 'the key identity for the risk accountant user (default: "%(default)s").')
    parser.add_argument("-P", "--risk_server_port", type=int, default=8124,
                        help = 'the ip address port the risk accountant listens for requests on (default: %(default)d).')
    parser.add_argument("-e", "--enforce_policy", default=policy, choices=policies.keys(),
                        help = 'risk management policy to enforce (default: "%(default)s").')
    parser.add_argument('-g', "--gpghome", type=str, default='.',
                        help = 'the folder in which to find key ring files (default: "%(default)s").')
    parser.add_argument("-l", "--logfile", type=str, default='risk.log',
                        help = 'the file information about transactions and the'
        ' state of the accountant is written to (default: "%(default)s").')
    parser.add_argument("-m", "--module", type=str, default=None,
                        help = 'a python module that contains additional policies (default: "%(default)s").')
    parser.add_argument('-v', "--version", action='store_true',
                        help = 'display version number and exit.')


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)

    logging.basicConfig(filename=args.logfile,level=logging.INFO,
                        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')

    gpg = gnupg.GPG(gnupghome=args.gpghome)
   
    print "Starting Risk Accountant! "
    print "GPG directory:", args.gpghome
    print "key :", args.key
    print "risk database:", args.database_url
    print "port:", args.risk_server_port
    print "policy:", args.enforce_policy

    factory = init_factory(gpg, args.key, args.database_url,
                           args.enforce_policy, args.module)

    reactor.listenTCP(args.risk_server_port, factory)
    reactor.run()
    

