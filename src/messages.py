# -*-Python-*-
################################################################################
#
# File:         messages.py
# RCS:          $Header: $
# Description:  Message formats
# Author:       Staal Vinterbo
# Created:      Sun Jun 23 10:09:00 2013
# Modified:     Tue Jun 25 12:59:49 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# messages.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# messages.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with messages.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

from ast import literal_eval


# qp request types
QP_META = 0
QP_INFO = 1
QP_RISK = 2
QP_ECHO = 3
QP_MAX = 3


# qp response codes
QP_OK = 0
QP_ERROR_BUDGET = 1
QP_ERROR_RA = 2
QP_ERROR_QUERY = 3
QP_ERROR_INTERNAL = 4

# ra query types
RA_CHECK = 0
RA_INFO = 1
RA_MAX = 1

# ra response codes
RA_OK = 0
RA_ERROR_USER = 1
RA_ERROR_QUERY = 2
RA_ERROR_INTERNAL = 3

# ra status
RA_GRANTED = 1
RA_DENIED = 0



class QPRequest:
    def __init__(self, rtype, alias = None, eps = 0, params = None):
        self.type = rtype
        self.eps = eps
        self.params = params
        self.alias = alias
    def __str__(self):
        return str((self.type, self.alias, self.eps, self.params))
    @classmethod
    def parse(self, text):
        '''parse request in a safe way'''
        try:
            tup = literal_eval(text)
            q = QPRequest(*tup)
            if q.type > QP_MAX or q.type < 0:
                q = None
        except:
            return None
        return q


class QPResponse:
    def __init__(self, status, towhat, response):
        self.status = status
        self.towhat = towhat
        self.response = response
    def __str__(self):
        return str((self.status, self.towhat, self.response))
    @classmethod
    def parse(self, text):
        '''parse response in a safe way'''
        try:
            tup = literal_eval(text)
            q = QPResponse(*tup)
        except:
            return None
        return q

class RAQuery:
    def __init__(self, typ, user, eps = None):
        self.type = typ
        self.user = user
        self.eps = eps
    def __str__(self):
        return str((self.type, self.user, self.eps))
    @classmethod
    def parse(self, text):
        '''parse response in a safe way'''
        try:
            tup = literal_eval(text)
            q = RAQuery(*tup)
            if q.type > RA_MAX or q.type < 0:
                return None
        except:
            return None
        return q

class RAResponse:
    def __init__(self, status, f1, tt = None, qt = None):
        self.status = status
        self.f1 = f1 # status, error text, or cum_risk
        self.tt = tt
        self.qt = qt
    def __str__(self):
        return str((self.status, self.f1, self.tt, self.qt))
    @classmethod
    def parse(self, text):
        '''parse response in a safe way'''
        try:
            tup = literal_eval(text)
            q = RAResponse(*tup)
        except:
            return None
        return q


def QPBadRequest(text, towhat = None):
    return QPResponse(QP_ERROR_QUERY, towhat, text)

def QPInternalError(text):
    return QPResponse(QP_ERROR_INTERNAL, None, text)

def QPRAError(text):
    return QPResponse(QP_ERROR_RA, None, text)

def QPBudgetError(text, towhat = None):
    return QPResponse(QP_ERROR_BUDGET, towhat, text)

def QPOK(text, towhat = None):
    return QPResponse(QP_OK, towhat, text)

def RABadQuery(text):
    return RAResponse(RA_ERROR_QUERY, text)

def RABadUser(text):
    return RAResponse(RA_ERROR_USER, text)    

def RAInternalError(text):
    return RAResponse(RA_ERROR_INTERNAL, text)

def RAOK(f1, tt=None, qt=None):
    return RAResponse(RA_OK, f1, tt, qt)
