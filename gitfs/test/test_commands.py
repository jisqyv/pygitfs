from nose.tools import (
    eq_ as eq,
    )

from gitfs.test.util import (
    maketemp,
    assert_raises,
    )

import os

from gitfs import commands

def check_repository(repo):
    assert os.path.isdir(repo)
    # it's a bare repo
    assert not os.path.exists(os.path.join(repo, '.git'))

    sha = commands.rev_parse(
        rev='refs/heads/master',
        repo=repo,
        )
    assert sha is None, 'Expected no commits yet: %r' % sha

    value = commands.get_symbolic_ref(repo=repo, ref='HEAD')
    eq(value, 'refs/heads/master')

def test_init():
    tmp = maketemp()
    commands.init_bare(tmp)
    check_repository(repo=tmp)

def test_init_repeat():
    tmp = maketemp()
    commands.init_bare(tmp)
    commands.init_bare(tmp)
    check_repository(repo=tmp)

def test_symbolic_ref_ok():
    tmp = maketemp()
    commands.init_bare(tmp)
    got = commands.get_symbolic_ref(repo=tmp, ref='HEAD')
    eq(got, 'refs/heads/master')

def test_symbolic_ref_bad_nonsymbolic():
    tmp = maketemp()
    commands.init_bare(tmp)
    e = assert_raises(
        # TODO better exception for this
        RuntimeError,
        commands.get_symbolic_ref,
        repo=tmp,
        ref='refs/heads/master',
        )
    eq(str(e), 'git symbolic-ref failed')

def test_rev_parse():
    tmp = maketemp()
    commands.init_bare(tmp)
    commands.fast_import(
        repo=tmp,
        commits=[
            dict(
                message='one',
                committer='John Doe <jdoe@example.com>',
                commit_time='1216235872 +0300',
                files=[
                    dict(
                        path='foo',
                        content='FOO',
                        ),
                    ],
                ),
            ],
        )
    got = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(got, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')

def test_ls_tree():
    tmp = maketemp()
    commands.init_bare(tmp)
    commands.fast_import(
        repo=tmp,
        commits=[
            dict(
                message='one',
                committer='John Doe <jdoe@example.com>',
                commit_time='1216235872 +0300',
                files=[
                    dict(
                        path='quux/foo',
                        content='FOO',
                        ),
                    dict(
                        path='bar',
                        content='BAR',
                        mode='100755',
                        ),
                    ],
                ),
            ],
        )
    g = commands.ls_tree(repo=tmp)
    eq(
        g.next(),
        dict(
            mode='100755',
            type='blob',
            object='add8373108657cb230a5379a6fcdaab73f330642',
            name='bar',
            ),
        )
    eq(
        g.next(),
        dict(
            mode='040000',
            type='tree',
            object='d513b699a47153aad2f0cb7ea2cb9fde8c177428',
            name='quux',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_ls_tree_all():
    tmp = maketemp()
    commands.init_bare(tmp)
    commands.fast_import(
        repo=tmp,
        commits=[
            dict(
                message='one',
                committer='John Doe <jdoe@example.com>',
                commit_time='1216235872 +0300',
                files=[
                    dict(
                        path='quux/foo',
                        content='FOO',
                        ),
                    dict(
                        path='bar',
                        content='BAR',
                        mode='100755',
                        ),
                    ],
                ),
            ],
        )
    g = commands.ls_tree(repo=tmp, children=False)
    eq(
        g.next(),
        dict(
            mode='100755',
            type='blob',
            object='add8373108657cb230a5379a6fcdaab73f330642',
            name='bar',
            ),
        )
    eq(
        g.next(),
        dict(
            mode='040000',
            type='tree',
            object='d513b699a47153aad2f0cb7ea2cb9fde8c177428',
            name='quux',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_cat_file_by_path():
    tmp = maketemp()
    commands.init_bare(tmp)
    commands.fast_import(
        repo=tmp,
        commits=[
            dict(
                message='one',
                committer='John Doe <jdoe@example.com>',
                commit_time='1216235872 +0300',
                files=[
                    dict(
                        path='quux/foo',
                        content='FOO',
                        ),
                    ],
                ),
            ],
        )
    g = commands.cat_file_by_path(repo=tmp, path='quux/foo')
    eq(g, 'FOO')

def test_cat_file_by_path_bad_notfound():
    tmp = maketemp()
    commands.init_bare(tmp)
    commands.fast_import(
        repo=tmp,
        commits=[
            dict(
                message='one',
                committer='John Doe <jdoe@example.com>',
                commit_time='1216235872 +0300',
                files=[
                    dict(
                        path='quux/foo',
                        content='FOO',
                        ),
                    ],
                ),
            ],
        )
    g = commands.cat_file_by_path(repo=tmp, path='does-not-exist')
    assert g is None

def test_write_object():
    tmp = maketemp()
    commands.init_bare(tmp)
    got = commands.write_object(repo=tmp, content='FOO')
    eq(got, 'd96c7efbfec2814ae0301ad054dc8d9fc416c9b5')

def test_read_tree():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    commands.fast_import(
        repo=repo,
        commits=[
            dict(
                message='one',
                committer='John Doe <jdoe@example.com>',
                commit_time='1216235872 +0300',
                files=[
                    dict(
                        path='quux/foo',
                        content='FOO',
                        ),
                    ],
                ),
            ],
        )
    index = os.path.join(tmp, 'index')

    assert not os.path.exists(index)
    commands.read_tree(
        repo=repo,
        treeish='HEAD',
        index=index,
        )
    assert os.path.isfile(index)
    st = os.stat(index)
    assert st.st_size > 0

def test_update_index():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')

    sha_foo = commands.write_object(repo=repo, content='FOO')
    sha_bar = commands.write_object(repo=repo, content='BAR')

    assert not os.path.exists(index)
    commands.update_index(
        repo=repo,
        index=index,
        files=[
            dict(
                sha1=sha_foo,
                path='quux/foo',
                ),
            dict(
                sha1=sha_bar,
                path='bar',
                ),
            ],
        )
    assert os.path.isfile(index)
    st = os.stat(index)
    assert st.st_size > 0
