from __future__ import with_statement

from nose.tools import (
    eq_ as eq,
    )

from gitfs.test.util import (
    maketemp,
    )

import os

from gitfs import indexfs
from gitfs import repo
from gitfs import commands

def test_simple():
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

    r = repo.Repository(path=tmp)
    with r.transaction() as p:
        assert type(p) == indexfs.IndexFS
        eq(p.path, '')
        eq(list(p), [p.child('bar'), p.child('quux')])

        with p.child('bar').open('w') as f:
            f.write('THUD')

        # the committed tree has not changed yet, because transaction
        # is still open
        got = commands.ls_tree(
            repo=tmp,
            path='bar',
            )
        got = list(got)
        eq(len(got), 1)
        got = got[0]
        object = got['object']
        content = commands.cat_file(
            repo=tmp,
            object=object,
            )
        eq(content, 'BAR')

    # transaction committed, now the content has changed
    got = commands.ls_tree(
        repo=tmp,
        path='bar',
        )
    got = list(got)
    eq(len(got), 1)
    got = got[0]
    object = got['object']
    content = commands.cat_file(
        repo=tmp,
        object=object,
        )
    eq(content, 'THUD')
