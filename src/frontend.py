# -*-Python-*-
################################################################################
#
# File:         frontend.py
# RCS:          $Header: $
# Description:  frontend:
#               responsibility:
#               init backend
#               init processors
#               handle two query types:
#               1) metadata
#                  response: metadata from backend and processors
#               2) informational
#                  response: proccess(proc(query))(backend(info(query)))
# Author:       Staal Vinterbo
# Created:      Wed May  8 16:28:56 2013
# Modified:     Wed Jun 12 23:08:54 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# frontend.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# frontend.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with frontend.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

from backend import init_backend, query_backend

def init_frontend(database, processors):
    if len(processors) == 0:
        raise Exception('Failed to initialize frontend: no processors given.')
    try: 
        backend = init_backend(database)
    except Exception as e:
        raise Exception('Could not initialize backend: ' + str(e))

    pdict = {}
    for (k,v) in processors.items():
        pdict[k] = v['meta']

    meta = dict(backend['meta'])
    meta['processors'] = pdict
    
    return {'backend' : backend, 'processors' : processors, 'meta' : meta}


def handle_query(frontend, eps, query):
    if eps <= 0:
        raise Exception('Privacy risk must be positive.')
    
    try:
        (ddesc, proc) = query
        (pname, parms) = proc
        (dname, sel, pro) = ddesc
    except Exception as e:
        raise Exception('Malformed data query.')

    # check if data set exists and if processor is allowed
    if dname not in frontend['backend']['meta']['datasets'].keys():
        raise Exception('Requested data set not available.')        
    if pname not in frontend['backend']['meta']['datasets'][dname]['processors']:
        raise Exception('Requested information not appropriate for data set.')

    try:
        proc = frontend['processors'][pname]
    except Exception as e:
        raise Exception('Could not find query type: ' + str(e))

    try:
        if proc.has_key('query_edit'):
            parms += [('orig_query', {'predicate' :sel, 'attributes' : pro})]
            (sel, pro) = proc['query_edit'](sel, pro)
            ddesc = (dname, sel, pro)
    except Exception as e:
        raise Exception('Query edit failed: ' + str(e))
    
    try:
        res = query_backend(frontend['backend'], ddesc)
    except Exception as e:
        raise Exception('Data query failed: ' + str(e))
    try:
        pres = proc['f'](eps, parms, res)
    except Exception as e:
        raise Exception('Information processing failed: ' + str(e))
    return pres

    
        
    
    
