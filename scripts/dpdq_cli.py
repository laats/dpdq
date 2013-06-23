#!/usr/bin/env python
################################################################################
#
# File:         client.py
# RCS:          $Header: $
# Description:  Encrypted echo client
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 20:32:04 2013
# Modified:     Sun Jun 23 15:25:36 2013 (Staal Vinterbo) staal@mats
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

from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import reactor
from sys import stdout,stdin
import re
import gnupg
from ast import literal_eval
from dpdq.cl.cli import Cli
from texttable import Texttable

# copied from dpdq_qserver.py
QTYPE_META = 0
QTYPE_INFO = 1
QTYPE_RISK = 2
QTYPE_MAX = 2

STATUS_OK = 0
STATUS_ERROR_BUDGET = 1
STATUS_ERROR_RA = 2
STATUS_ERROR_QUERY = 3
STATUS_ERROR_INTERNAL = 4

greeting = '''
Welcome to the text-based query client.
This client will help you compose a query for information on a dataset.

A query consists of:

- the dataset of interest
- the columns (variables) in that dataset of interest (at least one is needed)
- the predicate determining wanted dataset rows
- the type of query (wanted type of information)
- the value of any parameters for that query type
- the epsilon quantifying differential privacy risk you allow

Each of the above have an associated command, and once at least a dataset
and a query type have been selected, the query can be run.

If your system allows it, this client will use TAB completion. This means that
pressing TAB will complete what you are currently typing if there is a unique
way to do so. If there is no unique completion, pressing TAB again will list
all possible completions of what you are currently typing.

Type 'help' at the command prompt to see available commands.
'''

outp = '''
from random import uniform
def trans(s):
    if type(s) == str:
        if s[0] == '[' and s[-1] == ')':
            x = eval('slice(' + s[1:]) 
            return uniform(x.start, x.stop)
    return s
    
def tlist(res):
    l = [res['setup']['columns']]
    for tup,mult in res['response'].items():
        for i in range(mult):
            l.append(map(trans, tup))
    return l

if __name__ == '__main__':
    import sys
    import csv
    if response['setup']['type'] == 'histogram':
        writer = csv.writer(sys.stdout)
        writer.writerows(tlist(response))
    else: sys.stdout.write(str(response) + '\\n')
'''


class TextClient(NetstringReceiver):

    def __init__(self, serverkey, mykey, gpg, use_raw = True,
                 allow_write=True, alias = None):
        self.serverkey = serverkey
        self.mykey = mykey
        self.gpg = gpg
        self.new_meta = False
        self.meta = {}
        self.cli = None
        self.use_raw = use_raw
        self.allow_write = allow_write
        self.alias = alias
    
    def stringReceived(self, data):

        clear_in = self.gpg.decrypt(data)

        if not clear_in.valid:
            stdout.write('Response not valid!\n')
            self.transport.loseConnection()
            return

        (status, qtype, response) = literal_eval(str(clear_in))
        
        if status == STATUS_ERROR_INTERNAL:
            sys.stderr.write('Query server suffered internal problems. Signing off.\n')
            self.transport.loseConnection()
            return

        if qtype == QTYPE_META:
            if status != STATUS_OK:
                sys.stderr.write('Could not get metadata: ' + str((status,response)) + '\n')
                sys.stderr.write('Signing off.\n')
                self.transport.loseConnection()
                return
            self.meta = response

        if qtype == QTYPE_RISK:
            if status != STATUS_OK:
                sys.stderr.write('Could not get risk information: ' + str((status,response)) + '\n')
                sys.stderr.write('Signing off.\n')
                self.transport.loseConnection()
                return
            stdout.write('Total risk accumulated: ' + str(response['total']) + '\n'
                         'Cumulative max allowed risk: ' + str(response['tt']) + '\n'
                         'Per query allowed risk: ' + str(response['qt']) + '\n')

        if qtype == QTYPE_INFO:
            if type(response) == dict:
                if not self.cli.type == 'histogram':
                    for k,v in sorted(response.items()):
                        stdout.write(str(k) + ": " + str(v) + '\n')
                else:
                    #header = self.cli.project + ['count']
                    header = response['col_names'] + ['count']
                    hlen = len(header)
                    table = Texttable()
                    table.set_deco(Texttable.HEADER)
                    table.set_cols_align(["l"]*(hlen - 1) + ['r'])
                    table.set_cols_valign(["m"]*hlen)
                    table.set_cols_dtype((['t']*(hlen - 1)) + ['i'])
                    table.header(header)
                    table.add_rows(
                        map(lambda (k,v) : list(k) + [v],
                            sorted(response['histogram'].items(),
                                   key = lambda (_,x) : x, reverse=True)),
                        header=False)
                    print table.draw() + '\n'
            else:
                stdout.write(str(response) + '\n')
                
            if self.allow_write and self.cli.outfile != None and self.cli.outfile != '':
                try:
                    if self.cli.outfile == '-':
                        f = sys.stdout
                    else:
                        f = open(self.cli.outfile, 'a')
                    fields = [self.cli.data,
                              self.cli.project,
                              self.cli.expr,
                              self.cli.eps,
                              self.cli.type,
                              self.cli.params]
                    fnames = [
                        'dataset',
                        'columns',
                        'predicate',
                        'epsilon',
                        'type',
                        'parameters']
                    outdict = {
                        'setup' : dict(zip(fnames, fields)),
                        'response' : response
                    }
                    f.write('response =' + str(outdict) + '\n' + outp)
                    if f != sys.stdout: f.close()
                except Exception as e:
                    print 'Could not write reponse to ' + self.cli.outfile + ', ' + str(e)
                else:
                    print 'Wrote response to ' + self.cli.outfile
                self.cli.outfile = None

        if qtype > QTYPE_MAX:
            print 'Protocol error: Query server sent unknown query type response:', qtype
            print 'status:', status
            print 'response:', str(response)
                    
        if self.cli == None:
            self.cli = Cli(self.meta)
            self.cli.use_rawinput = self.use_raw
            if not self.use_raw:
                self.cli.prompt = ''
        self.cli.cmdloop()
        if self.cli.exit:
            if self.use_raw:
                print 'disconnecting...'
            self.transport.loseConnection()
            return

        if self.cli.qtype == 'info':
            message = str((QTYPE_INFO, self.alias, self.cli.eps,
                           ((self.cli.data, self.cli.select, self.cli.project),(self.cli.type, self.cli.params.items()))))
        elif self.cli.qtype == 'risk':
            message = str((QTYPE_RISK, self.alias, 0, None))
            
        self.sendString(str(self.gpg.encrypt(message, self.serverkey, sign=self.mykey)))

    def connectionMade(self):
        if self.use_raw:
            stdout.write('Getting metadata...\n')
            print greeting
        message = str((QTYPE_META,self.alias, 0,0))
        self.sendString(str(self.gpg.encrypt(message, self.serverkey, sign=self.mykey)))

        


