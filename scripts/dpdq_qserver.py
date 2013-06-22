#!/usr/bin/env python
################################################################################
#
# File:         queryserver.py
# RCS:          $Header: $
# Description:  Encrypted query server, by default echo. Handles multiple clients
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 16:05:34 2013
# Modified:     Sat Jun 22 10:25:07 2013 (Staal Vinterbo) staal@mats
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


from twisted.internet.protocol import Factory, ClientFactory
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import reactor
import gnupg
from dpdq.gpgutils import wrap, unwrap

from dpdq.frontend import init_frontend, handle_query
from ast import literal_eval
from logging import error, warning, info
from pprint import pprint

import imp
import os

import signal

# query types
QTYPE_META = 0
QTYPE_INFO = 1
QTYPE_RISK = 2
QTYPE_ECHO = 3
QTYPE_MAX = 3

# response codes
STATUS_OK = 0
STATUS_ERROR_BUDGET = 1
STATUS_ERROR_RA = 2
STATUS_ERROR_QUERY = 3
STATUS_ERROR_INTERNAL = 4


### wrappers

class Address:
    def __init__(self, fp, addr, port):
        self.fp = fp
        self.addr = addr
        self.port = port

class ServerParameters:
    '''collection of server parameters'''
    def __init__(self,
                 keyfp,
                 gpg,
                 handler,
                 handler_return,
                 risk_address,
                 risk_fp,
                 frontend,
                 allow_alias = False,
                 allow_echo=False):

        self.gpg = gpg # gpg instance
        self.keyfp = keyfp # own gpg key fingerprint
        self.handle_init = handler  # handle incoming request until risk accountant gets queried
        self.handle_return = handler_return # continue handling after risk accountant has answered       
        self.risk_address = risk_address # address of risk accountant
        self.user_fp = None # the sender of requests gpg fingerprint
        self.packet = None
        self.conn = 0
        self.frontend = frontend
        self.query = None
        self.risk_fp = risk_fp
        self.allow_alias = allow_alias
        self.allow_echo = allow_echo

    def client_wrap(self, message):
        '''wrap message in encryption/signature layer for sending to client'''
        return wrap(self.gpg, self.keyfp, self.user_fp, message)

    def ra_wrap(self, message):
        '''wrap message in encryption/signature layer for sending to Risk Accountant'''
        return wrap(self.gpg, self.keyfp, self.risk_fp, message)        

    def unwrap(self, cipher):
        '''decrypt/verify encrypted message'''
        return unwrap(self.gpg, cipher)
    
        
class Query:
    def __init__(self, qtype, alias, eps, params):
        self.type = qtype
        self.eps = eps
        self.params = params
        self.alias = alias
    def __str__(self):
        return str((self.type, self.alias, self.eps, self.params))
    

### Protocols

#### Server protocol for talking to clients
class ServerProtocol(NetstringReceiver):
    
    def __init__(self, parameters):
        self.parameters = parameters
        self.n = 0
        self.risk_pending = False
        self.query = None
        self.allow_alias = parameters.allow_alias

    def connectionLost(self, reason):
        print 'removing ' + str(self.parameters.conn)
        print 'reason: ' + str(reason).split(':')[-1][:-1]

    def stringReceived(self, line):
        print '\nhandling:\n' + line,
        self.parameters.handle_init(self, line)

class ServerFactory(Factory):
    def __init__(self, parameters):
        self.conns = 0
        self.parameters = parameters

    def buildProtocol(self, addr):
        self.conns += 1
        self.parameters.conn = self.conns

        if self.parameters.reload_frontend:
            self.parameters.reload_frontend = False
            reload_frontend(self.parameters)
            
        return ServerProtocol(self.parameters)

#### Client protocol for talking to Risk Accountant

class RiskClientProtocol(NetstringReceiver):

    def __init__(self, server):
        self.server = server
    
    def stringReceived(self, data):
        # pass on to server protocol
        self.server.risk_pending = False
        self.transport.loseConnection() # close down risk server connection
        self.server.parameters.handle_return(self.server, data)

    def connectionMade(self):
        # send packet
        self.server.risk_pending = True        
        self.sendString(self.server.parameters.packet)


