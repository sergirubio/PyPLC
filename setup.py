#!/usr/bin/env python
# Always prefer setuptools over distutils
from setuptools import setup, find_packages

__doc__ = """

To install as system package:

  python setup.py install
  
To install as local package, just run:

  mkdir /tmp/builds/
  python setup.py install --root=/tmp/builds
  /tmp/builds/usr/bin/$DS -? -v4

To tune some options:

  RU=/opt/control
  python setup.py egg_info --egg-base=tmp install --root=$RU/files --no-compile \
    --install-lib=lib/python/site-packages --install-scripts=bin

-------------------------------------------------------------------------------
"""

# print(__doc__)

version = str(open('PyPLC/VERSION').read().strip())
license = 'GPL-3.0'

package_dir = {'PyPLC': 'PyPLC',}
packages = package_dir.keys()
package_data = {'PyPLC': ['VERSION'],}

setup(name = 'pyplc',
      author = 'Sergi Rubio',
      author_email="srubio@cells.es",
      version = version,
      license = license,
      description = 'Tango device for Modbus equipment',
      packages = packages,
      package_dir= package_dir,
      entry_points={
            'console_scripts': [
                  'PyPLC = PyPLC.PyPLC:main'
            ]
      },
      include_package_data = True,
      package_data = package_data,
      install_requires=['fandango>=14.6.0','PyTango'],
     )
