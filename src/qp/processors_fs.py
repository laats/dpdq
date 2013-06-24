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
# Modified:     Mon Jun 24 10:22:07 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# processors_fs.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# processors_fs.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with processors_fs.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['processors']

from random import random
from math import log, pow, exp, floor

from distributions import rlaplace
from histogram import discretize_data, noisy_histogram


######## Simple count processor
def simple_count(eps, parms, result):
    '''simple laplace noise added to row count and then rounded'''
    count = 0
    for r in result['data']:
        count += 1
    out = int(round(rlaplace(2.0/eps, count)))
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
            },
        'MinBins': { 'type' : 1,
                     'default' : 2,
                     'bounds' : {
                         'lower' : 1,
                         'upper' : 4
                     },
                     'description' : 'The minimum number of bins to discretize numerical values into.'
        }
    }
}


def histogram(eps, parms, result):
    '''perturbed count with user preferences'''

    col_names = result['attributes']
    dmeta = result['setd']
    pdict = dict(parms)
    data = list(result['data'])
    A = pdict['A']
    nbin_min = pdict['MinBins']
    tau = A * log(dmeta['size']) / float(eps)
    values, discdata = discretize_data(data, col_names, dmeta, nbin_min)
    h = noisy_histogram(values, discdata, A = pdict['A'], eps = eps, tau=tau)
    return {'col_names' : col_names, 'histogram' : h}


    
proc_histogram = {
    'name': 'user_pref_count',
    'f' : histogram,
    'meta' : histogram_meta
    }
        
        
        
    
                    

processors = {'simple_count' : proc_simple_count,
              'user_pref_count' : proc_user_pref_count,
              'histogram' : proc_histogram}
