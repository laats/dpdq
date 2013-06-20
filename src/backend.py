# -*-Python-*-
################################################################################
#
# File:         backend.py
# RCS:          $Header: $
# Description:  the backend. Has the following responsibilities:
#               - extract and produce metadata
#               - interpret and execute queries
# Author:       Staal Vinterbo
# Created:      Wed May  8 10:11:37 2013
# Modified:     Wed Jun 19 15:29:33 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# backend.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# backend.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with backend.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['operators', 'CATEGORICAL', 'INTEGER', 'FLOAT', 'STRING', 'DATE',
           'init_backend', 'query_backend']

import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, MetaData, ForeignKey

needed_tables = ['datasets', 'attributes', 'bounds', 'values', 'processors']
needed_risk_tables = ['users', 'history']

# attribute type encodings
CATEGORICAL = 0
INTEGER = 1
FLOAT = 2
STRING = 3
DATE = 4

cat = lambda x,y : x + y

# operators: note that 'literal' is used to provide separation of symbol for the client
#            and implementation on the server. Also used to protect againts injection.
operators = {CATEGORICAL :
             {'==' : {'literal' : '==',  
                      'description' : 'equal to'},
              '!=' : {'literal' : '!=',
                      'description' : 'not equal to'}},
             INTEGER : {'==' : {'literal' : '==',
                                'description' : 'equal to'},
                        '!=' : {'literal' : '!=',
                                'description' : 'not equal to'},
                        '<'  : {'literal' : '<',
                                'description' : 'smaller than'},
                        '>' : {'literal' : '>',
                                'description' : 'greater than'},
                        '<=' : {'literal' : '<=',
                                'description' : 'smaller than or equal to'},
                        '>=' : {'literal' : '>=',
                                'description' : 'greater than or equal to'}},
             FLOAT : {'==' : {'literal' : '==',
                                'description' : 'equal to'},
                        '!=' : {'literal' : '!=',
                                'description' : 'not equal to'},
                        '<'  : {'literal' : '<',
                                'description' : 'smaller than'},
                        '>' : {'literal' : '>',
                                'description' : 'greater than'},
                        '<=' : {'literal' : '<=',
                                'description' : 'smaller than or equal to'},
                        '>=' : {'literal' : '>=',
                                'description' : 'greater than or equal to'}},
             STRING : {'==' : {'literal' : '==',
                                'description' : 'equal to'},
                        '!=' : {'literal' : '!=',
                                'description' : 'not equal to'},
                        '<'  : {'literal' : '<',
                                'description' : 'smaller than'},
                        '>' : {'literal' : '>',
                                'description' : 'greater than'},
                        '<=' : {'literal' : '<=',
                                'description' : 'smaller than or equal to'},
                        '>=' : {'literal' : '>=',
                                'description' : 'greater than or equal to'}},
             DATE : {'==' : {'literal' : '==',
                                'description' : 'equal to'},
                        '!=' : {'literal' : '!=',
                                'description' : 'not equal to'},
                        '<'  : {'literal' : '<',
                                'description' : 'smaller than'},
                        '>' : {'literal' : '>',
                                'description' : 'greater than'},
                        '<=' : {'literal' : '<=',
                                'description' : 'smaller than or equal to'},
                        '>=' : {'literal' : '>=',
                                'description' : 'greater than or equal to'}}}

def mk_cmp(typ, sym):
    '''create comparator from symbol for given type'''
    return eval('lambda x, y: x %s y' % operators[typ][sym]['literal'])


def get_meta(conn):
    '''get db metadata and list of offered data sets'''
    meta = sa.MetaData()
    meta.reflect(bind=conn, views=True)
    needed = set(needed_tables)
    if len(needed & set(meta.tables.keys())) != len(needed):
        raise Exception('Connected database does not have right metadata.')
    dtable = meta.tables['datasets']
    sets = reduce(cat, map(tuple, conn.execute(sa.select([dtable.c.name])).fetchall()))
    return (meta, sets)

def get_set_dict(meta, conn, sname):
    '''get metadata dict for dataset in sname'''
    (atable, btable, vtable, ptable) = map(lambda n: meta.tables[n], needed_tables[1:])
    s = sa.select([atable]).where(atable.c.set == sname)
    sdict = {}
    for atuple in conn.execute(s): # atuple = (name, set, type, description)
        (aname, aset, atyp, ax) = atuple
        adict = {'type' : atyp, 'description' : ax}
        res = []
        if atyp == CATEGORICAL: # get attribute (value, description) tuples
            sv = sa.select([vtable.c.name, vtable.c.description]).where((vtable.c.attribute == aname) &
                                                                        (vtable.c.set == sname))
            res = dict(conn.execute(sv).fetchall())
            adict['values'] = res
        elif atyp in [INTEGER, FLOAT]: # get attribute bounds
            sv = sa.select([btable.c.lower, btable.c.upper]).where((btable.c.attribute == aname) &
                                                                        (btable.c.set == sname))
            res = dict(zip(('lower', 'upper'), conn.execute(sv).fetchall()[0]))
            adict['bounds'] = res
        sdict[aname] = adict

    # get dataset processors
    sp = sa.select([ptable.c.type]).where(ptable.c.set == sname)
    procs = reduce(cat, map(tuple,conn.execute(sp).fetchall())) # need to convert RowProxy to tuple for cat to work

    # get dataset description
    stable = meta.tables['datasets']
    sd = sa.select([stable]).where(stable.c.name == sname)
    row = conn.execute(sd).fetchall()[0]
    cpairs = zip(map(lambda x : str(x.name),  stable.c), row)

    pairs = cpairs + [('attributes', sdict), ('processors', procs)]
    return dict(pairs)

