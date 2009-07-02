#!/usr/bin/python
from setuptools import setup, find_packages
import os

setup(
    name = "gitfs",
    version = "0.2",
    packages = find_packages(),

    author = "Tommi Virtanen",
    author_email = "tv@eagain.net",
    description = "Filesystem-like API for Git repositories",
    long_description = """

A pythonic filesystem API to Git, allowing you to access contents of
bare git repositories, including creating new commits.

""".strip(),
    license = "MIT",
    keywords = "git filesystem version-control",
#    url = "http://eagain.net/software/pygitfs/",
    url = "http://eagain.net/gitweb/?p=pygitfs.git",

    install_requires = [
        'filesystem',
        ],

    classifiers = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Operating System :: POSIX
Operating System :: Unix
Programming Language :: Python
Topic :: Software Development
Topic :: Software Development :: Libraries :: Python Modules
Topic :: Software Development :: Version Control
Topic :: System :: Archiving
Topic :: System :: Filesystems
""".splitlines(),

    )
