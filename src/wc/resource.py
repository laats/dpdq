#!/usr/bin/env python
################################################################################
#
# File:         skeleton.py
# RCS:          $Header: $
# Description:  Web interface, uses Jinja2 templating
# Author:       Staal Vinterbo
# Created:      Mon Apr  8 20:32:04 2013
# Modified:     Fri Jul  5 11:00:35 2013 (Staal Vinterbo) staal@mats
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# skeleton.py is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# skeleton.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with skeleton.py; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

__all__ = ['init_resource']

from urlparse import urlparse
import json
import math
from pprint import pformat
from collections import defaultdict

from twisted.web import resource, server
from twisted.internet import reactor
from twisted.web.resource import NoResource
from jinja2 import Environment, PackageLoader

import gnupg
from dpdq.wc.wproto import make_sender, State
from dpdq.messages import *    # needed for the QPRequest,QPResponse etc.
from texttable import Texttable

import pkgutil as pku
from mimetypes import guess_type

# like defaultdict(lambda : None) except no storing of missing keys
class tdict(dict):
    def __missing__(self, key):
        return None


wuli = lambda t, x : unicode(('<ul id="%s">' % (t,)) + x + '</ul>')
wulc = lambda t, x : unicode(('<ul class="%s">' % (t,)) + x + '</ul>')

def duck(v):
    for t in [int, float]:
        try:
            x = t(v)
            return x
        except:
            pass
    if v == 'None':
        return None
    return v


def htmlformat(r, qp_r):
    if r.status != QP_OK:
        return '<pre>\n' + str(r.response) + '\n</pre>'

    if type(r.response) == dict:
        if r.response.has_key('histogram'):
            header = r.response['col_names'] + ['count']
            hlen = len(header)
            table = Texttable(120)
            table.set_deco(Texttable.HEADER)
            table.set_cols_align(["l"]*(hlen - 1) + ['r'])
            table.set_cols_valign(["m"]*hlen)
            table.set_cols_dtype((['t']*(hlen - 1)) + ['i'])
            table.header(header)
            table.add_rows(
                map(lambda (k,v) : list(k) + [v],
                    sorted(r.response['histogram'].items(),
                           key = lambda (_,x) : x, reverse=True)),
                header=False)
            return '<pre>\n' + table.draw() + '\n</pre>'
        elif r.response.has_key('(Intercept)'):
            header = ['coefficient', 'value', 'odds ratio']
            hlen = len(header)
            table = Texttable(120)
            table.set_deco(Texttable.HEADER)
            table.set_cols_align(["l"]*(hlen - 1) + ['r'])
            table.set_cols_valign(["m"]*hlen)
            table.set_cols_dtype(['t'] + ['f']*(hlen - 1))
            table.header(header)
            table.add_rows(
                map(lambda (k,v) : [k, round(v,4), round(math.exp(v),4)],
                    sorted(r.response.items())),
                header=False)
            return '<pre>\n' + table.draw() + '\n</pre>'
        else:
            return ('<pre>\n' +
                    '\n'.join(str(k) + ': ' + str(v) for k,v in r.response.items())  +
                    '\n</pre>')
    else:
        return '<pre>\n' + str(r.response) + '\n</pre>'    
        

def resp_update(r, qp_request):
    if r.status != QP_OK:
        return {}
    if qp_request.type == QP_RISK:
        return r.response
    return {}
        


class kmap(dict):
    def __missing__(self, key):
        return 'data-' + str(key)


