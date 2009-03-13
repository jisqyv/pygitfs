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

def test_init_atomic():
    tmp = maketemp()
    commands.init_bare_atomic(
        repo=os.path.join(tmp, 'repo'),
        tmp=os.path.join(tmp, 'repo.42.tmp'),
        )
    eq(os.listdir(tmp), ['repo'])
    check_repository(repo=os.path.join(tmp, 'repo'))

def test_init_atomic_repeat():
    tmp = maketemp()
    commands.init_bare_atomic(
        repo=os.path.join(tmp, 'repo'),
        tmp=os.path.join(tmp, 'repo.42.tmp'),
        )
    commands.init_bare_atomic(
        repo=os.path.join(tmp, 'repo'),
        tmp=os.path.join(tmp, 'repo.42.tmp'),
        )
    eq(os.listdir(tmp), ['repo'])
    check_repository(repo=os.path.join(tmp, 'repo'))

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

def test_rev_parse_no_initial():
    tmp = maketemp()
    commands.init_bare(tmp)
    got = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(got, None)

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
            path='bar',
            ),
        )
    eq(
        g.next(),
        dict(
            mode='040000',
            type='tree',
            object='d513b699a47153aad2f0cb7ea2cb9fde8c177428',
            path='quux',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_ls_tree_children_false():
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
    g = commands.ls_tree(repo=tmp, path='quux', children=False)
    eq(
        g.next(),
        dict(
            mode='040000',
            type='tree',
            object='d513b699a47153aad2f0cb7ea2cb9fde8c177428',
            path='quux',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_ls_tree_children_true():
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
    g = commands.ls_tree(repo=tmp, path='quux', children=True)
    eq(
        g.next(),
        dict(
            type='blob',
            mode='100644',
            object='d96c7efbfec2814ae0301ad054dc8d9fc416c9b5',
            path='quux/foo',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_ls_tree_recursive():
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
    g = commands.ls_tree(repo=tmp, recursive=True)
    eq(
        g.next(),
        dict(
            mode='100755',
            type='blob',
            object='add8373108657cb230a5379a6fcdaab73f330642',
            path='bar',
            ),
        )
    eq(
        g.next(),
        dict(
            type='blob',
            mode='100644',
            object='d96c7efbfec2814ae0301ad054dc8d9fc416c9b5',
            path='quux/foo',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_cat_file():
    tmp = maketemp()
    commands.init_bare(tmp)
    sha1 = commands.write_object(repo=tmp, content='FOO')
    eq(sha1, 'd96c7efbfec2814ae0301ad054dc8d9fc416c9b5')
    got = commands.cat_file(repo=tmp, object=sha1)
    eq(got, 'FOO')

def test_cat_file_bad_notfound():
    tmp = maketemp()
    commands.init_bare(tmp)
    e = assert_raises(
        # TODO better exception for this
        RuntimeError,
        commands.cat_file,
        repo=tmp,
        object='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        )
    eq(str(e), 'git cat-file failed')

def test_batch_cat_file():
    tmp = maketemp()
    commands.init_bare(tmp)
    one = commands.write_object(repo=tmp, content='FOO')
    two = commands.write_object(repo=tmp, content='BAR')
    g = commands.batch_cat_file(repo=tmp)

    got = g.send(one)
    eq(sorted(got.keys()), ['contents', 'object', 'size', 'type'])
    eq(got['type'], 'blob')
    eq(got['size'], 3)
    eq(got['object'], one)
    eq(got['contents'].read(), 'FOO')

    got = g.send(two)
    eq(sorted(got.keys()), ['contents', 'object', 'size', 'type'])
    eq(got['type'], 'blob')
    eq(got['size'], 3)
    eq(got['object'], two)
    eq(got['contents'].read(), 'BAR')

    g.close()

def test_batch_cat_file_bad_notfound():
    tmp = maketemp()
    commands.init_bare(tmp)
    one = commands.write_object(repo=tmp, content='FOO')
    g = commands.batch_cat_file(repo=tmp)

    got = g.send('deadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    eq(sorted(got.keys()), ['object', 'type'])
    eq(got['type'], 'missing')
    eq(got['object'], 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef')

    # it should still be usable after the error
    got = g.send(one)
    eq(sorted(got.keys()), ['contents', 'object', 'size', 'type'])
    eq(got['type'], 'blob')
    eq(got['size'], 3)
    eq(got['object'], one)
    eq(got['contents'].read(), 'FOO')

    g.close()

def test_get_object_size():
    tmp = maketemp()
    commands.init_bare(tmp)
    sha1 = commands.write_object(repo=tmp, content='FOO')
    eq(sha1, 'd96c7efbfec2814ae0301ad054dc8d9fc416c9b5')
    got = commands.get_object_size(repo=tmp, object=sha1)
    eq(got, 3)

def test_get_object_size_bad_notfound():
    tmp = maketemp()
    commands.init_bare(tmp)
    e = assert_raises(
        # TODO better exception for this
        RuntimeError,
        commands.get_object_size,
        repo=tmp,
        object='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        )
    eq(str(e), 'git cat-file failed')

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
                object=sha_foo,
                path='quux/foo',
                ),
            dict(
                object=sha_bar,
                path='bar',
                ),
            ],
        )
    assert os.path.isfile(index)
    st = os.stat(index)
    assert st.st_size > 0

def test_ls_files():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
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
                    dict(
                        path='bar',
                        content='BAR',
                        mode='100755',
                        ),
                    ],
                ),
            ],
        )
    commands.read_tree(
        repo=repo,
        treeish='HEAD',
        index=index,
        )
    g = commands.ls_files(
        repo=repo,
        index=index,
        )
    eq(
        g.next(),
        dict(
            mode='100755',
            object='add8373108657cb230a5379a6fcdaab73f330642',
            path='bar',
            ),
        )
    eq(
        g.next(),
        dict(
            mode='100644',
            object='d96c7efbfec2814ae0301ad054dc8d9fc416c9b5',
            path='quux/foo',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_ls_files_path():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
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
                    dict(
                        path='bar',
                        content='BAR',
                        mode='100755',
                        ),
                    ],
                ),
            ],
        )
    commands.read_tree(
        repo=repo,
        treeish='HEAD',
        index=index,
        )
    g = commands.ls_files(
        repo=repo,
        index=index,
        path='quux',
        )
    eq(
        g.next(),
        dict(
            mode='100644',
            object='d96c7efbfec2814ae0301ad054dc8d9fc416c9b5',
            path='quux/foo',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_write_tree():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
    sha_foo = commands.write_object(repo=repo, content='FOO')
    sha_bar = commands.write_object(repo=repo, content='BAR')
    commands.update_index(
        repo=repo,
        index=index,
        files=[
            dict(
                object=sha_foo,
                path='quux/foo',
                ),
            dict(
                object=sha_bar,
                path='bar',
                ),
            ],
        )

    tree = commands.write_tree(
        repo=repo,
        index=index,
        )
    eq(tree, 'e8abc9dd8c483a4e27598521674ae7a357d2c825')

    g = commands.ls_tree(repo=repo, treeish=tree)
    eq(
        g.next(),
        dict(
            mode='100644',
            type='blob',
            object='add8373108657cb230a5379a6fcdaab73f330642',
            path='bar',
            ),
        )
    eq(
        g.next(),
        dict(
            mode='040000',
            type='tree',
            object='d513b699a47153aad2f0cb7ea2cb9fde8c177428',
            path='quux',
            ),
        )
    assert_raises(StopIteration, g.next)

def test_commit_tree():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
    commands.fast_import(
        repo=repo,
        ref='refs/heads/import',
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
    tree = commands.rev_parse(
        repo=repo,
        rev='refs/heads/import^{tree}',
        )
    eq(tree, 'd513b699a47153aad2f0cb7ea2cb9fde8c177428')

    commit = commands.commit_tree(
        repo=repo,
        tree=tree,
        parents=[],
        message='made some changes',
        committer_name='John Doe',
        committer_email='jdoe@example.com',
        committer_date='1216337226 +0300',
        author_name='Bob Smith',
        author_email='bob@example.com',
        author_date='1216337225 +0300',
        )
    eq(commit, '7a95f3e3276c9704d290375660fb143a3fe0bbcb')

def test_is_commit_needed_root_empty():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
    tree = commands.write_tree(
        repo=repo,
        index=index,
        )
    got = commands.is_commit_needed(
        repo=repo,
        tree=tree,
        parents=[],
        )
    eq(got, False)

def test_is_commit_needed_root_simple():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
    sha_foo = commands.write_object(repo=repo, content='FOO')
    commands.update_index(
        repo=repo,
        index=index,
        files=[
            dict(
                object=sha_foo,
                path='quux/foo',
                ),
            ],
        )
    tree = commands.write_tree(
        repo=repo,
        index=index,
        )
    got = commands.is_commit_needed(
        repo=repo,
        tree=tree,
        parents=[],
        )
    eq(got, True)

def test_is_commit_needed_merge():
    got = commands.is_commit_needed(
        repo='/does-not-exist',
        tree='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        parents=[
            '1111111111111111111111111111111111111111',
            '2222222222222222222222222222222222222222',
            ],
        )
    eq(got, True)

def test_is_commit_needed_no_change():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
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
    head = commands.rev_parse(repo=tmp, rev='HEAD')
    tree = commands.rev_parse(repo=tmp, rev='HEAD^{tree}')
    got = commands.is_commit_needed(
        repo=repo,
        tree=tree,
        parents=[head],
        )
    eq(got, False)

def test_is_commit_needed_has_change():
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
    head = commands.rev_parse(repo=tmp, rev='HEAD')
    tree = commands.rev_parse(repo=tmp, rev='HEAD^{tree}')
    got = commands.is_commit_needed(
        repo=tmp,
        tree='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        parents=[head],
        )
    eq(got, True)

def test_is_commit_needed_no_change():
    tmp = maketemp()
    repo = os.path.join(tmp, 'repo')
    os.mkdir(repo)
    commands.init_bare(repo)
    index = os.path.join(tmp, 'index')
    sha_foo = commands.write_object(repo=repo, content='FOO')
    commands.update_index(
        repo=repo,
        index=index,
        files=[
            dict(
                object=sha_foo,
                path='quux/foo',
                ),
            ],
        )
    tree = commands.write_tree(
        repo=repo,
        index=index,
        )
    got = commands.is_commit_needed(
        repo=repo,
        tree=tree,
        parents=[],
        )
    eq(got, True)

def test_update_ref():
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
    head = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(head, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/foo',
        newvalue=head,
        )
    got = commands.rev_parse(repo=tmp, rev='refs/heads/foo')
    eq(got, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')

def test_update_ref_oldvalue_ok():
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
    head = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(head, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/foo',
        newvalue=head,
        oldvalue=40*'0',
        )
    got = commands.rev_parse(repo=tmp, rev='refs/heads/foo')
    eq(got, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')

def test_update_ref_oldvalue_bad():
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
    head = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(head, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')
    e = assert_raises(
        # TODO better exception for this
        RuntimeError,
        commands.update_ref,
        repo=tmp,
        ref='HEAD',
        newvalue=head,
        oldvalue='deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        )
    eq(str(e), 'git update-ref failed')
    got = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(got, head)

def test_update_ref_delete():
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
    head = commands.rev_parse(repo=tmp, rev='HEAD')
    eq(head, 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/master',
        newvalue=None,
        )
    got = commands.rev_parse(repo=tmp, rev='refs/heads/master')
    eq(got, None)

# TODO unit test update_ref reason!=None

def test_rev_list():
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
            dict(
                message='two',
                committer='Jack Smith <smith@example.com>',
                commit_time='1216235940 +0300',
                files=[
                    dict(
                        path='foo',
                        content='FOO',
                        ),
                    dict(
                        path='bar',
                        content='BAR',
                        ),
                    ],
                ),
            ],
        )
    got = commands.rev_list(repo=tmp)
    got = iter(got)
    eq(got.next(), '27f952fd48ce824454457b9f28bb97091bc5422e')
    eq(got.next(), 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')
    assert_raises(StopIteration, got.next)

def test_rev_list_exclude():
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
            dict(
                message='two',
                committer='Jack Smith <smith@example.com>',
                commit_time='1216235940 +0300',
                files=[
                    dict(
                        path='foo',
                        content='FOO',
                        ),
                    dict(
                        path='bar',
                        content='BAR',
                        ),
                    ],
                ),
            ],
        )
    got = commands.rev_list(
        repo=tmp,
        exclude=['e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27'],
        )
    got = iter(got)
    eq(got.next(), '27f952fd48ce824454457b9f28bb97091bc5422e')
    assert_raises(StopIteration, got.next)

def test_rev_list_reverse():
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
            dict(
                message='two',
                committer='Jack Smith <smith@example.com>',
                commit_time='1216235940 +0300',
                files=[
                    dict(
                        path='foo',
                        content='FOO',
                        ),
                    dict(
                        path='bar',
                        content='BAR',
                        ),
                    ],
                ),
            ],
        )
    got = commands.rev_list(
        repo=tmp,
        reverse=True,
        )
    got = iter(got)
    eq(got.next(), 'e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27')
    eq(got.next(), '27f952fd48ce824454457b9f28bb97091bc5422e')
    assert_raises(StopIteration, got.next)

def test_for_each_ref_simple():
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
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/quux',
        newvalue='HEAD',
        oldvalue=40*'0',
        )
    got = commands.for_each_ref(
        repo=tmp,
        )
    got = iter(got)
    eq(got.next(), dict(refname='refs/heads/master'))
    eq(got.next(), dict(refname='refs/heads/quux'))
    assert_raises(StopIteration, got.next)

def test_for_each_ref_count():
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
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/quux',
        newvalue='HEAD',
        oldvalue=40*'0',
        )
    got = commands.for_each_ref(
        repo=tmp,
        count=1,
        )
    got = iter(got)
    eq(got.next(), dict(refname='refs/heads/master'))
    assert_raises(StopIteration, got.next)

def test_for_each_ref_sort():
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
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/quux',
        newvalue='HEAD',
        oldvalue=40*'0',
        )
    got = commands.for_each_ref(
        repo=tmp,
        sort='-refname',
        )
    got = iter(got)
    eq(got.next(), dict(refname='refs/heads/quux'))
    eq(got.next(), dict(refname='refs/heads/master'))
    assert_raises(StopIteration, got.next)

def test_for_each_ref_fields():
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
            dict(
                message='two',
                committer='Jack Smith <smith@example.com>',
                commit_time='1216235940 +0300',
                files=[
                    dict(
                        path='foo',
                        content='FOO',
                        ),
                    dict(
                        path='bar',
                        content='BAR',
                        ),
                    ],
                ),
            ],
        )
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/quux',
        newvalue='HEAD~1',
        oldvalue=40*'0',
        )
    got = commands.for_each_ref(
        repo=tmp,
        fields=['refname', 'objecttype', 'objectname'],
        )
    got = iter(got)
    eq(
        got.next(),
        dict(
            refname='refs/heads/master',
            objecttype='commit',
            objectname='27f952fd48ce824454457b9f28bb97091bc5422e',
            ),
        )
    eq(
        got.next(),
        dict(
            refname='refs/heads/quux',
            objecttype='commit',
            objectname='e1b2f3253b18e7bdbd38db0cf295e6b3b608bb27',
            ),
        )
    assert_raises(StopIteration, got.next)

def test_for_each_ref_patterns():
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
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/quux',
        newvalue='HEAD',
        oldvalue=40*'0',
        )
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/notme',
        newvalue='HEAD',
        oldvalue=40*'0',
        )
    commands.update_ref(
        repo=tmp,
        ref='refs/heads/thud/xyzzy',
        newvalue='HEAD',
        oldvalue=40*'0',
        )
    got = commands.for_each_ref(
        repo=tmp,
        patterns=[
            'refs/heads/thud',
            'refs/heads/[mq]*',
            ],
        )
    got = iter(got)
    eq(got.next(), dict(refname='refs/heads/master'))
    eq(got.next(), dict(refname='refs/heads/quux'))
    eq(got.next(), dict(refname='refs/heads/thud/xyzzy'))
    assert_raises(StopIteration, got.next)
