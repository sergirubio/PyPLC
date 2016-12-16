#!/usr/bin/env python
# Always prefer setuptools over distutils
from setuptools import setup, find_packages

__doc__ = """
To install as system package:

  python setup.py install
  
To install as local package:

  RU=/opt/control
  python setup.py egg_info --egg-base=tmp install --root=$RU/files --no-compile \
    --install-lib=lib/python/site-packages --install-scripts=ds

-------------------------------------------------------------------------------
"""

print(__doc__)

version = open('VERSION').read().strip()
scripts = ['PyPLC']
license = 'GPL-3.0'

package_dir = {
    'PyPLC': '.',
}
packages = package_dir.keys()

package_data = {
    '': ['VERSION'],
}

packages = package_dir.keys()


setup(name = 'tangods-pyplc',
      version = version,
      license = license,
      description = 'Tango device for Modbus equipment',
      packages = packages,
      package_dir= package_dir,
      scripts = scripts,
      include_package_data = True,
      package_data = package_data
     )
