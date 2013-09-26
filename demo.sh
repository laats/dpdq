#!/bin/bash
################################################################################
#
# File:         runtest.sh
# RCS:          $Header: $
# Description:  test deployment of dpdq system. Creates directories:
#               /tmp/dpdq/[cqr]
# Author:       Staal Vinterbo
# Created:      Fri May 10 16:44:21 2013
# Modified:     Mon Sep 16 10:48:55 2013 (Staal Vinterbo) staal@mats
# Language:     Shell-script
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# demo.sh is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# demo.sh is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with demo.sh; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

set -e

if [ ! -d /tmp/dpdq/c ]; then
    echo "setting up directories in /tmp..."
    rm -rf /tmp/dpdq/q /tmp/dpdq/r /tmp/dpdq/c
    mkdir -p /tmp/dpdq/q /tmp/dpdq/r /tmp/dpdq/c


    # generate gpg keys
    echo "generating keys..."
    echo "NOTE: this might take a *long* time if the entropy pool is depleted."
    echo "This can be a problem on virtual machines that do not have access to real hardware."
    echo " see: http://www.gnupg.org/faq/GnuPG-FAQ.html#why-does-it-sometimes-take-so-long-to-create-keys"
    python gentestkeys.py Alice /tmp/dpdq/c # &> /dev/null
    python gentestkeys.py QueryServer /tmp/dpdq/q # &> /dev/null
    python gentestkeys.py RiskAccountant /tmp/dpdq/r # &> /dev/null


    # share and sign public keys
    echo "sharing and signing keys..."

    # share public client key with servers
    gpg -q --no-tty --homedir /tmp/dpdq/c --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir /tmp/dpdq/r --import --batch &> /dev/null
    gpg -q --no-tty --homedir /tmp/dpdq/c --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir /tmp/dpdq/q --import --batch &> /dev/null

    # share public server keys with client
    gpg -q --no-tty --homedir /tmp/dpdq/r --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir /tmp/dpdq/c --import --batch &> /dev/null
    gpg -q --no-tty --homedir /tmp/dpdq/q --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir /tmp/dpdq/c --import --batch &> /dev/null

    # share server public keys among themselves
    gpg -q --no-tty --homedir /tmp/dpdq/r --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir /tmp/dpdq/q --import --batch &> /dev/null
    gpg -q --no-tty --homedir /tmp/dpdq/q --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir /tmp/dpdq/r --import --batch &> /dev/null

    # client signs server keys
    echo y | gpg -q --no-tty --homedir /tmp/dpdq/c --command-fd 0 --sign-key QueryServer &> /dev/null
    echo y | gpg -q --no-tty --homedir /tmp/dpdq/c --command-fd 0 --sign-key RiskAccountant &> /dev/null

    # servers sign each others' keys
    echo y | gpg -q --no-tty --homedir /tmp/dpdq/r --command-fd 0 --sign-key QueryServer &> /dev/null
    echo y | gpg -q --no-tty --homedir /tmp/dpdq/q --command-fd 0 --sign-key RiskAccountant &> /dev/null

    # servers sign client key
    echo y | gpg -q --no-tty --homedir /tmp/dpdq/r --command-fd 0 --sign-key Alice &> /dev/null
    echo y | gpg -q --no-tty --homedir /tmp/dpdq/q --command-fd 0 --sign-key Alice &> /dev/null
fi

# copy/create databases
echo "Creating database with datasets..."
rm -f /tmp/dpdq/q/warehouse.db
for t in databases/*.csv; do
    echo " adding $t..."
    dpdq_csv2db.py sqlite:////tmp/dpdq/q/warehouse.db $t  > /dev/null
done


rm -f /tmp/dpdq/r/risk.db

echo "creating users that have budgets..."
echo creating risk users
dpdq_riskuser.py -t 100 -g /tmp/dpdq/r sqlite:////tmp/dpdq/r/risk.db Alice &> /dev/null
echo created Alice
dpdq_riskuser.py -t 100 -n sqlite:////tmp/dpdq/r/risk.db Demo &> /dev/null
echo created Demo
dpdq_riskuser.py -t 100 -n sqlite:////tmp/dpdq/r/risk.db Demo-2 &> /dev/null
echo created Demo-2
     
# start servers
echo "Starting servers..."

echo " Checking to see if old instances need to be killed..."
if [ -f /tmp/dpdq/r/pid ]
then
    (kill `cat /tmp/dpdq/r/pid`) &> /dev/null || echo 'RA not running...'
    rm -f /tmp/dpdq/r/pid
fi

if [ -f /tmp/dpdq/q/pid ]
then
    (kill `cat /tmp/dpdq/q/pid`) &> /dev/null || echo 'QP not running...'
    rm -f /tmp/dpdq/q/pid
fi
if [ -f /tmp/dpdq/c/pid ]
then
    (kill `cat /tmp/dpdq/c/pid`) &> /dev/null || echo 'Web server not running...'
    rm -f /tmp/dpdq/c/pid
fi


echo " Starting new ones..."
if hash xterm 2> /dev/null; then
    xterm -T Risk_Accountant -e dpdq_rserver.py -g /tmp/dpdq/r sqlite:////tmp/dpdq/r/risk.db &
    echo $! > /tmp/dpdq/r/pid
    xterm -T Query_Processor -e dpdq_qserver.py --allow_alias -g /tmp/dpdq/q sqlite:////tmp/dpdq/q/warehouse.db -q aux/query_dplr.py &
    echo $! > /tmp/dpdq/q/pid
    xterm -T Web -e dpdq_web.py -g /tmp/dpdq/c &
    echo $! > /tmp/dpdq/c/pid
else
    echo "starting servers in the background. You will need to kill them explicitly!"
    dpdq_rserver.py -g /tmp/dpdq/r sqlite:////tmp/dpdq/r/risk.db > /dev/null &
    echo $! > /tmp/dpdq/r/pid
    dpdq_qserver.py --allow_alias -g /tmp/dpdq/q sqlite:////tmp/dpdq/q/warehouse.db > /dev/null &
    echo $! > /tmp/dpdq/q/pid
    dpdq_web.py -g /tmp/dpdq/c &> /dev/null &
    echo $! > /tmp/dpdq/c/pid
fi
echo "Server process id's (pid) are found in /tmp/dpdq/r/pid and /tmp/dpdq/q/pid."
echo 'They can be killed by "kill `cat /tmp/dpdq/[qrc]/pid`", respsectively.'
echo ''
echo 'To enjoy the web interface for user Demo, point browser to:'
echo '  http://localhost:8082'
echo ''

echo 'If you ran this script using source ("source demo.sh") then'
echo 'you can start the text client by issuing:'
echo '  dpdq'  
echo 'at the command prompt. Otherwise you will need to issue:'
echo '  dpdq_cli.py -g /tmp/dpdq/c -k Alice'
alias dpdq='dpdq_cli.py -g /tmp/dpdq/c -k Alice'




