#!/usr/bin/env python
################################################################################
#
# File:         client.py
# RCS:          $Header: $
# Description:  Encrypted echo client
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 20:32:04 2013
# Modified:     Tue Jun 25 13:33:20 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# dpdq_cli.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# dpdq_cli.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dpdq_cli.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################


if __name__ == '__main__':
    import sys
    import argparse as ap
    from dpdq import Version
    from urlparse import urlparse
    from os import environ, getcwd
    import gnupg

    from twisted.internet import reactor
    from dpdq.cl.cproto import init_factory


    parser = ap.ArgumentParser(description=(('Text based query client (version: %(s)s).\n' % {'s':str(Version)}) +
                                            'This program allows requesting information from and about datasets '+
                                            'from a query processing server.'))
    parser.add_argument("-k", "--key", type=str, default='Alice',
                        help = 'the key identifier for the user this client acts on behalf of (default: "%(default)s").')
    parser.add_argument("-s", "--query_server_key", type=str, default='QueryServer',
                        help = 'the key identifier for the query server user (default: "%(default)s").')
    parser.add_argument("-a", "--query_server_address", type=str, default='localhost',
                        help = 'the query server ip address (default: "%(default)s").')
    parser.add_argument("-p", "--query_server_port", type=int, default=8123,
                        help = 'the query server ip address port (default: %(default)d).')
    parser.add_argument('-g', "--gpghome", type=str, default='.',
                        help = 'the directory in which to find key ring files (default: "%(default)s").')
    parser.add_argument('-u', "--user", type=str, default=None,
                        help = 'the user alias to act on behalf on (default: "%(default)s").')
    parser.add_argument('-f', "--filter", action='store_true',
                        help = 'act like a filter: read commands from stdin and print output to stdout.'
        ' This is useful for batch execution of commands.')
    parser.add_argument('-v', "--version", action='store_true', 
                        help = 'display version number and exit.')
    parser.add_argument('-n', "--nowrite", action='store_true', 
                        help = 'disallow writing results to file.')
    parser.add_argument('-d', "--debug", action='store_true', 
                        help = 'display debug info.')


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)
    

    if args.debug:
        print 'env', environ
        print 'cwd', getcwd()
        print 'arguments:', vars(args)

    alias = None
    gpg = gnupg.GPG(gnupghome=args.gpghome)
        

    if args.debug:
        print "Starting!"
        print "gpghome:", args.gpghome
        print "key identity:", args.key
        print "server key identity:", args.query_server_key
        print "server address:", args.query_server_address
        print "server port:", args.query_server_port
        print "user:", args.user
        
    try:
        factory = init_factory(gpg, args.key, args.query_server_key,
                               silent = args.filter,
                               alias = args.user,
                               allow_write=not args.nowrite)

        reactor.connectTCP(args.query_server_address, args.query_server_port,
                           factory)
        reactor.run()
    except Exception as e:
        s = str(e).strip().split(':')[-1]
        print s, 'Bye.'
        sys.exit(1)
