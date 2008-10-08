from __future__ import with_statement

from nose.tools import eq_ as eq

from gitfs.test.util import (
    maketemp,
    assert_raises,
    )

import errno
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

def test_get_sha1_simple():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    index = os.path.join(tmp, 'index')
    commands.init_bare(repo)
    root = indexfs.IndexFS(
        repo=repo,
        index=index,
        )
    foo = root.child('foo')
    with foo.open('w') as f:
        f.write('foo')
    got = foo.git_get_sha1()
    eq(got, '19102815663d23f8b75a47e7a01965dcdc96468c')
    got = root.child('foo').git_get_sha1()
    eq(got, '19102815663d23f8b75a47e7a01965dcdc96468c')

def test_get_sha1_nonexistent():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    index = os.path.join(tmp, 'index')
    commands.init_bare(repo)
    root = indexfs.IndexFS(
        repo=repo,
        index=index,
        )
    foo = root.child('foo')
    e = assert_raises(
        OSError,
        foo.git_get_sha1,
        )
    eq(e.errno, errno.ENOENT)
    eq(str(e), '[Errno %d] No such file or directory' % errno.ENOENT)
