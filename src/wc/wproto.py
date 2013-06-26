# -*-Python-*-
################################################################################
#
# File:         wproto.py
# RCS:          $Header: $
# Description:  web server client protocol
# Author:       Staal Vinterbo
# Created:      Tue Jun 25 18:28:30 2013
# Modified:     Tue Jun 25 22:06:01 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# wproto.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# wproto.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with wproto.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

from twisted.internet.protocol import ReconnectingClientFactory
from logging import error, warning, info, debug

from dpdq.gpgproto import GPGProtocol
from dpdq.messages import *
import gnupg
import sys

#####

class State:
    '''shared information about the global state'''
    def __init__(self, gpg, me, qp):

        self.gpg = gpg # gpg instance
        self.me = me # my key identifier
        self.qp = qp # query processor identifier


#### Client protocol for talking to Query Processor

class ClientProtocol(GPGProtocol):

    def __init__(self, state, resource):
        GPGProtocol.__init__(self,
                             state.gpg,
                             state.me,
                             state.qp, # talk to qp 
                             [state.qp]) # only allow responses from this qp
        self.state = state
        self.handler = Handler(self)
        self.connected = False
        self.request = None     # the request sent
        self.callback = None   # the responder that through method
                                # callback(message, request) takes care
                                # of the second half of the web
                                # resource rendering
        self.resource = resource
        self.resource.proto = self # pass the protocol to the resource
    
    def messageReceived(self, message):
        self.handler.dispatch(message)

    def connectionMade(self):
        self.connected = True

    def connectionLost(self, reason):
        self.connected = False

    # when the web server gets a resource request
    # it creates a QPRequest to get info needed
    # and then calls this with the request and a callback
    # function. Should check if
    # protcol.connected is true first.
    def sendRequest(self, qp_request, web_request, callback):
        self.callback = callback
        self.request = qp_request
        self.web_request = web_request
        self.sendMessage(qp_request)
    

class QPClientFactory(ReconnectingClientFactory):
    def __init__(self, state, resource):
        self.state = state
        self.resource = resource # record web-resource
                                 # if we lose connection
                                 # we will need
                                 # resource.request.<methods>
                                 # to finish the request
        
    def buildProtocol(self, addr):
        self.resetDelay()
        return ClientProtocol(self.state, self.resource)

    def clientConnectionLost(self, connector, reason):
        why = str(reason).split(':')[-1][:-1].strip()
        if self.resource.request != None:
            self.resource.request.write(why + ', trying to reconnect.')
            self.resource.request.finish()
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                         reason)
        
class Handler:
    def __init__(self, clientProtocol):
        self.proto = clientProtocol

    def dispatch(self, response):
        r = QPResponse.parse(response)
        self.proto.callback(r, self.proto.request, self.proto.web_request)
        
def gen_factory(state):
    return lambda resource : QPClientFactory(state, resource)

