# -*-Python-*-
################################################################################
#
# File:         query_dplr.py
# RCS:          $Header: $
# Description:  Pluggable query type for DPDQ implementing logistic regression
# Author:       Staal Vinterbo
# Created:      Fri Jun  7 07:38:27 2013
# Modified:     Wed Nov 13 12:33:27 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# query_dplr.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# query_dplr.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with query_dplr.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
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
    lam = pdict['lambda'] if pdict['lambda'] not in [None, '', ' ', 0] else ro.NA_Real
    res = dplr.dplr(ro.Formula(fml), ro.DataFrame(dfd), lam, eps=eps)
    d = dict(res.iteritems())     
    return dict(zip(d['par'].names, d['par']))

logistic_regression_meta = {
    'name' : 'Logistic_Regression',
    'description' :
    'L2-regularized logistic regression.'
    ' The first attribute selected is the response. '
    'If no others are selected, all others are used as covariates. '
    'All points are used for estimation, regardless of predicate.',
    'parameters' : {
        'lambda' : {'type': 2, 'default': None,
                    'bounds': { 'lower': 0.0, 'upper': 1.0 },
                    'description' : 'L2-regularizer value.'}}
}
proc_logistic_regression = {
    'name': 'Logistic_Regression',
    'f' : logistic_regression,
    'query_edit' : lambda sel, pro : ([], [] if len(pro) == 1 else pro),
    'meta' : logistic_regression_meta 
}
processors = {'Logistic_Regression' : proc_logistic_regression }


