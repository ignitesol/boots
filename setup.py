#!/usr/bin/env python
from setuptools import find_packages, setup
from glob import glob

import boots


setup(name='boots',
      version=boots.__version__,
      description='Extensible framework for distributed systems',
      long_description=boots.__doc__,
      author=boots.__author__,
      author_email='boots@ignitesol.com',
      url='',
      packages=find_packages(),
      data_files=[ ('docs', glob('docs/source/*.rst') + ['docs/source/conf.py' ]) ],
      license='',
      platforms = 'any',
     )