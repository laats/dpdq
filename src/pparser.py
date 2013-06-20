# -*-Python-*-
################################################################################
#
# File:         pparser.py
# RCS:          $Header: $
# Description:  parser for predicates. Implements a recursive descent parser
#               for a disjunction of possibly negated conjunctions. Each
#               conjunction is a conjunction of descriptors. A descriptor
#               is a 'attribute operator value' expression. The parser
#               does limited checking of semantics.
# Author:       Staal Vinterbo
# Created:      Thu May  9 12:35:34 2013
# Modified:     Wed Jun 12 23:01:48 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# pparser.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pparser.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pparser.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

# status codes
OK = 0
UNKNOWN_VAL = 1
UNKNOWN_ATT = 2
UNKNOWN_OP = 3
ERROR = 4

fst = lambda x : x[0]


def toint(x):
    try:
        return int(x)
    except:
        return None

def tofloat(x):
    try:
        return float(x)
    except:
        return None

def tonum(x):
    if type(x) == int or type(x) == float:
        return x
    y = toint(x)
    if y == None:
        y = tofloat(x)
    return y


class pparser:
    def __init__(self, sdict, operators):
        self.sdict = sdict
        self.operators = operators
        self.attrs_ = sdict['attributes'].keys()

    def reset(self):
        self.p = []
        self.neg = 0
        self.attr = None
        self.report = ''
        self.index = 0
        self.expected = []

    def __str__(self):
        return str({'index': self.index, 'expected' : self.expected, 'p' : self.p})

    def __call__(self, tks):
        self.reset()
        self.tks = tks
        stat, l = self.clist()
        return stat


    def vals(self):
        '''possible values for the current attribute'''
        try:
            return self.sdict['attributes'][self.attr]['values'].keys()
        except:
            pass
        return []

    def attrs(self):
        '''available attributes'''
        return self.attrs_

    def typ(self, attr):
        '''type of attribute'''
        try:
            return self.sdict['attributes'][attr]['type']
        except:
            pass
        return None
        
    def ops(self):
        '''operators available for current attribute type'''
        try:
            typ = self.typ(self.attr)
            return self.operators[typ].keys()
        except:
            pass
        return []
        
    
    def consume(self, advance = True):
        '''consume a token'''
        try:
            out = self.tks[self.index]
        except:
            return None
        if advance:
            self.index += 1
        return out

    def back(self):
        '''push back a token'''
        if self.index > 0:
            self.index -= 1

    def peek(self):
        '''look at token withtout consuming it'''
        return self.consume(False)

    ######
    

    def clist(self):
        '''list of possibly negated conjunctions'''
        token = self.peek()
        self.expected = ['not']        
        if token == 'not':
            self.consume()
            self.neg = 1
            self.expected = []
        stat, l = self.conj()
        if stat != OK:
            return stat, l

        self.p.append((self.neg, l))
        self.neg = 0

        token = self.peek()
        if token == None:
            return OK, []

        if token == 'or':
            self.consume()
        else:
            self.expected = ['or']
            self.report = 'Expected "or" at ' + str(token)
            return ERROR, []

        return self.clist()

    def conj(self, acc = []):
        '''conjunction of descriptors'''
        stat, l = self.desc()
        if stat != OK:
            return stat, acc + l
        
        token = self.peek()
        if token == None or token == 'or':
            return OK, acc + [l]

        if token == 'and':
            self.consume()
        else:
            self.expected = ['and', 'or']
            self.report = 'Expected "and" or "or" at ' + str(token)
            return ERROR, []

        return self.conj(acc + [l])

    def desc(self):
        '''descriptor (a attribute operator value triplet)'''
        token = self.consume()
        if token == None or not token in self.attrs():
            self.expected += self.attrs()
            self.report = 'Unknown attribute: ' + str(token)
            return UNKNOWN_ATT, []

        self.attr = token
        attr = token
        self.expected = []

        token = self.consume()

        #print 'attr', attr
        #print 'typ', self.typ(attr)
        #print 'token', token
        #print 'ops', self.ops()
        #print 'values', self.vals()

        if token == None or not token in self.ops():
            self.expected = self.ops()
            self.report = 'Unknown operator: ' + str(token) 
            return UNKNOWN_OP, []

        op = token

        token = self.consume()

        #print 'value token', token

        if token == None:
            self.expected = self.vals()
            self.report = 'Missing attribute value.'
            return UNKNOWN_VAL, []

        if token[0] == '"' or token[0] == "'":
            return OK, (attr, op, token)

        if tonum(token) != None:
            return OK, (attr, op, tonum(token))            

        if not token in self.vals():
            self.expected = self.vals()
            self.report = 'Unknown attribute value: ' + str(token)
            return UNKNOWN_VAL, []

        return OK, (attr, op, token)

if __name__ == '__main__':

    from shlex import shlex
    import sys
        
    meta = {'operators':
            {0: {'==': {'literal': '==', 'description': 'equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}}, 1: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}, 2: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}, 3: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}, 4: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}},
            'datasets': {u'iris': {'attributes': {u'Sepal_Width': {'description': u'attribute Sepal_Width', 'type': 2, 'bounds': {'upper': 4.4, 'lower': 2.0}}, u'Petal_Width': {'description': u'attribute Petal_Width', 'type': 2, 'bounds': {'upper': 2.5, 'lower': 0.1}}, u'Species': {'values': {u'setosa': u'value for attribute Species', u'versicolor': u'value for attribute Species', u'virginica': u'value for attribute Species'}, 'description': u'attribute Species', 'type': 0}, u'Sepal_Length': {'description': u'attribute Sepal_Length', 'type': 2, 'bounds': {'upper': 7.9, 'lower': 4.3}}, u'Petal_Length': {'description': u'attribute Petal_Length', 'type': 2, 'bounds': {'upper': 6.9, 'lower': 1.0}}}, 'name': u'iris', 'processors': (u'simple_count',)}},
            'processors': {'simple_count': {'description': 'Produces a noise count of matching rows. Laplace(2/eps, 0) is added to the real count and the result is rounded to the nearest integer.', 'name': 'simple_count', 'parameters': {}}}}
    
    test = 'Species != versicolor an Petal_Length > 3' if len(sys.argv) < 2 else sys.argv[1]

    lex = shlex(test)
    lex.wordchars += '=!<>'
    tks = list(lex)
    print tks

    parser = pparser(meta['datasets']['iris'], meta['operators'])
    res = parser(tks)

    print res
    print str(parser)


    
    
