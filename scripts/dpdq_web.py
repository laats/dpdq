#!/usr/bin/env python
################################################################################
#
# File:         skeleton.py
# RCS:          $Header: $
# Description:  Web interface, uses Jinja2 templating
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 20:32:04 2013
# Modified:     Fri Jul  5 11:03:16 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# skeleton.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# skeleton.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with skeleton.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

#### globals

if __name__ == '__main__':

    from twisted.web import server
    from twisted.internet import reactor
    from dpdq.wc.resource import init_resource

    import sys
    import argparse as ap
    from dpdq import Version
    import urllib2
    from os import environ, getcwd
    from pprint import pprint
    from ast import literal_eval

    known_host = 'localhost:8123'

    parser = ap.ArgumentParser(
            description=(
                ('DPDQ web server (version: %(s)s).\n' %
                 {'s':str(Version)}) +
                'This program starts a Twisted web server that '
                'allows connecting clients to request information'
                ' from and about datasets '+ 
                'from a query processing server.'))
    parser.add_argument("-k", "--key", type=str, default='Alice',
                        help = 'the key identifier for the user this'
                        ' client acts on behalf of (default: "%(default)s").')
    parser.add_argument("-s", "--query_server_key", type=str,
                        default='QueryServer',
                        help = 'the key identifier for the query server'
                        ' user (default: "%(default)s").')
    parser.add_argument("-p", "--port", type=int, default=8082,
                        help = 'the webserver port (default: %(default)d).')
    parser.add_argument('-g', "--gpghome", type=str, default='.',
                        help = 'the directory in which to find key ring'
                        ' files (default: "%(default)s").')
    parser.add_argument('-f', "--hostsfile", type=str, default=None,
                        help = 'URL pointing to known hosts python dict.')
    parser.add_argument('-i', "--infopage", type=str,
                        default='http://ptg.ucsd.edu/~staal/dpdq',
                        help = 'URL pointing to the DPDQ homepage. '
                        'Used in the help dialog to point to more information.'
                        ' If not supplied %(default)s is used.')
    parser.add_argument('-v', "--version", action='store_true', 
                        help = 'display version number and exit.')
    parser.add_argument('-d', "--debug", action='store_true', 
                        help = 'display debug info.')


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)

    known_hosts = { known_host : 'Demo' }    

    if args.hostsfile:
        try:
            known_hosts = literal_eval(urllib2.urlopen(args.hostfile))
        except Exception as e:
            sys.stderr.write('Could not initialize known_hosts: ' +
                             str(e) + '\n')
            sys.exit(1)

    if args.debug:
        print 'env', environ
        print 'cwd', getcwd()
        print 'arguments:', vars(args)
        print 'known hosts:'
        pprint(known_hosts)


    try:
        root = init_resource(args.gpghome, args.key, args.query_server_key,
                             known_hosts, args.infopage)
    except Exception as e:
        sys.stderr.write('Could not initialize web server: ' +
                         str(e) + '\n')
        sys.exit(1)

    # start twisted web server here:
    reactor.listenTCP(args.port, server.Site(root))
    reactor.run()