def get_sets_dict(meta, conn, sets):
    '''get metadata dicts for datasets in sets'''
    return dict(zip(sets, map(lambda s : get_set_dict(meta, conn, s), sets)))

def get_backend_metadata(conn):
    (meta, sets) = get_meta(conn)
    return {'operators' : operators,
            'datasets'  : get_sets_dict(meta, conn, sets) }

def make_select(meta, setd, selection, projection):
    '''create a sqlalchemy executable select expression'''

    table = meta.tables[setd['name']]
    
    def desc(tup):
        '''translate descriptor into binary expression'''
        # checking of input could be done here, but is not...
        (a, o, v) = tup
        typ = setd['attributes'][a]['type']
        cmp = mk_cmp(typ, o)
        return cmp(table.c[a], v)

    def conj(tup):
        '''translate 'conjunction' into possibly negated conjuncion'''
        (neg, descs) = tup
        c = reduce(lambda x,y: x & y,
                   map(desc, descs))
        return sa.not_(c) if neg else c

    try:
        if projection:
            what = map(lambda k: table.c[k], projection)
        else :
            what = [table]

        if selection:
            where = reduce(lambda x,y: x | y,
                       map(conj, selection))
            s = sa.select(what).where(where)
        else:
            s = sa.select(what)

    except Exception as e:
        raise Exception('malformed query: ' + str(e))
    return s

def get_data_iterator(conn, sstmt):
    '''transforms RowProxies into tuples'''
    for row in conn.execute(sstmt):
        yield tuple(row)

def init_backend(database):
    '''initalize the backend'''
    engine = sa.create_engine(database)
    conn = engine.connect()
    (meta, sets) = get_meta(conn)
    data_meta = get_backend_metadata(conn)
    return {'schema' : meta, 'meta' : data_meta, 'engine': engine, 'connection' : conn}

def query_backend(backend, query):
    '''query the backend for the data'''

    (set, selection, projection) = query[:3]

    if projection == []:
        projection = map(lambda col : col.name, backend['schema'].tables[set].c)

    #    raise Exception('Query projection cannot be empty.')
    setd =  backend['meta']['datasets'][set]
    s = make_select(backend['schema'],setd, selection, projection)
    return {'data' : get_data_iterator(backend['connection'], s),
            'setd' : setd,
            'attributes': projection if projection else attrs }

def get_risk_meta(conn):
    '''get risk_db metadata'''
    meta = sa.MetaData()
    meta.reflect(bind=conn, views=True)
    needed = set(needed_risk_tables)
    if len(needed & set(meta.tables.keys())) != len(needed):
        raise Exception('Connected database does not have right metadata.')
    return meta
 

def init_risk_backend(database):
    '''initalize the risk backend'''
    engine = sa.create_engine(database)
    conn = engine.connect()
    meta = get_risk_meta(conn)
    return {'schema' : meta, 'engine': engine, 'connection' : conn}

def make_risk_tables(metadata, doit=True):
    '''create the metadata tables'''

    utable = Table('users', metadata,
                   Column('id', String(60), primary_key=True, nullable=False),
                   Column('info', String(200), nullable=False),                   
                   Column('tt', Float, default=10.0, nullable=False),
                   Column('qt', Float, default=3.0, nullable=False))    
    htable = Table('history', metadata,
                   Column('id', None, ForeignKey('users.id')),
                   Column('eps', Float, nullable=False),
                   Column('time', DateTime, server_default=sa.func.now(), nullable=False))
    tables = [utable, htable]
    if doit:
        metadata.create_all(tables = tables)
    return tables


            
if __name__ == "__main__":    
    import sys
    #try:
    backend = init_backend('sqlite:////tmp/dpdqserver/warehouse.db')
        #except Exception as e:
        #sys.stderr.write('Could not initialize backend: ' + str(e))
        #sys.exit(1)

    print backend['meta']

    sname = 'iris'
    projection = ['Species'] #, 'Petal_Width', 'Petal_Length']
    selection = [(0, [('Species', '!=', 'versicolor'), ('Petal_Length', '<=', 3)])]

    query = (sname, selection, projection)
    #try:
    result = query_backend(backend, query)
    #except Exception as e:
    #    sys.stderr.write('Could not query backend: ' + str(e))
    #    sys.exit(1)
        

    print '\t'.join(result['attributes'])
    count = 0
    for row in result['data']:
        print '\t'.join(map(str, row))
        count += 1
    print 'Total number of rows: ', count
