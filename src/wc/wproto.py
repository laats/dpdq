# -*-Python-*-
################################################################################
#
# File:         wproto.py
# RCS:          $Header: $
# Description:  twisted web server QP client protocol
# Author:       Staal Vinterbo
# Created:      Tue Jun 25 18:28:30 2013
# Modified:     Fri Jun 28 14:47:59 2013 (Staal Vinterbo) staal@mats
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

from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from logging import error, warning, info, debug

from dpdq.gpgproto import GPGProtocol
from dpdq.messages import *
import gnupg
import sys

#####

class State:
    '''information about the global state'''
    def __init__(self, gpg, me, qp):

        self.gpg = gpg # gpg instance
        self.me = me # my key identifier
        self.qp = qp # query processor identifier


#### Client protocol for talking to Query Processor

class ClientProtocol(GPGProtocol):

    def __init__(self, state, qp_request, web_request, callback):
        GPGProtocol.__init__(self,
                             state.gpg,
                             state.me,
                             state.qp, # talk to qp 
                             [state.qp]) # only allow responses from this qp
        self.state = state
        self.finished = False

        # callback is called with (QPResponse, self.qp_request, self.web_request)
        self.qp_request = qp_request      # the request to send
        self.web_request = web_request    # the associated web request associated 
        self.callback = callback # the responder that through method
                                 # callback(message, request) takes care
                                 # of the second half of the web
                                 # resource rendering
    
    def messageReceived(self, message):
        r = QPResponse.parse(message)
        self.finished = True
        self.transport.loseConnection()
        self.callback(r, self.qp_request, self.web_request)

    def connectionMade(self):
        self.sendMessage(self.qp_request)
        

    def connectionLost(self, reason):
        if not self.finished:
            self.callback(str(reason),
                          self.qp_request,
                          self.web_request) # signal connectionLost


class QPClientFactory(ClientFactory):
    def __init__(self, state, q_request, w_request, callback):
        self.state = state
        self.q_request = q_request
        self.w_request = w_request
        self.callback = callback
        
    def buildProtocol(self, addr):
        return ClientProtocol(self.state,
                              self.q_request,
                              self.w_request,
                              self.callback)

    def clientConnectionFailed(self, connector, reason):
        self.callback(str(reason), self.q_request, self.w_request) # signal connectionLost


# convenience wrapper to send_request
def make_sender(state, callback, timeout=5):
    def send(q, w, host, port):
        return send_request(state, host, port, q, w, callback, timeout)
    return send

# send a request        
def send_request(state, host, port, qp_request, web_request, callback, timeout=5):
    factory = QPClientFactory(state, qp_request, web_request, callback)
    return reactor.connectTCP(host, port, factory, timeout=timeout)
           
