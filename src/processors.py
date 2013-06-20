# -*-Python-*-
################################################################################
#
# File:         processors.py
# RCS:          $Header: $
# Description:  processors
#               a processor is a dict with entries
#               'f' : a function f(eps, params, meta, result)
#                     eps - differntial privacy level
#                     params - a list of (param, value) tuples
#                     result - the result from the backend query
#                              which is a dict with entries
#                              'data' - a row tuple generator function
#                              'attributes' - the data table attributes
#                              'setd' - data set metadata
#                'name' : the name of the processor
#                'meta' : a meta data dict with entries
#                         'name', 'explanation', 'parameters'
# Author:       Staal Vinterbo
# Created:      Wed May  8 18:51:43 2013
# Modified:     Tue May 21 17:47:11 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
################################################################################

__all__ = ['rlaplace', 'processors']

from random import random, uniform, choice
from math import log, pow, exp, floor
from operator import mul



def rlaplace(scale, location = 0, r = 0):
    '''genrate a random deviate from Laplace(location, scale)'''
    assert(scale > 0)
    r = uniform(r, 1)
    signr = 1 if r >= 0.5 else -1    
    rr = r if r < 0.5 else 1 - r
    return location - signr * scale * log(2 * rr)

def plaplace(q, location = 0, scale = 1): 
    assert(scale > 0)
    zedd = float(q - location)/scale
    return  0.5 * exp(zedd) if q < location else 1 - 0.5 * exp(-zedd)




######## Simple count processor
def simple_count(eps, parms, result):
    '''simple laplace noise added to row count and then rounded'''
    count = 0
    for r in result['data']:
        count += 1
    out = int(round(rlaplace(2/eps, count)))
    return {'count' : out }

simple_count_meta = {'name' : 'simple_count',
                     'description' : 'Produces a noisy count of matching rows'
                                     ' by adding a Laplace(2/eps, 0) distributed random deviate and '
                                     'rounding the result to the nearest integer.',
                     'parameters' : {} }
proc_simple_count = {
    'name': 'simple_count',
    'f' : simple_count,
    'meta' : simple_count_meta
    }



######### count with user prefereces

user_pref_count_meta = {
    'name' : 'user_pref_count',
    'description' : 'Produces a perturbed count of matching rows by sampling the perturbation'
                    ' according to a probability mass derived from a utility of a response centered on the real count.'
                    ' The utility can be assymetric around the real count,'
                    ' and this assymetry is determined by the parameters.',
    'parameters'  : {
        'beta_plus' : { 'type' : 2,
                        'default' : 1.0,
                        'bounds'  : {
                            'lower' : 0.0,
                            'upper' : 10.0
                            },
                        'description' : 'This is the slope of the utility to the right of the real count.'
                        },
        'beta_minus' : { 'type' : 2,
                        'default' : 1.0,
                        'bounds'  : {
                            'lower' : 0.0,
                            'upper' : 10.0
                            },
                        'description' : 'This is the slope of the utility to the right of the real count.'
                        },
        'alpha_plus' : {
                        'type' : 2,
                        'default' : 1.0,
                        'bounds'  : {
                            'lower' : 0.0,
                            'upper' : 3.0
                            },
                        'description' : 'the utility is proportional with the increase from the real count to the power of this.'
                        },
        'alpha_minus' : { 
                        'type' : 2,
                        'default' : 1.0,
                        'bounds'  : {
                            'lower' : 0.0,
                            'upper' : 3.0
                            },
                        'description' : 'the utility is proportional with the decrease from the real count to the power of this.'
                        }}
}

def user_pref_count(eps, parms, result):
    '''perturbed count with user preferences'''
    count = 0
    for r in result['data']:
        count += 1
    pdict = dict(parms)

    bp = pdict['beta_plus']
    bn = pdict['beta_minus']
    ap = pdict['alpha_plus']
    an = pdict['alpha_minus']

    size = result['setd']['size']

    def cumsum(p):
        s = 0
        for x in p:
            yield (x + s)
            s += x

    def sample(p):
        #assert(sum(p) == 1.0)
        what = random()
        i = 0
        for s in cumsum(p):
            if s >= what:
                return i
            i += 1
        return i - 1

    def util(r):
        if r >= count:
            return -bp * pow(r - count, ap)
        else:
            return -bn * pow(count - r, an)
    
    def genEM(eta):
        return lambda r : exp(eta * util(r))

    def comp_eta():
        delta = max(bp, bn)
        if an > 1:
            delta = max(delta, an * bn * pow(size, an - 1))
        if ap > 1:
            delta = max(delta, ap * bp * pow(size, ap - 1))
        return eps/(2 * delta)

    eta = comp_eta()
    emf = genEM(eta)

    def genPM():
        N = sum(map(emf, range(size)))
        return lambda r : emf(r)/N

    pfun = genPM()

    p = map(pfun, range(size))
    i = sample(p)
    return { 'count' : i}

