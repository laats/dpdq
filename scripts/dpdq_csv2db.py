#!/usr/bin/env python
################################################################################
#
# File:         csv2db.py
# RCS:          $Header: $
# Description:  create a data base with a data set given in a csv file.
# Author:       Staal Vinterbo
# Created:      Tue May  7 19:37:13 2013
# Modified:     Mon Sep 16 09:33:09 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# dpdq_csv2db.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# dpdq_csv2db.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dpdq_csv2db.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

import csv
from sqlalchemy import Table, Column, Integer, String, Float, MetaData, ForeignKey

typecodes = {str : 0, int : 1, float : 2}

def get_type(column):
    '''determine column type'''
    a = set(map(type, column))
    types = [int, float, str]
    i = max(map(lambda (t,n) : (t in a) * (n + 1),  zip(types, range(len(types)))))
    return types[i-1]


def get_dataset(f):
    snf = csv.Sniffer().sniff(f.read(1024))
    snf.quoting = csv.QUOTE_NONNUMERIC
    f.seek(0)
    return list(csv.DictReader(f, dialect=snf))

def colnames(dataset):
    return dataset[0].keys()

def rowlist(dataset):
    keys = colnames(dataset)
    return map(lambda r: map(lambda k: r[k], keys), dataset)

def possibly_categorize(col, k = 4):
    print 'col', col
    vals = set(col)
    if vals == set(range(min(k, len(vals)))):
        return map(lambda x : str(x), col)
    return col

def columns(dataset):
    return map(list, zip(*rowlist(dataset)))

def col_types(dataset, trans = False):
    cols = columns(dataset)
    if trans:
        cols = map(possibly_categorize, cols)
    return map(get_type, cols)

def get_metadata(dataset, sname, ctrans = False):
    names = colnames(dataset)
    print '    in get_metadata: column names: ', names
    types = col_types(dataset, ctrans)
    def check(col, typ):
        if typ in [float, int]: return [min(col), max(col)]
        return list(set(col))
    adata = [(name, 'attribute ' + name,
             typecodes[typ], check(col, typ)) for name, typ, col
             in  zip(names, types, columns(dataset))]
    fst = lambda (a,b): a
    vi = map(fst, filter(lambda (i, x): x == str, enumerate(types)))
    bi = map(fst, filter(lambda (i, x): x != str, enumerate(types)))
    pick = lambda idx, v : [v[i] for i in idx]

    atpls = [{'set' : sname, 'name' : a, 'description' : b, 'type' : c} for a,b,c,d in adata]
    btpls = [{'set' : sname, 'attribute' : a, 'lower' : d[0], 'upper' : d[1]}
             for a,b,c,d in pick(bi, adata)]
    vtpls = []
    for i in vi:
        an = adata[i][0]
        vs = adata[i][3]
        vtpls += [{'set' : sname, 'attribute' : an, 'name' : x, 'description' : 'value for attribute ' + an}
                  for x in vs]
    stpls = [{'name' : sname, 'size' : len(dataset), 'description' : 'Converted data set'}]
    return(stpls, atpls, btpls, vtpls)
    
def make_md_tables(metadata, doit=True):
    '''create the metadata tables'''

    stable = Table('datasets', metadata,
                   Column('name', String(50), primary_key=True, nullable=False),
                   Column('size', Integer, nullable=False),                   
                   Column('description', String(200), default='no description given', nullable=False))
    atable = Table('attributes', metadata,
                   Column('name', String(50), primary_key=True, nullable=False),
                   Column('set', None, ForeignKey('datasets.name')),
                   Column('type', Integer, nullable=False),
                   Column('description', String(200), default='no description given', nullable=False))
    btable = Table('bounds', metadata,
                   Column('attribute', None, ForeignKey('attributes.name')),
                   Column('set', None, ForeignKey('datasets.name')),
                   Column('lower', Float, nullable=False),
                   Column('upper', Float, nullable=False))
    vtable = Table('values', metadata,
                   Column('attribute', None, ForeignKey('attributes.name')),
                   Column('set', None, ForeignKey('datasets.name')),
                   Column('name', String(50), nullable=False),
                   Column('description', String(200), default='no description given', nullable=False))
    qtable = Table('processors', metadata,
                   Column('set', None, ForeignKey('datasets.name')),
                   Column('type', Integer, nullable=False))
    tables = [stable, atable, btable, vtable, qtable]
    if doit:
        metadata.create_all(tables = tables)
    return tables

def make_data_table(metadata, dataset, name, trans = False, doit=True):
    table = Table(name, metadata)
    cnames = colnames(dataset)
    print '   column names:', cnames
    typs = col_types(dataset, trans)
    ttypes = [String(50), Integer, Float]
    for (nam, typ) in zip(cnames, typs):
        table.append_column(Column(nam, ttypes[typecodes[typ]]))
    if doit:
        metadata.create_all(tables = [table])
    return table

        
if __name__ == "__main__":    
    import sys
    import argparse as ap
    import os.path
    from sqlalchemy import create_engine

    parser = ap.ArgumentParser(description=
                               'Import a data set in csv file into the database. Creates meta data.'
        ' Note that the meta data created is computed from the data and is *not* differentially private.'
        ' The dataset is given the basename of the csvfile. If the database does not exist, it is created.')
    parser.add_argument("database_url", type=str, 
                        help = 'The RFC 1738 style url pointing to the database.'
        ' The format is dialect+driver://username:password@host:port/database.')
    parser.add_argument("csvfile", type=str, 
                        help = 'the csv file the data is in.')
    parser.add_argument('-v', "--version", action='store_true',
                        help = 'display version number and exit.')
    parser.add_argument('-n', "--no_categorize", action='store_false',
                        help = "Don't interpret integer columns with a full complement of values in range(x) where x < 5 as categorical")


    args = parser.parse_args()

    if args.version:
        print Version
        sys.exit(0)

    try:
        
        print 'reading data from', args.csvfile, '...'
        data = get_dataset(open(args.csvfile))
        print '  extracting metadata...'
        setname = os.path.basename(args.csvfile).rsplit('.', 1)[0].replace('.', '_')        
        mdata = get_metadata(data, setname, args.no_categorize)

        print 'naming data set ', setname
    except Exception as e:
        sys.stderr.write('Could not read and process data from ' + args.csvfile + '\n'
                         + str(e))
        sys.exit(1)
        
    try:
        print 'creating database engine...'
        engine = create_engine(args.database_url)
        print 'connecting to database...'
        conn = engine.connect()
    except Exception as e:
        sys.stderr.write('Could not connect to ' + args.database_url + '\n'
                         + str(e))
        sys.exit(1)

    metadata = MetaData(engine)

    print 'creating tables...'
    (stable, atable, btable, vtable, ptable) = make_md_tables(metadata)
    dtable = make_data_table(metadata, data, setname, args.no_categorize)

    print 'inserting metadata...'
    (stpls, atpls, btpls, vtpls) = mdata
    if stpls: conn.execute(stable.insert(), stpls)
    if atpls: conn.execute(atable.insert(), atpls)
    if vtpls: conn.execute(vtable.insert(), vtpls)
    if btpls: conn.execute(btable.insert(), btpls)
    conn.execute(ptable.insert(), [{'set' : setname, 'type' : x} for
                                   x in ['Simple_Count',
                                         'Histogram',
                                         'Tuned_Count',
                                         'Logistic_Regression']])

    print 'inserting data...'
    conn.execute(dtable.insert(), data)

    conn.close()
    print 'done.'
    
    

    

    
    
