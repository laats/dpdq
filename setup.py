# -*-Python-*-
################################################################################
#
# File:         setup.py
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Wed May  8 21:41:31 2013
# Modified:     Sun Mar 15 23:09:37 2015 (Staal Vinterbo) staal@mats.gateway.pace.com
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2013, Staal Vinterbo, all rights reserved.
#
################################################################################
"""dpdq: differentially private data querying."""

classifiers = """\
Development Status :: 3 - Alpha
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Topic :: Scientific/Engineering :: Artificial Intelligence
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Environment :: Console
"""

from glob import glob

#from distutils.core import setup
from setuptools import setup
from src.version import Version
from src.docstring import __doc__ as dstring
__doc__ = dstring
doclines = __doc__.split("\n")
versionshort = Version
pname = 'dpdq'

setup(name=pname,
      version=versionshort,
      author="Staal A. Vinterbo",
      author_email="sav@ucsd.edu",
      url = "http://laats.github.io/sw/dpdq/",
      license = "http://www.gnu.org/copyleft/gpl.html",
      platforms = ["any"],
      description = doclines[0],
      classifiers = filter(None, classifiers.split("\n")),
      long_description = "\n".join(doclines[2:]),
      package_dir = {pname:'./src'},
      package_data = {pname : ['wc/templates/*.html', 'wc/js/*.js', 'wc/css/*.css']},
      packages = [pname] + map(lambda x : pname + '.' + x, ['qp', 'cl', 'ra', 'wc']),
      scripts = glob('./scripts/dpdq*.py'),
      install_requires = ['python-gnupg >= 0.3.3',
                          'sqlalchemy >= 0.8.0',
                          'twisted >= 12.0.0',
                          'texttable >= 0.8.1',
                          'numpy >= 1.6.1',
                          'jinja2 >= 2.7']
      )

