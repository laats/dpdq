# -*-Python-*-
################################################################################
#
# File:         policy.py
# RCS:          $Header: $
# Description:  Implement Risk accountant policy
# Author:       Staal Vinterbo
# Created:      Mon May 13 21:45:22 2013
# Modified:     Wed Jun 12 23:12:17 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# policy.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# policy.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with policy.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['policies']

# function that implements the policy
def threshold_policy(eps, tt, qt, total_sum, history):
    '''implement the threshold policy

    parameters:
       eps : currently requested risk
       tt  : total allowed risk
       qt  : per query allowed risk
       total_sum : the current total risk expenditure
       history: an iterator for the rows of the history table for this user.

    implements: eps + total_sum <= tt and eps <= qt'''
    return eps + total_sum <= tt and eps <= qt

# metadata for threshold policy
threshold_policy = {
    'name' : 'threshold',
    'implementation' : threshold_policy,
    'description' : threshold_policy.__doc__
    }

# dict containing all policies keyed by name
policies = { 'threshold' : threshold_policy }
