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
# Modified:     Sun Jun 23 16:46:14 2013 (Staal Vinterbo) staal@mats
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

from twisted.internet import reactor
from collections import defaultdict
import gnupg

import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, MetaData, ForeignKey

from logging import info, error, warning
from ast import literal_eval

from dpdq.ra.server import Server, ServerFactory
from dpdq.qp.backend import init_risk_backend
from dpdq.ra.policy import policies

class RiskServer(Server):
    def __init__(self, conn, keyfp, gpg, handler, queryserverfps, database, policy):
        Server.__init__(self, conn, keyfp, gpg, handler)
        self.database = database
        self.queryfp = queryserverfps
        self.backend = init_risk_backend(database)
        self.con = self.backend['connection']
        self.users = self.backend['schema'].tables['users']
        self.history = self.backend['schema'].tables['history']        
        self.handlers = defaultdict(lambda : (lambda f, p: (2, 'No such query')),
                                    {0 : self.handle0,
                                     1 : self.handle1})
        self.policy = policy

    def handle1(self, fromfp, parms):
        userfp = parms[0]
        if not (fromfp in (self.queryfp + [userfp])): # only user or server can ask
            return (1, "Permission denied, disconnecting.")
        try:
            res = list(self.con.execute(sa.select([self.users.c.tt,
                                                   self.users.c.qt]).where(self.users.c.id == userfp)))
            if len(res) != 1:
                return (1, 'User not found. Disconnecting.')
            (tt, qt) = res[0]
            res = list(self.con.execute(sa.select([sa.func.sum(self.history.c.eps)]).where(self.history.c.id == userfp)))
        except Exception as e:
            error('handle1: '+str(e))
            return (3, 'handle1: '+str(e))
        if res:
            s = res[0][0]
            used = float(s) if s != None else 0.0
        return (0, used, tt, qt)

        
    def handle0(self, fromfp, parms):
        if not (fromfp in self.queryfp): # only server can ask
            return (1, "Permission denied for " + str(fromfp) + ", only server can ask this. Disconnecting.")
        userfp = parms[0]
        try:
            eps = float(parms[1])
        except:
            return(2, 'Malformed query (eps not a float). Disconnecting.')
        
        res = self.handle1(fromfp, parms)
        if res[0] != 0:
            return res
        (status, used, tt, qt) = res

        ok = self.policy(eps, tt, qt, used, []) # XXX: add history  
        
        ok = used + eps <= tt and eps <= qt
        if ok: # add to history
            try:
                self.con.execute(self.history.insert().values(id=userfp, eps=eps))
            except Exception as e:
                error('handle2(insert): '+str(e))
                return (3, 'handle2(insert): '+str(e))
        try:
            self.con.close()
        except Exception as e:
                error('handle2(close): '+str(e))
                return (3, 'handle2(close): '+str(e))
        return(0, ok + 0)

    def dispatch(self, fromfp, query, parms):
        try:
            q = int(query)
        except:
            return (2, 'Malformed query (no such type). Disconnecting.')
        if self.handlers.has_key(q):
            return self.handlers[q](fromfp, parms)
        else:
            return (2, 'Malformed query (no such type). Disconnecting.')

        

def handler(server, message):
    res = server.deccheck(message)
    if res == None:
        warning('message could not be verified. Disconnecting.')
        server.transport.loseConnection()
        return

    (clear, username, fp) = res
    print 'query', clear, 'from', username

    try:
        qtuple = literal_eval(clear)
        query,parms = qtuple[0], qtuple[1:]
        response = server.dispatch(fp, query, parms)
        status = response[0]
    except Exception as e:
        warning('malformed query: ' + clear + ' exception:' + str(e))
        response = (2, 'malformed query')
        status = 2

    print 'response', response
    cipher = server.gpg.encrypt(str(response), fp, sign=server.keyfp)
    server.sendString(str(cipher))
    if status != 0:
        warning('Query status: ' + str(status) + ':'+str((clear, username, fp)))
        server.transport.loseConnection()
    else:
        info('Query ok: ' + str((clear, username, fp)))

class RiskServerFactory(ServerFactory):
    def __init__(self, keyfp, gpg, handler, serverfp, database, policy):
        ServerFactory.__init__(self, keyfp, gpg, handler)
        self.serverfp = serverfp
        self.base = database
        self.policy = policy

    def buildProtocol(self, addr):
        self.conns += 1
        return RiskServer(self.conns, self.keyfp, self.gpg, self.handler, self.serverfp, self.base, self.policy)


if __name__ == "__main__":    
    import sys
    import argparse as ap
    import logging

    from dpdq.gpgutils import findfp
    from dpdq import Version

    try:
        from dpdq_risk_policy import policies as new_policies
        policies.update(new_policies)
    except:
        pass


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
    parser.add_argument("-s", "--query_server_keys", type=str, default='QueryServer',
                        help = 'comma separated key identities for query server users (default: "%(default)s").')
    parser.add_argument("-e", "--enforce_policy", default='threshold', choices=policies.keys(),
                        help = 'risk management policy to enforce (default: "%(default)s").')
    parser.add_argument('-g', "--gpghome", type=str, default='.',
                        help = 'the folder in which to find key ring files (default: "%(default)s").')
    parser.add_argument("-l", "--logfile", type=str, default='risk.log',
                        help = 'the file information about transactions and the'
        ' state of the accountant is written to (default: "%(default)s").')
    parser.add_argument('-v', "--version", action='store_true',
                        help = 'display version number and exit.')


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)

    logging.basicConfig(filename=args.logfile,level=logging.INFO,
                        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')

    gpg = gnupg.GPG(gnupghome=args.gpghome)
    mykey = findfp(args.key, gpg, True)
    if mykey == None:
        sys.stderr.write('Could not find own key! Bye.\n')
        error('Could not find my own key ' + str((args.key, mykey)))
        sys.exit(1)
    querykeys = map(lambda x : findfp(x.strip(), gpg), args.query_server_keys.split())
    if None in querykeys:
        sys.stderr.write('Could not find query server keys! Bye.\n')
        error('Could not find server key ' + str((args.query_server_keys, querykeys)))        
        sys.exit(1)
   
    print "Starting Risk Accountant! "
    print "GPG directory:", args.gpghome
    print "key fingerprint:", mykey
    print "query server key fingerprints:", querykeys
    print "risk database:", args.database_url
    print "port:", args.risk_server_port
    print "policy:", args.enforce_policy
    info("Starting Risk Accountant:" + str((args.gpghome, mykey, querykeys, args.database_url, args.risk_server_port)))

    reactor.listenTCP(args.risk_server_port, RiskServerFactory(mykey, gpg, handler, querykeys,
                                                               args.database_url,
                                                               policies[args.enforce_policy]['implementation']))
    reactor.run()
    

