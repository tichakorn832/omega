import pip
from setuptools import setup
import sys


name = 'omega'
description = 'Algorithms related to omega regular languages.'
url = 'https://github.com/johnyf/{name}'.format(name=name)
README = 'README.md'
VERSION_FILE = '{name}/_version.py'.format(name=name)
MAJOR = 0
MINOR = 0
MICRO = 1
version = '{major}.{minor}.{micro}'.format(
    major=MAJOR, minor=MINOR, micro=MICRO)
s = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n").format(version=version)
install_requires = [
    'dd >= 0.0.4',
    'ply >= 3.4',
    'networkx >= 1.9.1']
# TODO: mv the bitblaster to `omega` to avoid circular dependencies
tests_require = ['nose >= 1.3.4']


if __name__ == '__main__':
    with open(VERSION_FILE, 'w') as f:
        f.write(s)
    if 'egg_info' not in sys.argv:
        pip.main(['install'] + install_requires)
        from omega.logic import lexyacc
        lexyacc._rewrite_tables(outputdir='./omega/logic/')
    setup(
        name=name,
        version=version,
        description=description,
        long_description=open(README).read(),
        author='Ioannis Filippidis',
        author_email='jfilippidis@gmail.com',
        url=url,
        license='BSD',
        install_requires=install_requires,
        tests_require=tests_require,
        packages=[name, 'omega.logic', 'omega.symbolic'],
        package_dir={name: name},
        keywords=['logic'])