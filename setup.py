# -*- coding: utf-8 -*-
#
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import ast
import re
from setuptools import setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('jotquote/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

with open('README.rst') as readme:
    long_description = readme.read()

setup(name='jotquote',
      description='A command-line interface for collecting and organizing quotes, and a quote of the day web server.',
      author='Jake Kugel',
      author_email='jake_kugel@yahoo.com',
      version=version,
      keywords='quotes',
      include_package_data=True,
      packages=['jotquote'],
      install_requires=[
          'flask >= 0.10.1',
          'configparser >= 3.5.0',
          'future >= 0.16.0'
      ],
      long_description=long_description,
      python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4',
      entry_points={  # Generate appropriate executables based on platform
          'console_scripts': [
              'jotquote = jotquote.cli:main'
          ],
      },
      url='',
      license='MIT License',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Environment :: Web Environment',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'License :: OSI Approved :: MIT License'
      ]
      )
