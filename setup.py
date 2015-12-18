#!/usr/bin/env python

from setuptools import setup


if __name__ == '__main__':
    summary = 'Pure-Python non-blocking IO functions'
    try:
        with open('README.rst', 'rt') as f:
            long_description = f.read()
    except:
        long_description = summary

    setup(name='python-nonblock',
            version='1.0.0',
            packages=['nonblock'],
            author='Tim Savannah',
            author_email='kata198@gmail.com',
            maintainer='Tim Savannah',
            url='https://github.com/kata198/python-nonblock',
            maintainer_email='kata198@gmail.com',
            description=summary,
            long_description=long_description,
            license='LGPLv2',
            keywords=['python', 'nonblock', 'nonblocking', 'io', 'blocking', 'non', 'read', 'read1', 'file', 'stream', 'pure', 'function'],
            classifiers=['Development Status :: 5 - Production/Stable',
                         'Programming Language :: Python',
                         'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
                          'Programming Language :: Python :: 2',
                          'Programming Language :: Python :: 2.7',
                          'Programming Language :: Python :: 3',
                          'Programming Language :: Python :: 3.4',
                          'Operating System :: POSIX',
                          'Operating System :: POSIX :: Linux',
                          'Operating System :: Unix',
                          'Operating System :: Microsoft :: Windows',
                          'Topic :: System',
            ]
    )



#vim: set ts=4 sw=4 expandtab
