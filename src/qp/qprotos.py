# -*-Python-*-
################################################################################
#
# File:         qprotos.py
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Sun Jun 23 12:41:01 2013
# Modified:     Mon Jun 24 10:16:38 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# qprotos.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# qprotos.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qprotos.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['init_factory', 'Address', 'RiskClientFactory']

from twisted.internet.protocol import Factory, ClientFactory
from ..gpgproto import GPGProtocol
from frontend import init_frontend
from logging import error, warning, info
import imp
import os
import signal

from ..messages import *
from frontend import handle_query
from twisted.internet import reactor
from logging import error, info, debug


class Address:
    def __init__(self, addr, port):
        self.addr = addr
        self.port = port

class ServerState:
    '''collection of server parameters'''
    def __init__(self,
                 gpg,
                 me,
                 risk_id,
                 risk_address,
                 frontend,
                 allow_alias = False,
                 allow_echo=False):

        self.gpg = gpg # gpg instance
        self.me = me # my key identifier
        self.ra = risk_id
        self.risk_address = risk_address # address of risk accountant
        self.frontend = frontend
        self.allow_alias = allow_alias
        self.allow_echo = allow_echo
        self.loadf = lambda _ : None

        
    def reload_frontend(self):
        self.loadf(self)


### Protocols

#### Server protocol for talking to clients
class ServerProtocol(GPGProtocol):
    
    def __init__(self, state):
        GPGProtocol.__init__(self, state.gpg, state.me)
        self.risk_pending = False
        self.state = state
        self.handler = ClientHandler(self)

    def connectionLost(self, reason):
        print 'reason: ' + str(reason).split(':')[-1][:-1]

    def messageReceived(self, line):
        print '\nhandling:\n' + line,
        self.handler.dispatch(line)

class ServerFactory(Factory):
    def __init__(self, state):
        self.state = state
        self.reload_frontend = False

    def buildProtocol(self, addr):
        if self.reload_frontend:
            self.reload_frontend = False
            self.state.reload_frontend()
        return ServerProtocol(self.state)

#### Client protocol for talking to Risk Accountant

class RiskClientProtocol(GPGProtocol):

    def __init__(self, server):
        GPGProtocol.__init__(self,
                             server.state.gpg,
                             server.state.me,
                             server.state.ra, # talk to ra 
                             [server.state.ra]) # only allow contact with
        self.server = server
    
    def messageReceived(self, message):
        # pass on to server protocol
        self.server.risk_pending = False
        self.transport.loseConnection() # close down risk server connection
        self.server.handler.collect(message)

    def connectionMade(self):
        # send packet
        self.server.risk_pending = True        
        self.sendMessage(self.server.handler.pending)


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
        self.server.sendMessage(QPInternalError(
            'Could not connect to Risk Accountant'))
        self.server.transport.loseConnection()
        
    def clientConnectionLost(self, connector, reason):
        if self.server.risk_pending:
            self.server.risk_pending = False
            why = str(reason).split(':')[-1][:-1].strip()
            self.server.sendMessage(QPInternalError(
                'Lost connection to Risk Accountant'))
            self.server.transport.loseConnection()

#### Handling client requests


