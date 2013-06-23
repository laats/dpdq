# -*-Python-*-
################################################################################
#
# File:         gpgutils.py
# RCS:          $Header: $
# Description:  Utils for using gnugp
# Author:       Staal Vinterbo
# Created:      Thu Apr 11 21:56:02 2013
# Modified:     Sun Jun 23 16:05:02 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# gpgutils.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# gpgutils.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gpgutils.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['findfp', 'findkey', 'finduserinfo', 'wrap', 'unwrap']

import re
from pprint import pprint

def flatten(iterables):
    for it in iterables:
        if hasattr(it, '__iter__'):
            for element in it:
                yield element
        else:
            yield it

def findfp(pattern, gpg, private=False):
    '''find key fingerprint corresponsing to pattern'''
    kds = gpg.list_keys(private)
    fields = ['fingerprint', 'keyid', 'uids']
    pat = re.compile(pattern)
    for d in kds:
        if any([pat.match(x) for x in flatten([d[f] for f in fields])]):
            return d['fingerprint']
    return None

def findkey(pattern, gpg, private=False):
    '''find key for pattern'''
    kds = gpg.list_keys(private)
    fields = ['fingerprint', 'keyid', 'uids']
    pat = re.compile(pattern)
    for d in kds:
        if any([pat.match(x) for x in flatten([d[f] for f in fields])]):
            return d
    return None

def finduserinfo(pattern, gpg, private=False):
    '''find username + info for pattern'''
    d = findkey(pattern, gpg, private)
    if d == None:
        return None
    fields = ['uids', 'keyid']    
    return ':'.join(map(str,flatten([d[f] for f in fields])))



def unwrap(gpg, cipher):
    '''decrypt and verify'''
    clear = gpg.decrypt(cipher)
    if ( (not clear.valid) or clear.trust_level is None or
         clear.trust_level < clear.TRUST_FULLY or clear.key_status is not None):
        return None
    if clear.username != None and len(clear.username) > 0: # in case we don't have the username
        uname = clear.username.split()[0]
    else:
        uname = 'Unknown'
    return (str(clear), uname, clear.fingerprint)

def wrap(gpg, fromfp, tofp, clear):
    '''encrypt and sign'''
    return str(gpg.encrypt(clear, tofp, sign=fromfp))

    
    
