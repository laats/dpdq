################################################################################
#
# File:         Makefile
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Wed May  8 22:20:31 2013
# Modified:     Thu Jun 20 18:03:30 2013 (Staal Vinterbo) staal@mats
# Language:     BSDmakefile
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
# Makefile is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Makefile is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Makefile; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################

pname = dpdq

SRCDIR = ./src
SCRIPTDIR = ./scripts
BINSTALLDIR = /usr/local/bin
DOCDIR = ./doc
DOCSRC = $(DOCDIR)/docstring.mdwn $(DOCDIR)/*.png

PSRC = $(SRCDIR)/*.py $(SCRIPTDIR)/*.py setup.py

PINSTALL = pip install

options:
	@echo 'targets are: builds sdist egg dist love install'
	@echo 'to build and install do: make builds; sudo make install'
	@echo 'to see what each target does, do: make -n target'

builds: egg sdist demo.tgz

clean: 
	rm -f *.pyc *.aux *.log 

MANIFEST.in: MANIFEST.template Makefile
	cat MANIFEST.template > MANIFEST.in

$(SRCDIR)/docstring.py: $(DOCDIR)/docstring.mdwn
	echo '"""dpdq: differentially private data queries' > $@
	pandoc -f markdown -t rst  $< >> $@
	echo '"""' >> $@

readme.txt: $(DOCDIR)/docstring.mdwn
	pandoc -t plain $< > $@


demo.tgz: demo.sh gentestkeys.py 
	tar cvzf $@ $^ databases/*.csv


sdist: $(PSRC) readme.txt MANIFEST.in
	python setup.py sdist

egg: $(PSRC) 
	python setup.py bdist_egg

install.source: sdist
	$(PINSTALL) `ls -t dist/dpdq-*.tar.gz | head -1`

test.install: sdist
	$(PINSTALL) -U --no-deps --force-reinstall `ls -t dist/dpdq-*.tar.gz | head -1`

install: install.source


love:
	@echo 'your place or mine?'


