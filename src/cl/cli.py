# -*-Python-*-
################################################################################
#
# File:         cli.py
# RCS:          $Header: $
# Description:  Command line query constructor
# Author:       Staal Vinterbo
# Created:      Thu May  9 16:03:40 2013
# Modified:     Tue Jun 25 14:42:28 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# cli.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# cli.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cli.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

import sys
from shlex import shlex
from cmd import Cmd
import pparser
import readline

from pprint import pprint
from textwrap import wrap

def filtero(text, options):
    '''filter used in tab completion'''
    return options if not text else [ f for f in options if f.startswith(text)  ]

class Cli(Cmd):

    def __init__(self, meta):
        Cmd.__init__(self)
        self.meta = meta
        self.exit = False
        self.outfile = None
        self.select = []
        self.project = []
        self.type = None
        self.params = {}
        self.eps = 1
        self.data = None
        self.expr = 'not set'
        self.prompt = '> '
        self.qtype = None
        self.print_ = lambda x : sys.stdout.write(x + '\n')


    def preloop(self):
        '''before starting the loop, remove readline deliminer chars'''
        self.delims = readline.get_completer_delims()
        ndelims = ''.join(x for x in self.delims if x not in '!=<>')
        readline.set_completer_delims(ndelims)

    def postloop(self):
        '''restore delimiter chars after the loop'''
        readline.set_completer_delims(self.delims)

    def do_EOF(self, line):
        '''EOF  -- quit without sending query by pressing the control key and 'd' at the same time.'''
        self.exit = True
        return True

    def do_run(self, line):
        '''run [OUTFILE] -- send query to query server. If OUTFILE is given, the computed result is copied to the file.'''
        n = [ #'predicate', 'columns',
            'dataset',
            'query type']

        unset = map(lambda (y,_) : y,
                    filter(lambda (_,x) : x == [] or x == None,
                           zip(n,
                               [ #self.select,
                                    #self.project,
                                   self.data,
                                   self.type])))
        if len(unset) > 0:
            self.print_('Cannot run without setting: ' + ', '.join(unset))
            return False
        self.qtype = 'info'
        self.outfile = line.strip()
        return True

    def do_quit(self, line):
        '''quit  -- quit without sending query.'''
        self.exit = True
        return True

    def do_columns(self, line):
        '''columns COLUMN [COLUMN]*   -- set columns (data attributes) you are interested in. If left unset, all columns are chosen.'''
        if self.data == None:
            self.print_('Sorry, need to set data first.')
        else:
            if line.strip() == '':
                self.print_('set columns to all')
                self.project = []
                return False
            cand = line.strip().split()
            allowed = set(self.meta['datasets'][self.data]['attributes'].keys())
            cool = [x for x in cand if x in allowed]
            not_cool = set(cand) - set(cool)
            if len(cool) == 0:
                self.print_('Sorry, no columns recognized.')
                return False
            self.project = cool
            if len(not_cool) > 0:
                self.print_('Not all columns were recognized.\nSkipped: ' + ' '.join(not_cool))
            self.print_('set columns to: ' + ' '.join(self.project))
        return False

    def complete_columns(self, text, line, begidx, endidx):
        if self.data == None:
            self.print_('\nSorry, need to set data first. Press [return] to return to prompt.')
            return False
        return filtero(text, self.meta['datasets'][self.data]['attributes'].keys())

    def do_type(self, line):
        '''type TYPE  -- sets query type.'''
        if line not in self.meta['processors'].keys():
            self.print_('Sorry, ' + str(line) + ' is not available')
        else:
            self.print_('Selecting type: ' + str(line))
            self.type = line
            pad = self.meta['processors'][line]['parameters']
            self.params = dict((x, pad[x]['default']) for x in pad.keys())
        return False

    def complete_type(self, text, line, begidx, endidx):
        return filtero(text, self.meta['processors'].keys())

    def do_value(self, line):
        '''value PARAMETER VALUE  -- set parameter for query type.'''
        if self.type == None:
            self.print_('Please select a query type first.')
            return False

        words = line.strip().split()
        if len(words) != 2:
            self.print_('Sorry, need exactly one parameter and one value.')
            return False

        parm, val = words
        
        if parm not in self.params.keys():
            self.print_('Sorry, it seems ' + parm + ' is not a parameter for the query type.')
            return False
        pad = self.meta['processors'][self.type]['parameters'][parm]
        ptype = pad['type']
        if ptype == 0 and val not in pad['values'].keys():
            self.print_('Sorry, ' + str(val) + ' is not a recogized value for this parameter.')
        if ptype == 1:
            try:
                val = int(val)
            except:
                self.print_('Sorry, the value must be an integer.')
                return False
        if ptype == 2:
            try:
                val = float(val)
            except:
                self.print_('Sorry, the value must be a float.')
                return False
        if ptype in [1,2]:
            if val < pad['bounds']['lower'] or val > pad['bounds']['upper']:
                self.print_('Sorry, the value is out of bounds.')
                return False
        self.params[parm] = val
        return False

    def complete_value(self, text, line, begidx, endidx):
        words = line.strip().split()[1:]

        if len(words) > 2:
            return []

        if len(words) == 2:
            parm, val = words
            if parm not in self.params.keys():
                return []
            pad = self.meta['processors'][self.type]['parameters'][parm]
            if pad['type'] == 0: # categorical
                return filtero(text, pad['values'].keys())
            return []
        return filtero(text, self.params.keys())

    def do_dataset(self, line):
        '''dataset DATASET  -- select data set.'''
        if line not in self.meta['datasets'].keys():
            print 'Sorry,', line, 'is not available'
        else:
            self.print_('Selecting data set: ' + line)
            self.data = line
            self.select = []
            self.project = []
        return False

    def complete_dataset(self, text, line, begidx, endidx):
        return filtero(text, self.meta['datasets'].keys())

    def do_predicate(self, line):
        '''predicate PREDICATE  -- input selection predicate (example: gender == male and age > 30). If left unset, all rows are selected.'''
        if self.data == None:
            self.print_('Cannot evaluate predicate without knowing the data set.\nPlease choose a data set first.')
        else:
            if line.strip() == '':
                self.select = []
                self.expr = '*'
                return False
                
            try: 
                lex = shlex(line)
                lex.wordchars += '!=<>.'
                tks = list(lex)
            except ValueError as err:
                fle = lex.token.splitlines()[0]
                self.print_('ERROR: ' + ' '.join([lex.error_leader(), str(err), ('following "' + fle + '"')]))
            else:
                parser = pparser.pparser(self.meta['datasets'][self.data],
                                         self.meta['operators'])
                status = parser(tks)
                if status == pparser.OK:
                    self.select = parser.p
                    self.expr = line
                else:
                    self.print_(' '.join(['ERROR:', parser.report, 'expected', parser.expected]))
                    self.print_('keeping previous predicate.')
        return False

    def complete_predicate(self, text, line, begidx, endidx):
        if self.data == None:
            self.print_('\nPlease choose a data set first. Hit [return] to return to prompt.')
            return []
        try: 
            lex = shlex(line)
            lex.wordchars += '!=<>.'
            tks = list(lex)[1:] # get rid of command
        except ValueError as err:
            #fle = lex.token.splitlines()[0]
            return [text]

        if text in ['<', '>']:
            tks = tks[:-1]

        parser = pparser.pparser(self.meta['datasets'][self.data], self.meta['operators'])
        status = parser(tks)
        if status == pparser.OK:
            return [f for f in ['and', 'or'] if text == '' or f.startswith(text) ]
        else:
            #print parser.expected, parser.report
            return [f for f in parser.expected if text == '' or f.startswith(text) ]

    def do_epsilon(self, line):
        '''epsilon NUMBER  -- set differential privacy risk level.'''
        num = pparser.tonum(line)
        if num == None or num <= 0:
            self.print_('Sorry, ' + line + ' is not a legal value.')
        else:
            self.eps = num

    def do_list(self, line):
        '''list datasets | types  -- list available datasets or query types.'''
        if line == '':
            self.print_('what do you want me to list?')
            return
        if line == 'datasets':
            for n,d in self.meta['datasets'].items():
                s = n + (': ' + '\n'.join(wrap(d['description'], 50, subsequent_indent = '   ')) if d.has_key('description') else '')
                self.print_(s)
        elif line == 'types':
            for n,d in self.meta['processors'].items():
                s = n + (': ' + '\n'.join(wrap(d['description'], 50, subsequent_indent = '    ')) if d.has_key('description') else '')
                self.print_(s)
        else:
            self.print_('Sorry, list argument "' + line + '" not recognized.')

    def complete_list(self, text, line, begidx, endidx):
        return filtero(text, ['datasets', 'types'])

            
    def do_show(self, line):
        '''show settings | dataset DATASET | type TYPE | risk -- show settings or info about dataset, query type, or user risk levels.'''

        words = line.strip().split()
        if len(words) < 1:
            self.print_('What do you want me to show?')
            return False

        cmd = words[0]
        arg = words[1] if len(words) > 1 else ''
        
        if cmd == 'settings':
            s = (' dataset    : %(data)s\n' +
                 ' columns    : %(attrs)s\n' +
                 ' type       : %(type)s\n' +
                 ' parameters : %(parms)s\n' +
                 ' eps        : %(eps)s\n' +
                 ' predicate  : %(pred)s\n'
                 ) % {
                     'data' : str(self.data),
                     'attrs': ' '.join(self.project),
                     'pred' : self.expr,
                     'type' : str(self.type),
                     'parms': str(self.params),
                     'eps'  : str(self.eps) }
            self.print_(s)
            return False

        elif cmd == 'dataset':
            if arg == '':
                print 'which dataset do you want me to show info about?.'
                return False
            try:
                dd = self.meta['datasets'][arg]
            except:
                self.print_('Sorry, ' + str(arg) + 'not available. Did you misspell the name?')
                return False

            ttype = {0 : 'categorical',
                     1 : 'integer',
                     2 : 'float',
                     3 : 'string',
                     4 : 'date'}
            
            self.print_('========== ' + str(arg) + ' ============')
            self.print_('\n'.join(wrap(dd['description'], 70)))
            self.print_('---------- columns --------------')
            attd = dd['attributes']
            for a,ad in attd.items():
                self.print_( str(a) + ': ' + str(ttype[ad['type']]))
                self.print_('    description: ' + '\n'.join(wrap(ad['description'], 50, subsequent_indent = '    ')))
                if ad['type'] == 0:
                    adv = ad['values']
                    self.print_('    values:')
                    for v in adv.keys():
                        self.print_('       ' + str(v) + ': ' + '\n'.join(wrap(adv[v], 60, subsequent_indent = '          ')))
                elif ad['type'] in [1,2]:
                    self.print_('    bounds: ' + str(ad['bounds']))
            return False

        elif cmd == 'type':
            if arg == '':
                self.print_('which query type?')
                return False
            try:
                pd = self.meta['processors'][arg]
            except:
                self.print_('Sorry, ' + str(arg) + ' not available. Did you misspell the name?')
                return False
            self.print_('========== ' + str(arg) + ' ============')
            self.print_('\n'.join(wrap(pd['description'], 70)))
            self.print_('---------- parameters --------------')         
            
            for p, v in pd['parameters'].items():
                self.print_('----------- ' + str(p) + ' ------------')
                self.print_('Description: ' + '\n'.join(wrap(v['description'], 60, subsequent_indent = '   ')))
                self.print_('Default value: ' + str(v['default']))
                if v.has_key('bounds'):
                    self.print_('Bounds: ' + ', '.join(map(lambda (x,y): x + ': ' + str(y), v['bounds'].items())))
                if v.has_key('values'):
                    self.print_('Values:')
                    for wk, we in v['values']:
                        self.print_(wrap(' ' + wk +': ' + we, 60, subsequent_indent = '   '))
                print ''

        elif cmd == 'risk':
            self.qtype = 'risk'
            return True
        else:
            self.print_('Unrecognized show parameter: ' + line)
        
        return False

    def complete_show(self, text, line, begidx, endidx):
        words = line.strip().split()

        if len(words) > 1 and words[1] == 'dataset':
            return filtero(text, self.meta['datasets'].keys())
        if len(words) > 1 and words[1] == 'type':
            return filtero(text, self.meta['processors'].keys())
        return filtero(text, ['dataset', 'settings', 'type', 'risk'])
        
    
