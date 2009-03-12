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

def test_set_sha1_simple():
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
    foo_sha = foo.git_get_sha1()
    bar = root.child('bar')
    bar.git_set_sha1(foo_sha)
    with bar.open() as f:
        got = f.read()
    eq(got, 'foo')

def test_set_sha1_missing():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    index = os.path.join(tmp, 'index')
    commands.init_bare(repo)
    root = indexfs.IndexFS(
        repo=repo,
        index=index,
        )
    bar = root.child('bar')
    # this succeeds but creates a broken index
    bar.git_set_sha1('deadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    got = bar.git_get_sha1()
    eq(got, 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    e = assert_raises(
        # TODO this really should be more specific
        RuntimeError,
        bar.open,
        )
    eq(str(e), 'git cat-file failed')

def test_set_sha1_mass():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    index = os.path.join(tmp, 'index')
    commands.init_bare(repo)
    root = indexfs.IndexFS(
        repo=repo,
        index=index,
        )
    one = root.child('one')
    with one.open('w') as f:
        f.write('one')
    one_sha = one.git_get_sha1()
    two = root.child('two')
    with two.open('w') as f:
        f.write('two')
    two_sha = two.git_get_sha1()

    bar = root.child('bar')
    quux = root.child('quux')
    thud = root.child('thud')
    root.git_mass_set_sha1([
            (bar, one_sha),
            (quux, two_sha),
            (thud, one_sha),
            ])
    with bar.open() as f:
        got = f.read()
    eq(got, 'one')
    with quux.open() as f:
        got = f.read()
    eq(got, 'two')
    with thud.open() as f:
        got = f.read()
    eq(got, 'one')

def test_open_readonly():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    index = os.path.join(tmp, 'index')
    commands.init_bare(repo)
    root = indexfs.IndexFS(
        repo=repo,
        index=index,
        )
    one = root.child('one')
    with one.open('w') as f:
        f.write('one')

    old = os.stat(index)
    with one.open() as f:
        _ = f.read(1)
    new = os.stat(index)
    # read only opens shouldn't bother editing the index, that just
    # slows things down
    eq(old.st_dev, new.st_dev)
    eq(old.st_ino, new.st_ino)
    eq(old.st_mtime, new.st_mtime)

def test_TemporaryIndexFS_simple():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    commands.init_bare(repo)
    t = indexfs.TemporaryIndexFS(repo=repo)
    with t as root:
        with root.child('bar').open('w') as f:
            f.write('hello')
    eq(t.tree, '4d9fa708931786c374d879e71f89f97a68e73f94')
    got = commands.cat_file(
        repo=repo,
        object='4d9fa708931786c374d879e71f89f97a68e73f94:bar',
        )
    eq(got, 'hello')

def test_TemporaryIndexFS_abort():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    commands.init_bare(repo)

    class MyException(Exception):
        pass

    try:
        t = indexfs.TemporaryIndexFS(repo=repo)
        with t as root:
            with root.child('bar').open('w') as f:
                f.write('hello')
            raise MyException()
    except MyException:
        pass
    else:
        raise RuntimeError('Must not eat MyException!')
    eq(t.tree, None)
