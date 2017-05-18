# -*-Python-*-
################################################################################
#
# File:         gentestkeys.py
# RCS:          $Header: $
# Description:  Generate gpg keys for Alice, Bob, and Fred. Note that this will
#               add the keys to directory 
# Author:       Staal Vinterbo
# Created:      Tue Apr  9 12:39:44 2013
# Modified:     Thu May 18 12:35:27 2017 (Staal Vinterbo) staal@klump
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
################################################################################

import gnupg

who_client = [('Bob', 'Client Key', 'bob@nodomain.oph'),
              ('Demo', 'Client Key', 'demo@nodomain.oph'),              
              ('Alice', 'Client Key', 'alice@nodomain.oph')]
who_server = [('QueryServer', 'Server Key', 'fred@nodomain.oph'),
              ('RiskAccountant', 'Server Key', 'ted@nodomain.oph')]
who_all = who_client + who_server
keys = dict(zip(map(lambda x : x[0], who_all), who_all))

def gkey(who, gpg):
    for (a,b,e) in who:
        keyinput = gpg.gen_key_input(name_real = a,
                                     name_comment = b,
                                     name_email = e,
                                     key_type = 'RSA')
        key = gpg.gen_key(keyinput)


if __name__ == "__main__":
    import sys
    import argparse as ap

    parser = ap.ArgumentParser(description='Generate gpg test keys')
    parser.add_argument('key', help='the key to generate', choices= keys.keys())
    #parser.add_argument("-s", "--server", action="store_true",
    #                    help = 'Generate the server keys for: ' + ' '.join(a for a,b,c in who_server))
    #parser.add_argument("-c", "--client", action="store_true",
    #                    help = 'Generate the client keys for: ' + ' '.join(a for a,b,c in who_client))
    parser.add_argument("directory", type=str, default='.',
                        help = 'the directory in which to store key files (default: "%(default)s").')

    args = parser.parse_args()

    gpg = gnupg.GPG(homedir=args.directory)

    gkey([keys[args.key]], gpg)    
    print "generated: ", gpg.list_keys()
    
    
    

    
                                            
