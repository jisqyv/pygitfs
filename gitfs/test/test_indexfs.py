from __future__ import with_statement

from nose.tools import eq_ as eq

from gitfs.test.util import (
    maketemp,
    )

import os

from gitfs import indexfs
from gitfs import commands

def test_concurrent():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    index = os.path.join(tmp, 'index')
    commands.init_bare(repo)
    root = indexfs.IndexFS(
        repo=repo,
        index=index,
        )
    foo1 = root.child('foo')
    foo2 = root.child('foo')
    assert foo1 is not foo2
    with foo1.open('w') as f1:
        f1.write('one')
        f1.flush()
        with foo2.open('r') as f2:
            got = f2.read()
            eq(got, 'one')
