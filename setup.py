#!/usr/bin/env python
"""Distutils setup file"""
import sys
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

# Metadata
PROJECT = 'Crosscuts'
VERSION = '0.1'
TAGLINE = 'Dynamic variables ala Lisp (or AspectJ context-passing)'
MODULES = []
PACKAGES = NAMESPACES = ['peak', 'peak.util']

def get_description():
    # Get our long description from the documentation
    f = file('README.txt')
    lines = []
    for line in f:
        if not line.strip():
            break     # skip to first blank line
    for line in f:
        if line.startswith('.. contents::'):
            break     # read to table of contents
        lines.append(line)
    f.close()
    return ''.join(lines)

setup(
    name=PROJECT, version=VERSION, description=TAGLINE,
    url = "http://cheeseshop.python.org/pypi/" + PROJECT,
    download_url = "http://peak.telecommunity.com/snapshots/",
    long_description = get_description(),
    author="Phillip J. Eby", author_email="peak@eby-sarna.com",
    license="PSF or ZPL", test_suite = 'peak.util.crosscuts',
    packages = PACKAGES, namespace_packages = NAMESPACES, py_modules=MODULES,
    include_package_data = True, install_requires = [],
)