class ClientHandler:

    def __init__(self, clientProtocol):
        self.proto = clientProtocol
        self.request = None
        self.user_id = None
        self.pending = None
        self.handler = [self.handle_meta,
                        self.handle_ra,
                        self.handle_ra,
                        self.handle_echo]
        self.collector = { QP_INFO : self.collect_info,
                           QP_RISK : self.collect_risk }
            

    def dispatch(self, request):
        r = QPRequest.parse(request)
        if r == None:
            self.proto.sendMessage(QPBadRequest(request))
            return

        self.request = r

        self.user_id = self.proto.peer_key
        if self.proto.state.allow_alias and r.alias != None:
            self.user_id = r.alias

        try:
            self.handler[r.type](r)
        except Exception as e:
            print 'exception:', e
            self.proto.sendMessage(QPInternalError('Sorry.'))
            
    def handle_meta(self, r):
        print ('Sending metadata to ' +
             str(self.proto.peer) + '(' + str(self.proto.peer_key) + ')')
        info('Served: ' + str((self.user_id, str(self.request))))
        self.proto.sendMessage(
            QPResponse(QP_OK, r.type, self.proto.state.frontend['meta']))

    def handle_ra(self, r):
        print 'querying risk accountant...'
        ra_type = RA_CHECK if r.type == QP_INFO else RA_INFO
        self.pending = RAQuery(ra_type, self.user_id, r.eps)
        factory = RiskClientFactory(self.proto)
        reactor.connectTCP(
            self.proto.state.risk_address.addr,
            self.proto.state.risk_address.port,
            factory, 3)

    def handle_echo(self, r):
        info('Served: ' + str((self.user_id, str(self.request))))
        self.proto.sendMessage(QPResponse(QP_OK, r.type, r))

    def collect(self, message):
        rar = RAResponse.parse(message)
        if rar == None:
            error('Invalid reponse from RA:' + message)
            self.proto.sendMessage(QPInternalError('Sorry.'))
            return

        if rar.status == RA_ERROR_USER:
            self.proto.sendMessage(QPBadRequest('User not found.',
                                                self.request.type))
            return
        
        if rar.status > RA_OK:
            error('RA error: ', str(rar))
            self.proto.sendMessage(QPInternalError('Sorry.'))
            return
        try:
            self.collector[self.request.type](rar)
        except Exception as e:
            print 'exception:', e
            self.proto.sendMessage(QPInternalError('Sorry.'))
        
    def collect_info(self, rar):
        if rar.f1 != RA_GRANTED:
            self.proto.sendMessage(QPBudgetError('Budget exceeded.'))
            return
        try:
            res = handle_query(self.proto.state.frontend,
                               self.request.eps, self.request.params)
        except Exception as e:
            self.proto.sendMessage(QPBadRequest(str(self.request)))
        else:
            info('Served: ' + str((self.user_id, str(self.request))))
            self.proto.sendMessage(QPOK(res, self.request.type))

    def collect_risk(self, rar):
        response = { 'total' : rar.f1,
                     'tt' : rar.tt,
                     'qt' : rar.qt }
        info('Served: ' + str((self.user_id, str(self.request))))
        self.proto.sendMessage(QPOK(response, self.request.type))

####

def load_mod(fname, mname='module'):
    '''load module from a python source file'''
    fname = os.path.join(os.getcwd(), fname)
    return imp.load_source(mname, fname)
 
        
def reload_frontend(state):
    '''reload frontend and update with hotpluggable query type'''
    print 'Trying to reload frontend...'

    try:
        if state.querymodule != None:
            module = load_mod(state.querymodule)
            state.frontend['processors'].update(module.processors)
            info('added query types: ' + ' '.join(module.processors.keys()))
            print ('added query types: ' + ' '.join(module.processors.keys()))
    except Exception as e:
        print 'Reload failed: ', str(e)
        pass

    state.frontend = init_frontend(None,
                                   state.frontend['processors'],
                                   reinit=True)


### create a server factory

def init_factory(gpg, # initialized gpg
                 me,  # my name
                 risk_accountant, # risk accountants name
                 database,   # database ulr
                 processors, # list of processors
                 ra_address, # the address of the RA
                 allow_alias, # allow clients to query on others' behalf
                 allow_echo, # allow echo request
                 querymodule): # where to load new queries from

        frontend = init_frontend(database, processors)

        state = ServerState(
            gpg,
            me,
            risk_accountant,
            ra_address,
            frontend,
            allow_alias = allow_alias,
            allow_echo  = allow_echo)
        
        state.querymodule = querymodule
        state.loadf = reload_frontend

        factory = ServerFactory(state)
        
        def sig_handler(signum, frame):
            factory.reload_frontend = True
        signal.signal(signal.SIGUSR1, sig_handler) # install signal handler

        return factory
