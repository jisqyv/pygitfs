from __future__ import with_statement

from nose.tools import eq_ as eq

from gitfs.test.util import (
    maketemp,
    assert_raises,
    )

import errno
import os

from gitfs import repo
from gitfs import commands
from gitfs import readonly

def test_open():
    tmp = maketemp()
    commands.init_bare(tmp)
    r = repo.Repository(tmp)
    with r.transaction() as root:
        with root.child('foo').open('w') as f:
            f.write('FOO')
    with readonly.ReadOnlyGitFS(
        repo=tmp,
        rev='HEAD',
        ) as root:
        with root.child('foo').open() as f:
            got = f.read()
    eq(got, 'FOO')

def test_open_write():
    tmp = maketemp()
    commands.init_bare(tmp)
    with readonly.ReadOnlyGitFS(
        repo=tmp,
        rev='HEAD',
        ) as root:
        p = root.child('foo')
        e = assert_raises(
            IOError,
            p.open,
            'w',
            )
        eq(e.errno, errno.EROFS)
        eq(str(e), '[Errno %d] Read-only file system' % errno.EROFS)

def test_name():
    tmp = maketemp()
    commands.init_bare(tmp)
    r = repo.Repository(tmp)
    with readonly.ReadOnlyGitFS(
        repo=tmp,
        rev='HEAD',
        ) as root:
        p1 = root.child('foo')
        p2 = p1.child('bar')
        eq(p1.name(), 'foo')
        eq(p2.name(), 'bar')

def test_iter():
    tmp = maketemp()
    commands.init_bare(tmp)
    r = repo.Repository(tmp)
    with r.transaction() as root:
        with root.child('foo').open('w') as f:
            f.write('FOO')
        with root.child('bar').child('baz').open('w') as f:
            f.write('BAZ')
    with readonly.ReadOnlyGitFS(
        repo=tmp,
        rev='HEAD',
        ) as root:
        eq(
            sorted(root),
            sorted([root.child('foo'), root.child('bar')]),
            )
        eq(
            sorted(root.child('bar')),
            [root.child('bar').child('baz')],
            )
