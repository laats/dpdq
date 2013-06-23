# -*-Python-*-
################################################################################
#
# File:         gpgproto.py
# RCS:          $Header: $
# Description:  GPG encrypted netstring protocol
# Author:       Staal Vinterbo
# Created:      Sun Jun 23 07:53:44 2013
# Modified:     Sun Jun 23 16:32:14 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# gpgproto.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# gpgproto.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gpgproto.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

from twisted.protocols.basic import NetstringReceiver
import gnupg
from dpdq.gpgutils import wrap, unwrap, findfp

class fdict(dict): # like defaultdict(False) except does not store
    def __missing__(self, key):
        return False

class GPGProtocol(NetstringReceiver):
    '''Wrap NetstringReceiver in a layer of encryption. Disconnects invalids.'''

    def __init__(self, gpg, me, recipient = None, peers = None, silent = True):
        '''initialize

        me -- identifies my own key
        recipient -- default recipient
        peers -- who I will accept messages from. If None
                 messages from anyone who has a valid key are valid.
        silent -- if True then invalid messages will be silently
                  ignored. Otherwise Exception will be raised.
        '''
        self.gpg = gpg

        # find my own key
        self.me = me
        self.my_key = findfp(me, gpg, True)
        if self.my_key == None:
            raise Exception('Could not find my key!')

        # set peer if recipiet != None
        self.peer = recipient
        if recipient:
            self.peer_key = findfp(recipient, gpg, False)

        # initialize peers map
        self.peers = fdict() # map keys to names
        self.allow_any = True
        if peers != None:
            self.peers.update(
                zip(map(lambda nam : findfp(nam, gpg, False), peers),
                    peers))
            self.allow_any = False


    def messageReceived(self, cleartext):
        '''to be overloaded by protocol user'''
        pass

    def stringReceived(self, cipher):

        clear_in = unwrap(self.gpg, cipher)
        if clear_in == None:
            self.transport.loseConnection()
            if not self.silent:
                raise Exception('Unknown peer.')
            else:
                return

        (cleartext, uname, fp) = clear_in

        if not (self.allow_any or self.peers[fp]):
            if not self.silent:
                raise Exception('Unknown peer.')
            else:
                return

        self.peer_key = fp
        if not self.peers[fp]:
            self.peers[fp] = uname

        self.messageReceived(cleartext)

    def sendMessage(self, cleartext):
        self.sendString(wrap(self.gpg,
                             self.my_key,
                             self.peer_key,
                             str(cleartext)))

            

            

            
            