class TextClientFactory(ClientFactory):

    def __init__(self, serverkey, mykey, gpg, use_raw = True,
                 allow_write=True, alias = None):
        self.serverkey = serverkey
        self.mykey = mykey
        self.gpg = gpg
        self.use_raw = use_raw
        self.allow_write = allow_write
        self.alias = alias
    
    def startedConnecting(self, connector):
        if self.use_raw:
            print 'Started to connect.'

    def buildProtocol(self, addr):
        if self.use_raw:
            print 'Connected.'
        return TextClient(self.serverkey, self.mykey, self.gpg, self.use_raw,
                          allow_write = self.allow_write,
                          alias = self.alias)

    def clientConnectionLost(self, connector, reason):
        if self.use_raw:
            print 'disconnected.'
        if reactor.running:
            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        print str(reason).split(':')[-1][:-1].strip()        
        reactor.stop()



if __name__ == '__main__':
    import sys
    import argparse as ap
    from dpdq.gpgutils import findfp
    from dpdq import Version
    from urlparse import urlparse
    from os import environ, getcwd

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
    parser.add_argument('-U', "--url", type=str, default=None,
                        help = 'url with query section for passing parameters to the client.'
                        ' Used to pass information when providing access to this '
                        'client in a web-service. (default: "%(default)s").')
    parser.add_argument('-f', "--filter", action='store_false',
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
    mykey = findfp(args.key, gpg, True)
    if mykey == None:
        sys.stderr.write('Could not find own key! Bye.\n')
        sys.exit(1)
        
    serverkey = findfp(args.query_server_key, gpg)
    if serverkey == None:
        sys.stderr.write('Could not find query server key! Bye.\n')
        sys.exit(1)

    if args.url != None:
        print "url: ", args.url
        try:
            qs = urlparse(args.url).query
            qdict = {}
            if len(qs) > 0:
                for parm in qs.split('&'):
                    tup = parm.split('=')
                    qdict[tup[0]] = tup[1]
            if (qdict.has_key('user')) :
                alias = qdict['user']
        except Exception as e:
            sys.stderr.write('--url argument error: ' + str(e) +'\n')
            sys.exit(1)

    if alias == None and args.user != None:
        alias = args.user

    if args.debug:
        print "Starting!"
        print "gpghome:", args.gpghome
        print "key fingerprint:", mykey
        print "server key fingerprint:", serverkey
        print "server address:", args.query_server_address
        print "server port:", args.query_server_port
        if alias != None:
            print "alias:", alias
        
    try:
        reactor.connectTCP(args.query_server_address, args.query_server_port,
                           TextClientFactory(serverkey, mykey, gpg, args.filter,
                                             not args.nowrite,
                                             alias))
        reactor.run()
    except Error as e:
        s = str(e).split(':').strip()[-1]
        print s, 'Bye.'
        sys.exit(1)
