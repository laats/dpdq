# -*-Python-*-
################################################################################
#
# File:         rproto.py
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Sun Jun 23 17:17:49 2013
# Modified:     Mon Jun 24 10:04:12 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# rproto.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# rproto.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with rproto.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################


from twisted.internet import reactor
from twisted.internet.protocol import Factory
from collections import defaultdict


import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import Float, DateTime, MetaData, ForeignKey

from logging import info, error, warning
from ast import literal_eval

from server import Server, ServerFactory
from ..qp.backend import init_risk_backend
from policy import policies

from ..gpgproto import GPGProtocol
from ..messages import *

import imp
import os
import signal

#from policy import policies, policy



class ServerState:
    '''collection of server parameters'''
    def __init__(self,
                 gpg,
                 me,
                 database,
                 policies,
                 policy):

        self.gpg = gpg # gpg instance
        self.me = me # my key identifier
        self.loadf = lambda _ : None

        self.database = database
        self.backend = init_risk_backend(database)
        self.con = self.backend['connection']
        self.users = self.backend['schema'].tables['users']
        self.history = self.backend['schema'].tables['history']        
        self.policies = policies
        self.policy = policy

        
    def reload_backend(self):
        self.loadf(self)


### Protocols

#### Server protocol for talking to clients
class ServerProtocol(GPGProtocol):
    
    def __init__(self, state):
        GPGProtocol.__init__(self, state.gpg, state.me)
        self.state = state
        self.handler = ClientHandler(self)

    def connectionLost(self, reason):
        print 'reason: ' + str(reason).split(':')[-1][:-1]

    def messageReceived(self, message):
        print '\nhandling:\n' + message
        self.handler.dispatch(message)

class ServerFactory(Factory):
    def __init__(self, state):
        self.state = state
        self.reload_backend = False

    def buildProtocol(self, addr):
        if self.reload_backend:
            self.reload_backend = False
            self.state.reload_backend()
        return ServerProtocol(self.state)

#### Handling client requests


class ClientHandler:

    def __init__(self, clientProtocol):
        self.proto = clientProtocol
        self.request = None
        self.user_id = None
        self.pending = None
        self.handler = [self.handle_check,
                        self.handle_info]

    def dispatch(self, request):
        r = RAQuery.parse(request)
        if r == None:
            self.proto.sendMessage(RABadQuery(request))
            return
        self.request = r
        try:
            res = self.handler[r.type](r)
            info('Served: ' + str((str(r), str(res))))
            print('Served: ' + str((str(r), str(res))))
            self.proto.sendMessage(res)
        except Exception as e:
            print 'exception:', e
            self.proto.sendMessage(RAInternalError('Sorry.'))
            

    def get_info(self, r):
        res = list(self.proto.state.con.execute(
            sa.select([self.proto.state.users.c.tt,
                       self.proto.state.users.c.qt]).where(
                           self.proto.state.users.c.id == r.user)))
        if len(res) != 1:
            return None
        row = res[0]
        res = list(self.proto.state.con.execute(
            sa.select([sa.func.sum(self.proto.state.history.c.eps)]).where(
                       self.proto.state.history.c.id == r.user)))
        used = 0.0
        if res:
            s = res[0][0]
            used = float(s) if s != None else 0.0
        return (used, row)

    def handle_check(self, r):
        user = self.get_info(r)
        if user == None:
            return RABadUser('User not found.')
        (total, (tt, qt)) = user
        ok = self.proto.state.policies[self.proto.state.policy]['implementation'](
            r.eps, tt, qt, total, []) 
        if ok: # add to history
            self.proto.state.con.execute(self.proto.state.history.insert().values(
                id=r.user, eps=r.eps))
        return RAOK(ok + 0)

    def handle_info(self, r):
        user = self.get_info(r)
        if user == None:
            return RABadUser('User not found.')
        (total, (tt, qt)) = user
        return RAOK(total, tt, qt)
        


def load_mod(fname, mname='module'):
    '''load module from a python source file'''
    fname = os.path.join(os.getcwd(), fname)
    return imp.load_source(mname, fname)
 
        
def reload_backend(state):
    '''reload frontend and update with hotpluggable query type'''
    print 'Trying to reload frontend...'

    try:
        if state.module != None:
            module = load_mod(state.module)
            state.policies.update(module.policies)
            state.policy = module.policy
            info('enforcing policy: ' + state.policy)
            print ('enforcing: ' + state.policy)
    except Exception as e:
        print 'Reload failed: ', str(e)
        pass



def init_factory(gpg, me, database, policy, module):
    state = ServerState(gpg, me, database, policies, policy)
    state.module = module
    state.loadf = reload_backend
    factory = ServerFactory(state)
    
    def sig_handler(signum, frame):
        factory.reload_frontend = True
    signal.signal(signal.SIGUSR1, sig_handler) # install signal handler

    return factory

    
