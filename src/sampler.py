# -*-Python-*-
################################################################################
#
# File:         sampler.py
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Mon May 20 21:03:16 2013
# Modified:     Wed Jun 12 23:35:55 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# sampler.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# sampler.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with sampler.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['worsample', 'mr_toint', 'mr_fromint', 'nrows2id', 'irows2nam', 'transd' ]


from random import random, randrange

############# WOR sample [modern implementation of Ernvall and Nevalainen, 1982]
#An Algorithm for Unbiased Random Sampling
#Jarmo Ernvall, Olli Nevalainen
#THE COMPUTER JOURNAL, VOL.25,NO.1,1982

from random import randrange

class ptdict(dict):
    '''dict that returns the key without storing it if key not found'''
    def __missing__(self, key):
        return key

def worsample(N, exclude = []):
    '''sampling without replacement, returns a generator

       do not sample from exclude'''
    end = N
    remap = ptdict()

    for x in sorted(exclude, reverse=True):
        remap[x] = remap[end-1]
        end -= 1

    for i in xrange(end):
        j = randrange(end)
        k = remap[j]
        remap[j] = remap[end-1]
        end -= 1
        yield k
        

    
#############  Mixed radix
# convert point in [a] x [b] x [c] x ... x [d] where 
# [k] = {0,1,...,k-1}
# to an integer and back

def mr_toint(c, b):
    '''convert element in set product to integer

       b[i] contains the sizes of factor i in the set product'''
    n = len(b)
    res = 0
    for i in range(n):
        res = res * b[i] + c[i]
    return res

def mr_fromint(v, b):
    '''convert integer to element in set product'''
    n = len(b)
    res = [0] * n
    for i in range(n-1, -1, -1):
        res[i] = v % b[i]
        v = v / b[i]
    return res

def mr_test(b):
    '''test conversion functions'''
    N = reduce(mul, b, 1)
    for i in range(N):
        if i != mr_toint(mr_fromint(i, b), b):
            print 'fail', i
            return False
    return True




########## data to mixed radix and back

def transd(lol):
    return map(lambda l : dict((x, i) for i, x in enumerate(l)), lol)

def getb(lol):
    return map(len, lol)

def nam2id(td, row):
    return map(lambda (d, n) : d[n], zip(td, row))

def id2nam(lol, row):
    return map(lambda (l, i) : l[i], zip(lol, row))

def nrows2id(td, rows):
    return map(lambda row : nam2id(td, row), rows)

def irows2nam(lol, irows):
    return map(lambda irow : id2nam(lol, irow), irows)



def test_trans():
    from itertools import islice    
    lol = ['abc', 'defg', 'hijkl']
    lol = map(list, lol)
    print 'lol', lol
    b = getb(lol)
    print 'b', b
    td = transd(lol)
    print 'td', td
    N = reduce(mul, b, 1)
    print 'N', N
    l = list(islice(worsample(N), 6))
    print 'l', l
    di = map(lambda n : fromint(n, b), l)
    print 'di', di
    dn = irows2nam(lol, di)
    print 'dn', dn
    dii = nrows2id(td, dn)
    ll = map(lambda row : toint(row, b), dii)
    print 'll', ll
    print ll == l
    



#############

if __name__ == "__main__":

    from itertools import islice
    from random import randint

    def test_sampler(i):

        N = randint(3, 10000)
        n = randint(1, N-1)
        m = randint(1, N-n)

        #print (N,n,m)

        assert(n + m <= N)

        wos = worsample(N)
        lm = list(islice(wos, m))
        wos2 = worsample(N, lm)
        ln = list(islice(wos2, n))

        sm = set(lm)
        sn = set(ln)

        assert(len(sm) == m)
        assert(len(sn) == n)

        assert(len(sm & sn) == 0)

        return True

    l = map(test_sampler, xrange(10000))
    
        