def init_resource(gpghome, key_id, qp_id, known_hosts, homepage):

    gpg = gnupg.GPG(gnupghome=gpghome)
    state = State(gpg, key_id, qp_id)

    # load template
    env = Environment(loader=PackageLoader('dpdq', 'wc/templates'),
                      line_statement_prefix = '#')
    template = env.get_template('dpdq.html')
    htemplate = env.get_template('host.html')
    ctemplate = env.get_template('cat.html')
    ntemplate = env.get_template('num.html')
    stemplate = env.get_template('str.html')

    class getter:
        def __init__(self, meta):
            self.meta = meta
            self.table = defaultdict(lambda : (lambda x : false, NoResource()),
                                     { 'd' : self.handle_descriptor,
                                       'a' : self.handle_attributes,
                                       'p' : self.handle_parameters,
                                       'r' : self.handle_risk })

            self.kmap = kmap({
                'description' : 'title',
                'type' : 'type'
                })

        # returns (true, QPRequest) or (false, response)
        # where response should be given to request.write()
        # if type(response) == 'str' response is set as json
        # if type(response) == 'unicode' it is assumed that
        # the response header is set
        # if type(response) not above, the response is
        # sent 'as is', i.e., assume it is a QPResponse object.
        def __call__(self, request):
            if request.path == '/':
                if 'q' in request.args:
                    try:
                        rval = self.table[request.args['q'][0]](request)
                    except Exception as e:
                        print 'error: ' + str(e)
                        request.setResponseCode(404)
                        return False, str({'error' : 'Unknown request.'})
                    return rval
                else:
                    return False, htemplate.render(hosts=known_hosts)
            else: # there is a path, so we try to serve it from package data
                try:
                    d = pku.get_data('dpdq.wc', request.path)
                    request.setHeader("content-type", guess_type(request.path)[0])
                    return False, unicode(d)
                except:
                    request.setResponseCode(404)
                    return False, unicode('Not found: ' + str(request.uri))

        def get(self, keys, fields = ['description'], classes = []):
            dd = self.meta
            for k in keys:
                dd = dd[k]
            prefix = '<li'
            if classes:
                prefix += ' class="' + ' '.join(classes) + '"'
            l = []
            if not fields:
                l = map(lambda k,v : prefix + ' title="%s">%s</li>' % (v,k),
                        dd.items())
            else:
                for key, d in dd.items():
                    s = prefix
                    for k in fields:
                        s += ' ' + self.kmap[k] + '="' + str(d[k]) + '"'
                    s += '>%s</li>' % (key,)
                    l.append(s)
            return l

        def getj(self, keys, fields = ['description']):
            dd = self.meta
            for k in keys:
                dd = dd[k]
            if not fields:
                x = dd
            else:
                x = map(dict,
                        [[('key', key)] + [(k, d[k]) for k in fields]
                         for key, d in dd.items()])
            return x

        def getp(self, request, what='a'):
            return request.args[what][0]

        def handle_attributes(self, request):
            return False, unicode('\n'.join(['<ul>'] + sorted(self.get(
                ['datasets', self.getp(request), 'attributes'],
                ['description', 'type'],
                classes = ['pickable', 'attribute'])) + ['</ul>']))

        def handle_parameters(self, request):
            ps = sorted(self.getj(['processors', self.getp(request), 'parameters'],
                           ['description', 'type', 'default']))
            l = map(lambda d : 
                    '<div class="parameter" title="%s" type="%s"><span class="name">%s</span>:<input type="%s" value="%s" size=8></div>' % (d['description'], d['type'], d['key'], 'number' if d['type'] in [1, 2] else 'text', d['default']), ps)
            return False, unicode('\n'.join(l) if l else 'No parameters.')

        def handle_descriptor(self, request):
            a = self.getp(request)
            b = self.getp(request, 'b')
            att = self.meta['datasets'][a]['attributes'][b]
            typ = int(att['type'])
            ops = self.meta['operators']

            #print ops[typ]

            if typ == 0: # categorical
                vals = sorted(att['values'].items())
                opl = [(k, d['description']) for k,d in ops[typ].items()]
                s = ctemplate.render(attribute=b, operator=opl[0][0],
                                     value=vals[0][0], olist=opl, vlist=vals)
            elif typ == 1 or typ == 2:
                bnds = att['bounds']
                val = bnds['lower'] + (bnds['upper'] - bnds['lower'])/2.0
                if typ == 1:
                    val = int(round(val - 0.5))
                opl = sorted([(k, d['description']) for k,d in ops[typ].items()])
                s = ntemplate.render(attribute=b, operator=opl[0][0],
                                     value=val,
                                     olist=opl, bounds=bnds)
            else:
                opl = [(k, d['description']) for k,d in ops[typ].items()]
                s = stemplate.render(attribute=b, operator=opl[0][0],
                                     value='Not set.', olist=opl)
            return False, unicode(s)


        def handle_risk(self, request):
            return True, QPRequest(QP_RISK, 'Demo')



    # twisted resource == url path
    class MyResource(resource.Resource):
        def __init__(self):
            self.isLeaf = True # we are a leaf, processing happens here

            # convenience interface to wproto.send_request
            self.send = make_sender(state, self.callback, timeout=5)
            self.getter = getter({})

            self.host = None
            self.port = None

        # send form
        def render_GET(self, request):
            # pick a host in known_hosts
            sendOn, res = self.getter(request)
            if not sendOn:
                #print 'res', str(res)
                if type(res) == str:
                    request.setHeader("content-type", "application/json")
                    return res.encode('ascii')
                elif type(res) == unicode:
                    return res.encode('ascii')
                else:
                    return res

            if not (self.host and self.port):
                request.setReseponseCode(404)
                return 'Error: No host set.'

            ### protocol code
            # create QPRequest
            try:
                self.send(res, request, self.host, self.port)
            except Exception as e:
                print 'Error with sending: ', str(e)
                request.setReseponseCode(404)
                return 'Error with sending.'

            ### end protocol code
            return server.NOT_DONE_YET


        # Splits handling of POST requests into two:
        # 1. parse request
        # 2. send QPRequest to QP
        # 3. hand control back to the reactor
        def render_POST(self, web_request):

            #print 'Got Post', web_request.args
            #print 'web_request', web_request


            # read in web request and parse
            fargs = tdict()
            for key, item in web_request.args.items():
                fargs[key] = item[0] 

            #print 'fargs', fargs

            qp_r = None

            if fargs['host'] != None:

                o = urlparse('//' + str(fargs['host']))

                # check if host makes sense
                if any(o[-1]) and o.hostname == '':
                    request.setReseponseCode(404)
                    return 'Please specify "host[:port]"'

                # got something that resembles host:port
                port = o.port if o.port else default_port
                hostport = o.hostname + ':' + str(port)

                # check if connection has been initiated
                # if not, try to initialize
                if hostport not in known_hosts:
                    request.setReseponseCode(404)
                    return 'Error: Unknown host %s.' % (hostport,)

                self.host = o.hostname
                self.port = port
                ### protocol code
                # create QPRequest 
                qp_r = QPRequest(QP_META, alias=web_request.getUser() or 'Demo')



            if fargs['info'] != None:
                #print fargs
                try:
                    rd = json.loads(fargs['info'])

                    for k,v in rd.items():
                        if type(v) == unicode:
                            rd[k] = v.encode('ascii')


                    rd['eps'] = float(rd['eps'])
                    pdict = dict(map(lambda (k,v) : (k,duck(v)), rd['parameters']))
                    l = []
                    for (bit, con) in rd['predicate']:
                        ll =  [(a,o,duck(v)) for (a,o,v) in map(tuple, con)]
                        l.append((bit, ll))
                    rd['predicate'] = l

                    parms = self.getter.meta['processors'][rd['processor']]['parameters']
                    for k in parms.keys():
                        if not pdict.has_key(k):
                            pdict[k] = parms[k]['default']

                    qp_r = QPRequest(QP_INFO, alias=web_request.getUser() or 'Demo',
                                     eps=rd['eps'],
                                     params=((rd['dataset'], rd['predicate'],
                                              rd['attributes']),
                                             (rd['processor'], pdict.items())))
                except Exception as e:
                    print 'failed to parse info request', e


            errormsg = 'Malformed request.'
            if qp_r != None:
                try:
                    self.send(qp_r, web_request, self.host, self.port)
                    return server.NOT_DONE_YET
                except Exception as e:
                    print 'Error sending: ', str(e)
                    errormsg = 'Could not talk to QP.'
                ### end protocol code


            # something is wrong

            #print 'something is wrong...'
            resp = {
                'status' : 500,
                'html'   : errormsg
            }

            web_request.setHeader("content-type", "application/json")
            web_request.setResponseCode(500)
            web_request.write(json.dumps({'response' : str(resp)}))
            web_request.finish()

            return server.NOT_DONE_YET

        # second half of POST request handling:
        # when reactor receives message from QP
        #    this function is called with
        #     r -- the QPResponse
        #     request -- the QPRequest we sent
        #     web_request -- the request that this
        #    resource got.
        # 4. finish rendering of the form   
        # 5. hand control back to the reactor
        def callback(self, r, qp_request, web_request):
            # note that type(r) == str means something went wrong
            # and r contains reason.

            if type(r) != str and r.status == QP_OK and qp_request.type == QP_META:
                self.getter.meta = r.response
                # serve template with ajax from now on
                dsets = self.getter.get(['datasets'],
                                        classes=['pickable dataset'])
                procs = self.getter.get(['processors'],
                                        classes=['pickable processor'])
                #print 'dsets', dsets
                #print 'procs', procs
                s = template.render(datasets = sorted(dsets),
                                    processors = sorted(procs),
                                    user=web_request.getUser() or 'Demo',
                                    homepage=homepage)
                web_request.write(s.encode('ascii'))
                web_request.finish()
                return

            if type(r) != str:
                try:
                    resp = {
                        'status' : r.status,
                        'html' : htmlformat(r, qp_request),
                    }
                except:
                    resp = {
                        'status' : 500,
                        'html' : 'Sorry, we are experiencing some problems.'
                    }


                resp.update(resp_update(r, qp_request))
                #print 'response: ', str(resp)

                web_request.setHeader("content-type", "application/json")
                web_request.write(json.dumps(resp))
                web_request.finish()
                return


            # something is wrong
            resp = {
                'status' : 500, # arbitrary choice
                'html'   : r.encode('ascii')
            }
            web_request.setHeader("content-type", "application/json")
            web_request.setResponseCode(500)
            web_request.write(json.dumps(resp))
            web_request.finish()

    return MyResource()

#### globals

if __name__ == '__main__':

    # init protocol state
    gpghome = '/tmp/dpdq/c'
    key_id = 'Alice'
    qp_id = 'QueryServer'
    # only connect to known hosts
    known_hosts = {'localhost:8123' : 'Demon' }


    root = init_resource(gpghome, key_id, qp_id, known_hosts,
                         'http://ptg.ucsd.edu/~staal/dpdq')

    # start twisted web server here:
    reactor.listenTCP(8082, server.Site(root))
    reactor.run()
