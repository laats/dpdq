# -*-Python-*-
################################################################################
#
# File:         histogram.py
# RCS:          $Header: $
# Description:  Differentially private truncated histograms
# Author:       Staal Vinterbo
# Created:      Wed May 22 08:01:57 2013
# Modified:     Thu Sep 26 13:59:59 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
################################################################################

__all__ = ['discretize_data', 'noisy_histogram', 'max_size']

from distributions import rlaplace, plaplace, rbinom
from operator import mul
from sampler import *
from itertools import islice
from math import floor, exp, log
max_size = 500000

def discretize_data(row_iterator, col_names, dmeta, nbin_min=2):
    data = map(tuple, row_iterator)
    attd = dmeta['attributes']
    types = map(lambda cn : attd[cn]['type'], col_names)
    dim = len(types)    
    n = len(data)
    size = dmeta['size']
    print 'dataset size', size
    print 'dims', dim
    print 'n', n

    if any(map(lambda x : x > 2, types)):
        raise ValueError('histogram: can only use columns that are categorical or numeric.')

    nbin = max(nbin_min, int(floor(1.0/pow((log(size)/size), (1.0/(dim + 1))))))

    if nbin < 1:
        raise ValueError('Dataset too small: nbin < 1.')

    print 'nbin:', nbin

    values = []
    newcolv = []
    colv = zip(*data)
    
    for i,cn in enumerate(col_names):
        if types[i] == 0:
            vals = attd[cn]['values'].keys()
            if n > 0:
                newcol = colv[i]
        else:
            #print cn
            a = attd[cn]['bounds']['lower']
            b = attd[cn]['bounds']['upper']
            extra = float(b-a)/1000
            w = float((b+extra)-a)/nbin # avoid index overflow if upper bound is encoutered
            mids = map(lambda i : a + i*w + w/2, range(nbin))
            vals = map(lambda v : '[' + str(v - w/2) + ', ' + str(v + w/2) + ')', mids)
            check_bounds = lambda x : max(a, min(x, b)) # 'Windsorize' value
            if n > 0:
                newcol = map(lambda v : vals[int(floor((check_bounds(v) - a)/w))], colv[i])
        values.append(vals)
        if n > 0:
            newcolv.append(newcol)
    
    #sizes = map(len, values)
    #print 'sizes', sizes
    #print 'values', values
    #N = reduce(mul, sizes)
        
    discdata = zip(*newcolv)

    return(values, discdata)


def noisy_histogram(values, discdata, A, eps = 1, tau = None):
    sizes = map(len, values) # attribute co-domain sizes
    print 'sizes', sizes
    #print 'values', values
    N = reduce(mul, sizes) # size of full histogram
    print 'N: ', N
        
    datad = {}
    for row in map(tuple, discdata):
        if datad.has_key(row):
            datad[row] += 1
        else:
            datad[row] = 1

    exclude = set(datad.keys())
    n = len(exclude)
    print 'n: ', n 
    if tau == None:
        tau = A * log(1 if n == 0 else n) / eps 
    print 'tau', tau

    b = 2.0/eps
    plb = plaplace(tau, scale = b) # P(L < tau | L ~ Laplace(location = 0, scale = 2/eps))
    p = 0.5 * exp(-tau/b)

    print 'P(L(0,2/eps) > tau)', p
    print 'P(L(0,2/eps) =< tau)', plb
    #print ' p + plb ', p + plb
    
    assert(p < 1)
    print 'N-n:', N-n
    nzero = 0
    if N - n > 0:
        nzero = rbinom(N-n, p) # expected to be int(round(p * (N - n))) 
    print 'extra samples : ', nzero, 'expected:', int(round(p * (N - n)))

    if nzero + n > max_size:
        raise ValueError('Histogram too large.')

    for nam, rw in sorted(datad.items(), key = lambda (_,x) : x, reverse=True)[0:max(20, len(datad))]:
        print nam, ':', rw

    for k, c in datad.items():
        noisy = rlaplace(scale = b, location = c)
        if noisy < tau:
            del datad[k]
        else:
            datad[k] = int(round(noisy))

    #######   sample      ##
    print 'sampling', nzero, '...'
    newvals = sample_new_rows(nzero, values, exclude)

    # create dict and add
    datad2 = {}
    for row in newvals:
        datad2[row] = int(round(rlaplace(scale = b, r = plb)))

    datad.update(datad2)
    return datad

def sample_new_rows(n, values_list, exclude_tuples):
    bases = map(len, values_list)
    N = reduce(mul, bases, 1)
    tdict = transd(values_list)
    di = nrows2id(tdict, exclude_tuples)
    usednums = map(lambda row : mr_toint(row, bases), di)
    print 'usednums', len(usednums)
    print 'N', N
    sampleit = worsample(N, usednums)
    newnums = list(islice(sampleit, n))
    print 'sampled', len(newnums)
    di = map(lambda x : mr_fromint(x, bases), newnums)
    newvals = map(tuple, irows2nam(values_list, di))
    print 'newvals', len(newvals)
    return newvals

    
    
