#!/usr/bin/env python
################################################################################
#
# File:         riskadduser.py
# RCS:          $Header: $
# Description:  add/alter a user to the risk accounting data base. User must have
#               gpg key.
# Author:       Staal Vinterbo
# Created:      Thu Apr 11 19:53:50 2013
# Modified:     Thu Jun 13 16:37:05 2013 (Staal Vinterbo) staal@dink
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# dpdq_riskuser.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# dpdq_riskuser.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dpdq_riskuser.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

import gnupg
import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, MetaData, ForeignKey

from dpdq.gpgutils import finduserinfo, findfp
from dpdq.backend import make_risk_tables


if __name__ == "__main__":    
    import sys
    import argparse as ap

    parser = ap.ArgumentParser(description='Add user to the risk accounting data base. Creates database if it does not exist.')
    parser.add_argument("database_url", type=str, 
                        help = 'The RFC 1738 style url pointing to the database.'
        ' The format is dialect+driver://username:password@host:port/database.')
    parser.add_argument("user", type=str,
                        help = 'the user identifier.')
    parser.add_argument("-g", "--gpghome", type=str, default='.',
                        help = 'the directory in which to find key (and possibly database) files (default: "%(default)s").')
    parser.add_argument("-t", "--totalthreshold", type=float, default=10.0,
                        help = 'the total risk threshold (default: %(default)d).')
    parser.add_argument("-q", "--querythreshold", type=float, default=3.0,
                        help = 'the per query risk threshold (default: %(default)d).')
    parser.add_argument('-u', '--update',  action = 'store_true', help="Update existing user instead of add")
    parser.add_argument('-k', '--kill', action = 'store_true', help="Delete existing user")
    parser.add_argument('-i', '--info', action = 'store_true', help="Show user information and history")        
    parser.add_argument('-v', "--version", action='store_true',
                        help = 'display version number and exit.')
    parser.add_argument('-n', "--nokey", action='store_true',
                        help = 'Use user identifier directly instead of looking up key fingerprint.')


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)

    if not args.nokey:
        gpg = gnupg.GPG(gnupghome=args.gpghome)
        userkey = findfp(args.user, gpg) #, True)
        userinfo = finduserinfo(args.user, gpg) #, True)
        if userkey == None or userinfo == None:
            sys.stderr.write('Could not find user key fingerprint and user information! Bye.\n')
            sys.exit(1)
    else:
        userkey = args.user
        userinfo = 'user without key'

    print 'user:' , userinfo
    if not args.nokey:
        print 'user key fingerprint :' , userinfo    

    try:
        print 'creating database engine...'
        engine = sa.create_engine(args.database_url)
        print 'connecting to database...'
        conn = engine.connect()
    except Exception as e:
        sys.stderr.write('Could not connect to ' + args.database_url + '\n'
                         + str(e))
        sys.exit(1)

    try:        
        metadata = MetaData(engine)
        (users, history) = make_risk_tables(metadata)
    except Exception as e:
        sys.stderr.write('Could not get/create tables from ' + args.database_url + '. Schema mismatch?\n'
                         + str(e))
        sys.exit(1)
        
            

    try:
        if args.update:
            conn.execute(users.update().values(tt=args.totalthreshold, qt = args.querythreshold).where(users.c.id == userkey))
        elif args.kill:
            conn.execute(history.delete().where(history.c.id == userkey))
            conn.execute(users.delete().where(users.c.id == userkey))        
        elif args.info:
            print "User", args.user, "info:"        
            for row in conn.execute(users.select().where(users.c.id == userkey)).fetchall():
                print row
            print "------------------\nHistory:"
            for row in conn.execute(history.select().where(history.c.id == userkey)).fetchall():
                print row
        else:
            conn.execute(users.insert().values(id=userkey, tt=args.totalthreshold, qt = args.querythreshold,
                                      info=userinfo))
        print 'Ok.'
        conn.close()
    except Exception as e:
        sys.stderr.write('Could not perform operation on ' + args.database_url + '.\nreson:\n'
                         + str(e))
        sys.exit(1)
    

