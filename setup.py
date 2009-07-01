#!/usr/bin/python
from setuptools import setup, find_packages
import os

setup(
    name = "gitfs",
    version = "0.1",
    packages = find_packages(),

    author = "Tommi Virtanen",
    author_email = "tv@eagain.net",
    description = "Filesystem-like API for Git repositories",
    long_description = """

TODO

""".strip(),
    license = "MIT",
    keywords = "git filesystem version-control",
    url = "http://eagain.net/software/pygitfs/",

    install_requires = [
        'filesystem',
        ],

    )