class RiskClientFactory(ClientFactory):
    def __init__(self, server):
        self.server = server # the query server instance
        
    def buildProtocol(self, addr):
        '''build protocol that passes on packet from factory'''
        print 'Connected.'
        return RiskClientProtocol(self.server)

    def clientConnectionFailed(self, connector, reason):
        self.server.risk_pending = False            
        why = str(reason).split(':')[-1][:-1].strip()
        self.server.sendString(self.server.parameters.client_wrap(
            str((STATUS_ERROR_INTERNAL, self.server.query.type, 'Could not connect to risk accountant: '+why))))
        self.server.transport.loseConnection()
        
    def clientConnectionLost(self, connector, reason):
        if self.server.risk_pending:
            self.server.risk_pending = False
            why = str(reason).split(':')[-1][:-1].strip()
            self.server.sendString(self.server.parameters.client_wrap(
                str((STATUS_ERROR_INTERNAL, self.server.query.type, 'Lost connection to risk accountant: '+why))))
            self.server.transport.loseConnection()
        


### handlers
    
def parse_query(query):
    '''parse query in a save way'''
    try:
        (typ, alias, eps, rest) = literal_eval(query)
        q = Query(typ, alias, eps, rest)
    except:
        return None
    return q

def load_mod(fname, mname='module'):
    '''load module from a python source file'''
    fname = os.path.join(os.getcwd(), fname)
    return imp.load_source(mname, fname)
 
        
def reload_frontend(parameters):
    '''reload frontend and update with hotpluggable query type'''
    print 'Trying to reload frontend...'
    try:
        if parameters.querymodule != None:
            module = load_mod(parameters.querymodule)
            parameters.processors.update(module.processors)
            info('added query types: ' + ' '.join(module.processors.keys()))
            print ('added query types: ' + ' '.join(module.processors.keys()))
    except Exception as e:
        print 'Reload failed: ', str(e)
        pass

    parameters.frontend = init_frontend(parameters.database,
                                        parameters.processors)
        



def handle_init(server, message):
    '''handle an incoming query request: first half, send query to Risk Accountant'''

    sunwrap = lambda c : unwrap(server.parameters.gpg, c)
    swrap = lambda t,m : str(wrap(server.parameters.gpg, server.parameters.keyfp, t, m))
    
    res = sunwrap(message)
    if res == None:
        print 'message could not be verified. Disconnecting.'
        server.transport.loseConnection()
        return
        
    # pass message on to risk accountant
    (clear, username, fp) = res
    server.parameters.user_fp = fp # record who this was from

    q = parse_query(clear)


    if (q == None or q.type > QTYPE_MAX or
        (q.type == QTYPE_ECHO and not server.parameters.allow_echo)):
        print 'malformed query. Disconnecting.'
        info('Malformed query from ' + username + '(' + fp + ')')
        server.sendString(swrap(fp, str((STATUS_ERROR_QUERY, q.type, 'Malformed query, bye.'))))
        server.transport.loseConnection()
        return


    server.parameters.query = q
    server.query = q

    # check if connecting client can supply aliases
    # this should only be used if the client can be trusted
    user_id = fp
    if server.parameters.allow_alias and q.alias != None:
        user_id = q.alias

    if q.type == QTYPE_ECHO:
        print 'Echo...'
        #pprint(server.parameters.frontend['meta'])
        info('Sending echo to ' + username + '(' + fp + ')')
        server.sendString(swrap(fp, str((STATUS_OK, q.type, q))))
        return


    if q.type == QTYPE_META:
        print 'sending meta'
        #pprint(server.parameters.frontend['meta'])
        info('Sending metadata to ' + username + '(' + fp + ')')
        server.sendString(swrap(fp, str((STATUS_OK, q.type,
                                         server.parameters.frontend['meta']))))
        return

    if q.type == QTYPE_RISK:
        risk_query = str((1, user_id, q.eps))
        server.parameters.packet = swrap(server.parameters.risk_address.fp, risk_query)
        factory = RiskClientFactory(server)
        reactor.connectTCP(server.parameters.risk_address.addr,
                           server.parameters.risk_address.port,
            factory, 3)
        return

    if q.type == QTYPE_INFO:
        # query risk accountant if user (id == fp) has eps to spend
        print 'querying risk accountant...'
        risk_query = str((0, user_id, q.eps))
        server.parameters.packet = swrap(server.parameters.risk_address.fp, risk_query)
        factory = RiskClientFactory(server)
        reactor.connectTCP(server.parameters.risk_address.addr,
                           server.parameters.risk_address.port,
            factory, 3)
        
    
