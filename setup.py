#!/usr/bin/env python
from setuptools import find_packages, setup
from glob import glob

import fabric


setup(name='fabric',
      version=fabric.__version__,
      description='Extensible framework for distributed systems',
      long_description=fabric.__doc__,
      author=fabric.__author__,
      author_email='fabric@ignitesol.com',
      url='',
      packages=find_packages(),
      data_files=[ ('docs', glob('docs/source/*.rst') + ['docs/source/conf.py' ]) ],
      license='',
      platforms = 'any',
     )