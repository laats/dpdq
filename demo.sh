#!/bin/bash
################################################################################
#
# File:         runtest.sh
# RCS:          $Header: $
# Description:  test deployment of dpdq system. Creates directories:
#               /tmp/dpdq/[cqr]
# Author:       Staal Vinterbo
# Created:      Fri May 10 16:44:21 2013
# Modified:     Thu May 18 12:20:19 2017 (Staal Vinterbo) staal@klump
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

DROOT=/tmp/dpdq

if [ ! -d ${DROOT}/c ]; then
    echo "setting up directories in /tmp..."
    rm -rf ${DROOT}/q ${DROOT}/r ${DROOT}/c
    mkdir -p ${DROOT}/q ${DROOT}/r ${DROOT}/c


    # generate gpg keys
    echo "generating keys..."
    echo "NOTE: this might take a *long* time if the entropy pool is depleted."
    echo "This can be a problem on virtual machines that do not have access to real hardware."
    echo " see: http://www.gnupg.org/faq/GnuPG-FAQ.html#why-does-it-sometimes-take-so-long-to-create-keys"
    python gentestkeys.py Alice ${DROOT}/c # &> /dev/null
    python gentestkeys.py QueryServer ${DROOT}/q # &> /dev/null
    python gentestkeys.py RiskAccountant ${DROOT}/r # &> /dev/null


    # share and sign public keys
    echo "sharing and signing keys..."

    # share public client key with servers
    echo "sharing public client key with servers..."
    gpg -q --no-tty --homedir ${DROOT}/c --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir ${DROOT}/r --import --batch &> /dev/null
    gpg -q --no-tty --homedir ${DROOT}/c --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir ${DROOT}/q --import --batch &> /dev/null

    # share public server keys with client
    echo "sharing public server keys with client..."
    gpg -q --no-tty --homedir ${DROOT}/r --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir ${DROOT}/c --import --batch &> /dev/null
    gpg -q --no-tty --homedir ${DROOT}/q --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir ${DROOT}/c --import --batch &> /dev/null

    # share server public keys among themselves
    echo "share server public keys among themselves..."
    gpg -q --no-tty --homedir ${DROOT}/r --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir ${DROOT}/q --import --batch &> /dev/null
    gpg -q --no-tty --homedir ${DROOT}/q --export --batch 2> /dev/null | \
	gpg -q --no-tty --homedir ${DROOT}/r --import --batch &> /dev/null

    # client signs server keys
    echo "client signs server keys..."
    echo y | gpg -q --no-tty --homedir ${DROOT}/c --command-fd 0 --sign-key QueryServer &> /dev/null
    echo y | gpg -q --no-tty --homedir ${DROOT}/c --command-fd 0 --sign-key RiskAccountant &> /dev/null

    # servers sign each others' keys
    echo "servers sign each others' keys..."
    echo y | gpg -q --no-tty --homedir ${DROOT}/r --command-fd 0 --sign-key QueryServer &> /dev/null
    echo y | gpg -q --no-tty --homedir ${DROOT}/q --command-fd 0 --sign-key RiskAccountant &> /dev/null

    # servers sign client key
    echo "servers sign client key..."
    echo y | gpg -q --no-tty --homedir ${DROOT}/r --command-fd 0 --sign-key Alice &> /dev/null
    echo y | gpg -q --no-tty --homedir ${DROOT}/q --command-fd 0 --sign-key Alice &> /dev/null
fi

# copy/create databases
echo "Creating database with datasets..."
rm -f ${DROOT}/q/warehouse.db
for t in databases/*.csv; do
    echo " adding $t..."
    dpdq_csv2db.py sqlite:///${DROOT}/q/warehouse.db $t  > /dev/null
done


rm -f ${DROOT}/r/risk.db

echo "creating users that have budgets..."
echo creating risk users
dpdq_riskuser.py -t 100 -g ${DROOT}/r sqlite:///${DROOT}/r/risk.db Alice &> /dev/null
echo created Alice
dpdq_riskuser.py -t 100 -n sqlite:///${DROOT}/r/risk.db Demo &> /dev/null
echo created Demo
dpdq_riskuser.py -t 100 -n sqlite:///${DROOT}/r/risk.db Demo-2 &> /dev/null
echo created Demo-2
     
# start servers
echo "Starting servers..."

echo " Checking to see if old instances need to be killed..."
if [ -f ${DROOT}/r/pid ]
then
    (kill `cat ${DROOT}/r/pid`) &> /dev/null || echo 'RA not running...'
    rm -f ${DROOT}/r/pid
fi

if [ -f ${DROOT}/q/pid ]
then
    (kill `cat ${DROOT}/q/pid`) &> /dev/null || echo 'QP not running...'
    rm -f ${DROOT}/q/pid
fi
if [ -f ${DROOT}/c/pid ]
then
    (kill `cat ${DROOT}/c/pid`) &> /dev/null || echo 'Web server not running...'
    rm -f ${DROOT}/c/pid
fi


echo " Starting new ones..."
if hash xterm 2> /dev/null; then
    xterm -T Risk_Accountant -e dpdq_rserver.py -g ${DROOT}/r sqlite:///${DROOT}/r/risk.db &
    echo $! > ${DROOT}/r/pid
    xterm -T Query_Processor -e dpdq_qserver.py --allow_alias -g ${DROOT}/q sqlite:///${DROOT}/q/warehouse.db -q ${DROOT}/aux/query_dplr.py &
    echo $! > ${DROOT}/q/pid
    xterm -T Web -e dpdq_web.py -g ${DROOT}/c &
    echo $! > ${DROOT}/c/pid
else
    echo "starting servers in the background. You will need to kill them explicitly!"
    dpdq_rserver.py -g ${DROOT}/r sqlite:///${DROOT}/r/risk.db > /dev/null &
    echo $! > ${DROOT}/r/pid
    dpdq_qserver.py --allow_alias -g ${DROOT}/q sqlite:///${DROOT}/q/warehouse.db -q ${DROOT}/aux/query_dplr.py > /dev/null &
    echo $! > ${DROOT}/q/pid
    dpdq_web.py -g ${DROOT}/c &> /dev/null &
    echo $! > ${DROOT}/c/pid
fi
echo "Server process id's (pid) are found in ${DROOT}/r/pid and ${DROOT}/q/pid."
echo "They can be killed by \"kill `cat ${DROOT}/[qrc]/pid`\", respsectively."
echo ''
echo 'To enjoy the web interface for user Demo, point browser to:'
echo '  http://localhost:8082'
echo ''

echo 'If you ran this script using source ("source demo.sh") then'
echo 'you can start the text client by issuing:'
echo '  dpdq'  
echo 'at the command prompt. Otherwise you will need to issue:'
echo "  dpdq_cli.py -g ${DROOT}/c -k Alice"
alias dpdq="dpdq_cli.py -g ${DROOT}/c -k Alice"

echo 'If you are starting this as a reverse proxied demo on a machine with iptables,'
echo 'consider doing:'
echo 'sudo iptables -A INPUT -i lo -p tcp --dport 8082 -j ACCEPT'
echo 'sudo iptables -A INPUT -p tcp --dport 8082 -j DROP'




