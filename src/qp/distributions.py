# -*-Python-*-
################################################################################
#
# File:         distributions.py
# RCS:          $Header: $
# Description:  Statistical discribution
# Author:       Staal Vinterbo
# Created:      Wed May 22 08:03:03 2013
# Modified:     Thu Sep 26 13:56:28 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# distributions.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# distributions.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with distributions.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['rlaplace', 'plaplace']

from random import uniform
from math import log, exp
from numpy.random import binomial

def rlaplace(scale, location = 0, r = 0):
    '''genrate a random deviate from Laplace(location, scale)'''
    assert(scale > 0)
    r = uniform(r, 1)
    signr = 1 if r >= 0.5 else -1    
    rr = r if r < 0.5 else 1 - r
    return location - signr * scale * log(2 * rr)

def plaplace(q, location = 0, scale = 1):
    '''quantile function'''
    assert(scale > 0)
    zedd = float(q - location)/scale
    return  0.5 * exp(zedd) if q < location else 1 - 0.5 * exp(-zedd)

def rbinom(n, p):
    return binomial(n, p)
