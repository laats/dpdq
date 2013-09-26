# -*-Python-*-
################################################################################
#
# File:         cproto.py
# RCS:          $Header: $
# Description:  dpdq client protocol
# Author:       Staal Vinterbo
# Created:      Tue Jun 25 10:21:50 2013
# Modified:     Mon Sep 16 16:15:40 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# cproto.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# cproto.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cproto.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################



import os
import sys
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from logging import error, warning, info, debug
from texttable import Texttable

from ..gpgproto import GPGProtocol
from ..messages import *
from cli import Cli



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
from ast import literal_eval
def trans(s):
    if type(s) == str:
        if s[0] == '[' and s[-1] == ')':
            a,b = literal_eval('(' + s[1:])
            return uniform(a, b)
    return s
    
def tlist(res):
    l = [res['response']['col_names']]
    for tup,mult in res['response']['histogram'].items():
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

#####

class State:
    '''shared information about the global state'''
    def __init__(self, gpg, me, qp,
                 silent = False,
                 alias = None,
                 allow_write=True):

        self.gpg = gpg # gpg instance
        self.me = me # my key identifier
        self.qp = qp # query processor identifier
        self.silent = silent
        self.user = None # either alias or my key fingerprint
        self.allow_write = allow_write
        self.alias = alias

    def set_user(self, user):
        self.user = user if self.alias == None else self.alias

    def print_(self, text):
        if not self.silent:
            sys.stdout.write(text)


#### Client protocol for talking to Query Processor

class ClientProtocol(GPGProtocol):

    def __init__(self, state):
        GPGProtocol.__init__(self,
                             state.gpg,
                             state.me,
                             state.qp, # talk to qp 
                             [state.qp]) # only allow responses from this qp
        self.state = state
        self.state.set_user(self.my_key)
        self.handler = Handler(self)
    
    def messageReceived(self, message):
        self.handler.dispatch(message)

    def connectionMade(self):
        self.state.print_(greeting)
        self.handler.request = QPRequest(QP_META)
        self.sendMessage(self.handler.request)


class QPClientFactory(ClientFactory):
    def __init__(self, state):
        self.state = state
        
    def buildProtocol(self, addr):
        return ClientProtocol(self.state)

    def clientConnectionFailed(self, connector, reason):
        why = str(reason).split(':')[-1][:-1].strip()
        sys.stderr.write('Could not connect to Query Processor: ' +
                   why + '\n')
        if reactor.running:
            reactor.stop()
        
    def clientConnectionLost(self, connector, reason):
        why = str(reason).split(':')[-1][:-1].strip()
        sys.stderr.write(why + '\nGoodbye.\n')
        if reactor.running:
            reactor.stop()

        


#### Handling client requests

class Handler:

    def __init__(self, clientProtocol):
        self.proto = clientProtocol
        self.request = None
        self.user_id = None
        self.pending = None
        self.handle_response = [self.handle_meta,
                                self.handle_info,
                                self.handle_risk]
        self.make_request = {'info' : self.make_info,
                             'risk' : self.make_risk }
        self.request = None
        self.meta = None

        self.print_ = self.proto.state.print_

        self.cli = None # need metadata to initialize

    def dispatch(self, response):
        r = QPResponse.parse(response)
        if r == None:
            sys.stderr.write('Malformed response received.\n')
            self.proto.transport.loseConnection()
            return

        ### handle reponse
        try:
            if r.status != QP_OK:
                self.print_('Status(' + str(r.status) + '): ' +
                           str(r.response) + '\n')
            elif r.towhat != self.request.type:
                self.print_('Did not get reponse to request sent: ' +
                           str(r.response) + '\n')
            else:
                res = self.handle_response[self.request.type](r)
        except Exception as e:
            sys.stderr.write('Response handling error: ', e, '\n')

        # write response to file if so requested
        if (self.request.type != QP_META and self.cli != None and
            r.status == QP_OK and self.proto.state.allow_write and
            self.cli.outfile != None and self.cli.outfile != ''):
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
                    'response' : r.response
                }
                f.write('response =' + str(outdict) + '\n' + outp)
                if f != sys.stdout: f.close()
            except Exception as e:
                self.print_('Could not write reponse to '
                           + self.cli.outfile + ', ' + str(e) + '\n')
            else:
                self.print_('Wrote response to ' + self.cli.outfile + '\n')
            self.cli.outfile = None
        
        # let user compose next request
        request = None
        while request == None:
            if self.cli == None:
                self.cli = Cli(self.meta)
                self.cli.use_rawinput = not self.proto.state.silent
                if not self.cli.use_rawinput:
                    self.cli.prompt = ''
            self.cli.cmdloop()
            if self.cli.exit:
                self.proto.transport.loseConnection()
                return 

            # create request 
            request = self.make_request[self.cli.qtype]()

        # send request
        self.request = request
        self.proto.sendMessage(request)

    def make_info(self):
        return QPRequest(QP_INFO, self.proto.state.user, self.cli.eps,
                         ((self.cli.data, self.cli.select, self.cli.project),
                          (self.cli.type, self.cli.params.items())))

    def make_risk(self):
        return QPRequest(QP_RISK, self.proto.state.user, 0, None)

    def handle_meta(self, r):
        self.meta = r.response

    def handle_risk(self, r):
        self.print_('Total risk accumulated: ' + str(r.response['total']) + '\n'
                   'Cumulative max allowed risk: ' + str(r.response['tt']) + '\n'
                   'Per query allowed risk: ' + str(r.response['qt']) + '\n')

    def handle_info(self, r):
        response = r.response
        if type(response) == dict:
            if not self.cli.type == 'Histogram':
                for k,v in sorted(response.items()):
                    self.print_(str(k) + ": " + str(v) + '\n')
            else:
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
                self.print_(table.draw() + '\n')
        else:
            self.print_(str(response) + '\n')



def init_factory(gpg, me, qp,
                   silent = False,
                   alias = None,
                   allow_write=True):

     state = State(gpg, me, qp,
                   silent = silent,
                   alias = alias,
                   allow_write=allow_write)

     return QPClientFactory(state)


            

