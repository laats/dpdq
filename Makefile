################################################################################
#
# File:         Makefile
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Wed May  8 22:20:31 2013
# Modified:     Mon Jul  8 08:52:02 2013 (Staal Vinterbo) staal@mats
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
DOCDIR = ./doc


PSRC = $(SRCDIR)/docstring.py $(SRCDIR)/*.py $(SRCDIR)/ra/*.py $(SRCDIR)/cl/*.py \
	$(SRCDIR)/qp/*.py $(SCRIPTDIR)/*.py setup.py

PINSTALL = pip install

options:
	@echo 'targets are: builds sdist egg dist doc love install'
	@echo 'to build and install do: make builds; sudo make install'
	@echo 'to see what each target does, do: make -n target'

builds: egg sdist demo.tgz

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

doc: $(pname).pdf

$(pname).pdf : $(DOCDIR)/docstring.mdwn
	pandoc -s -S --toc -V geometry:margin=1in -o $@ $<

install.source: sdist
	$(PINSTALL) `ls -t dist/dpdq-*.tar.gz | head -1`

test.install: sdist
	$(PINSTALL) -U --no-deps --force-reinstall `ls -t dist/dpdq-*.tar.gz | head -1`

install: install.source


love:
	@echo 'your place or mine?'


