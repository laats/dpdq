# -*-Python-*-
################################################################################
#
# File:         query_dplr.py
# RCS:          $Header: $
# Description:  Pluggable query type for DPDQ implementing logistic regression
# Author:       Staal Vinterbo
# Created:      Fri Jun  7 07:38:27 2013
# Modified:     Fri Jun  7 15:48:24 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
################################################################################

import rpy2.robjects as ro
from rpy2.robjects.packages import importr
import rpy2.rlike.container as rlc
dplr = importr('PrivateLR')

def logistic_regression(eps, parms, result):
    '''run PrivateLR::dplr'''
    # get meta data
    col_names = result['attributes']     
    types = map(lambda cn : result['setd']['attributes'][cn]['type'], col_names)
    pdict = dict(parms)

    # create dictionary of R vectors
    cols = zip(*list(result['data']))    
    tfun = [ro.FactorVector, ro.IntVector, ro.FloatVector]
    dfd = rlc.OrdDict(zip(col_names, map(lambda (tt,cc): tfun[tt](cc), zip(types, cols))))

    # create formula string (ascii as rpy2 does not like unicode)
    oattrs = pdict['orig_query']['attributes']    
    fml = ((oattrs[0] if oattrs else col_names[-1]) + ' ~ .').encode('ascii', 'ignore')

    # run dplr and return coefficients with names
    lam = pdict['lambda'] if pdict['lambda'] != None else ro.NA_Real
    res = dplr.dplr(ro.Formula(fml), ro.DataFrame(dfd), lam, eps=eps)
    d = dict(res.iteritems())     
    return dict(zip(d['par'].names, d['par']))

logistic_regression_meta = {
    'name' : 'logistic_regression',
    'description' : 'L2-regularized logistic regression.',
    'parameters' : {
        'lambda' : {'type': 2, 'default': None, 'bounds': { 'lower': 0.0, 'upper': 1.0 },
                    'description' : 'L2-regularizer value.'}}
}
proc_logistic_regression = {
    'name': 'logistic_regression',
    'f' : logistic_regression,
    'query_edit' : lambda sel, pro : ([], [] if len(pro) == 1 else pro),
    'meta' : logistic_regression_meta 
}
processors = {'logistic_regression' : proc_logistic_regression }