def handle_return(server, cipher):
    '''handle incoming request: second half: response from Risk Accountant'''

    sunwrap = lambda c : unwrap(server.parameters.gpg, c)
    swrap = lambda m : str(wrap(server.parameters.gpg, server.parameters.keyfp,
                              server.parameters.user_fp, m))

    res = sunwrap(cipher)
    if res == None:
        print 'message from risk accountant could not be verified. Disconnecting.'
        server.sendString(swrap(str(4, server.query.type, 'Internal error: risk accountant could not be verified!')))
        server.transport.loseConnection()
        return

    # handle return from risk accountant
    (clear, username, fp) = res
    print 'was from', username
    print 'risk accountant said: ', clear

    try:
        ra_tuple = literal_eval(clear)
    except:
        error('Malformed response from risk accountant!')
        server.sendString(swrap(str(4, server.query.type, 'Internal error: malformed response from risk accountant!')))        
        sys.exit(1)
        
    ra_status = ra_tuple[0]
    if ra_status > 0:
        error('RA error:' + str((ra_tuple)))
        server.sendString(swrap(str((STATUS_ERROR_RA, server.query.type, ra_tuple))))
        return

    if server.query.type == QTYPE_RISK:
        info('Responding to ' + server.parameters.user_fp + ', query: ' + str(server.query) + ', sent: ' + str(ra_tuple[1:]))
        response = dict(zip(['total', 'tt', 'qt'], ra_tuple[1:]))
        server.sendString(swrap(str((STATUS_OK, server.query.type, response))))
        return

    if server.query.type == QTYPE_INFO:
        if ra_status == 0 and ra_tuple[1] != 1:
            server.sendString(swrap(str((STATUS_ERROR_BUDGET, server.query.type, 'Budget Exceeded.'))))
        else:
            try:
                eps = server.parameters.query.eps
                query = server.parameters.query.params
                res = handle_query(server.parameters.frontend, eps, query)
            except Exception as e:
                server.sendString(swrap(str((STATUS_ERROR_QUERY, server.query.type, str(e)))))
            else:
                info('Responding to ' + server.parameters.user_fp + ', query: ' + str(server.query) + ', sent: ' + str(res))
                server.sendString(swrap(str((STATUS_OK, server.query.type, res))))




if __name__ == "__main__":    
    import sys
    import argparse as ap
    import logging    
    from dpdq.processors_fs import processors
    from dpdq.gpgutils import findfp
    from dpdq import Version
    import os

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

    logging.basicConfig(filename=args.logfile,level=logging.DEBUG, format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')
 
    try:
        gpg = gnupg.GPG(gnupghome=args.gpghome)
        mykey = findfp(args.key, gpg, True)
        if mykey == None:
            sys.stderr.write('Could not find own key! Bye.\n')
            sys.exit(1)

        ra_fp = findfp(args.risk_server_key, gpg)
        if ra_fp == None:
            sys.stderr.write('Could not find risk accountant key! Bye.\n')
            sys.exit(1)

        print "Starting! "
        print "gpghome:", args.gpghome
        print "key fingerprint:", mykey
        print "port:", args.query_server_port
        print "risk accountant fp", ra_fp
        print "risk accountant address", args.risk_server_address + ':' + str(args.risk_server_port)

        ra_address = Address(ra_fp, args.risk_server_address, args.risk_server_port)
        #own_address = Address(mykey, 'localhost', args.ownport)

        try:
            if args.querymodule != None:
                module = load_mod(args.querymodule)
                processors.update(module.processors)
                info('added query types: ' + ' '.join(module.processors.keys()))
        except Exception as e:
            print 'Failed to load query types on startup:', str(e)
            print 'cwd: ', os.getcwd()

        frontend = init_frontend(args.database_url, processors)

        parameters = ServerParameters(mykey, gpg, handle_init, handle_return,
                                      ra_address, ra_fp, frontend,
                                      allow_alias = args.allow_alias,
                                      allow_echo = args.allow_echo)
        # hack, clean up at some point...
        parameters.querymodule = args.querymodule
        parameters.database = args.database_url
        parameters.processors = processors
        parameters.reload_frontend = False
        
        def sig_handler(signum, frame):
            parameters.reload_frontend = True
        signal.signal(signal.SIGUSR1, sig_handler) # install signal handler
         
    except Exception as e:
        sys.stderr.write('Initialization error: ' + str(e) + '\n')
        sys.exit(1)
        
    reactor.listenTCP(args.query_server_port, ServerFactory(parameters))
    reactor.run()
