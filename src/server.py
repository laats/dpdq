# -*-Python-*-
################################################################################
#
# File:         server.py
# RCS:          $Header: $
# Description:  Twisted server protocol skeleton
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 16:05:34 2013
# Modified:     Wed Jun 12 23:23:44 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# server.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# server.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with server.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['ServerFactory']


from twisted.internet.protocol import Factory
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import reactor
import gnupg

class Server(NetstringReceiver):
    
    def __init__(self, conn, keyfp, gpg, handler):
        self.num = conn
        self.n = 0
        self.gpg = gpg
        self.keyfp = keyfp
        self.handler = handler

    def connectionLost(self, reason):
        print 'removing ' + str(self.num)
        print 'reason: ' + str(reason).split(':')[-1][:-1]

    def stringReceived(self, line):
        print '\nhandling:\n' + line,
        self.handler(self, line)


    def deccheck(self, cipher):
        clear = self.gpg.decrypt(cipher)
        if not clear.valid:
            print 'message from ' + str(clear.username) + ' not valid!'
            return None
        if clear.username != None and len(clear.username) > 0:
            uname = clear.username.split()[0]
        else:
            uname = 'Unknown'
        return (str(clear), uname, clear.fingerprint)


class ServerFactory(Factory):

    def __init__(self, keyfp, gpg, handler):
        self.conns = 0
        self.gpg = gpg
        self.keyfp = keyfp
        self.handler = handler
        

    def buildProtocol(self, addr):
        self.conns += 1
        return Server(self.conns, self.keyfp, self.gpg, self.handler)



if __name__ == "__main__":    
    import sys
    import argparse as ap
    from gpgutils import findfp

    parser = ap.ArgumentParser(description='Start Encrypted Echo Server')
    parser.add_argument("-k", "--key", type=str, default='QueryServer',
                        help = 'the key to user for the server (default: "%(default)s").')
    parser.add_argument("directory", type=str, default='.',
                        help = 'the directory in which to find key files (default: "%(default)s").')
    parser.add_argument("-p", "--port", type=int, default=8123,
                        help = 'the server port (default: %(default)d).')
    args = parser.parse_args()

    gpg = gnupg.GPG(gnupghome=args.directory)
    mykey = findfp(args.key, gpg, True)
    if mykey == None:
        sys.stderr.write('Could not find own key! Bye.\n')
        sys.exit(1)
   
    def handle_CHAT(server, message):
        res = server.deccheck(message)
        if res == None:
            print 'message could not be verified. Disconnecting.'
            server.transport.loseConnection()
            return

        (clear, username, fp) = res
        print 'was from', username
        clear_out = 'Hi ' + username + ', you sent:\n' + clear
        cipher = server.gpg.encrypt(clear_out, fp, sign=server.keyfp)
        server.sendString(str(cipher))



    print "Starting! "
    print "directory:", args.directory
    print "key fingerprint:", mykey
    print "port:", args.port

    reactor.listenTCP(args.port, ServerFactory(mykey, gpg, handle_CHAT))
    reactor.run()