if __name__ == '__main__':

        
    meta = {'operators':
            {0: {'==': {'literal': '==', 'description': 'equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}}, 1: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}, 2: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}, 3: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}, 4: {'>=': {'literal': '>=', 'description': 'greater than or equal to'}, '==': {'literal': '==', 'description': 'equal to'}, '<=': {'literal': '<=', 'description': 'smaller than or equal to'}, '!=': {'literal': '!=', 'description': 'not equal to'}, '<': {'literal': '<', 'description': 'smaller than'}, '>': {'literal': '>', 'description': 'greater than'}}},
            'datasets': {u'iris': {'attributes': {u'Sepal_Width': {'description': u'attribute Sepal_Width', 'type': 2, 'bounds': {'upper': 4.4, 'lower': 2.0}}, u'Petal_Width': {'description': u'attribute Petal_Width', 'type': 2, 'bounds': {'upper': 2.5, 'lower': 0.1}}, u'Species': {'values': {u'setosa': u'value for attribute Species', u'versicolor': u'value for attribute Species', u'virginica': u'value for attribute Species'}, 'description': u'attribute Species', 'type': 0}, u'Sepal_Length': {'description': u'attribute Sepal_Length', 'type': 2, 'bounds': {'upper': 7.9, 'lower': 4.3}}, u'Petal_Length': {'description': u'attribute Petal_Length', 'type': 2, 'bounds': {'upper': 6.9, 'lower': 1.0}}}, 'name': u'iris', 'processors': (u'simple_count',)}},
            'processors': {'simple_count': {'description': 'Produces a noise count of matching rows. Laplace(2/eps, 0) is added to the real count and the result is rounded to the nearest integer.', 'name': 'simple_count', 'parameters': {}}}}
        

    cli = Cli(meta)
    cli.cmdloop()

    print cli.select