proc_user_pref_count = {
    'name': 'user_pref_count',
    'f' : user_pref_count,
    'meta' : user_pref_count_meta
    }


    
############# Histogram ###################
histogram_meta = {
    'name' : 'histogram',
    'description' : 'Produces a perturbed histogram truncated by A * log(n)/eps.',
    'parameters'  : {
        'A' : { 'type' : 2,
                        'default' : 0.5,
                        'bounds'  : {
                            'lower' : 0.0,
                            'upper' : 5.0
                            },
                        'description' : 'The truncating threshold tuning parameter.'
                        }}
}


def histogram(eps, parms, result):
    '''perturbed count with user preferences'''

    max_size = 300000

    pdict = dict(parms)
    
    data = [tuple(x) for x in result['data']]
    n = len(data)
    colv = zip(*data)
    col_names = result['attributes']
    dmeta = result['setd']

    attd = dmeta['attributes']
    types = map(lambda cn : attd[cn]['type'],
                col_names)
    if any(map(lambda x : x > 2, types)):
        raise ValueError('histogram: can only use columns that are categorical or numeric.')

    dim = len(types)
    nbin = int(floor(1.0/pow((log(n)/n), (1.0/(dim + 1)))))
    print 'nbin:', nbin
    if nbin < 1:
        raise Exception('Internal error: nbin < 1 in histogram.')
    sizes = [nbin] * dim
    print 'sizes', sizes
    values = []
    newcolv = []
    for i,cn in enumerate(col_names):
        if types[i] == 0:
            vals = attd[cn]['values'].keys()
            newcol = colv[i]
        else:
            print cn
            a = attd[cn]['bounds']['lower']
            b = attd[cn]['bounds']['upper']
            extra = float(b-a)/1000
            w = float((b+extra)-a)/nbin # avoid index overflow if upper bound is encoutered
            vals = map(lambda i : a + i*w + w/2, range(nbin))
            check_bounds = lambda x : max(a, min(x, b)) # 'Windsorize' value
            newcol = map(lambda v : vals[int(floor((check_bounds(v) - a)/w))], colv[i])
        values.append(vals)
        sizes[i] == len(vals)
        newcolv.append(newcol)

    N = reduce(mul, sizes)
    if N > max_size:
        ValueError('Histogram too large.')
        
    discdata = zip(*newcolv)
    datad = {}
    for row in map(tuple, discdata):
        if datad.has_key(row):
            datad[row] += 1
        else:
            datad[row] = 1
    exclude = set(datad.keys())

    for nam, rw in sorted(datad.items()):
        print nam, ':', rw

    A = pdict['A']
    tau = A * log(n) / eps
    print 'tau', tau

    b = 2.0/eps
    plb = plaplace(tau, scale = b) # P(L > tau | L ~ Laplace(location = 0, scale = 2/eps))
    p = 0.5 * exp(-tau/b)

    print 'p', p
    print 'plb', plb
    
    assert(p < 1)
    nzero = int(round(p * (N - len(exclude)))) # number of extra to sample
    print 'nzero', nzero

    # 
    # quick and dirtly sampling
    datad2 = {}        
    for i in range(nzero):
        x = tuple(map(lambda j : choice(values[j]), range(dim)))
        while x in exclude:
            x = tuple(map(lambda j : choice(values[j]), range(dim)))
        print 'sampled', x
        exclude.add(x)
        datad2[x] = int(round(rlaplace(scale = b, r = plb)))

    for k, c in datad.items():
        noisy = rlaplace(scale = b, location = c)
        if noisy < tau:
            del datad[k]
        else:
            datad[k] = int(round(noisy))

    datad.update(datad2)
    return datad


    
proc_histogram = {
    'name': 'user_pref_count',
    'f' : histogram,
    'meta' : histogram_meta
    }
        
        
        
    
                    

processors = {'simple_count' : proc_simple_count,
              'user_pref_count' : proc_user_pref_count,
              'histogram' : proc_histogram}
