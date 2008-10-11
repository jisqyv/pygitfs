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

def test_commit_race():
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
                        content='orig\n',
                        mode='100755',
                        ),
                    ],
                ),
            ],
        )

    r = repo.Repository(path=tmp)
    racecount = 0
    tries = 1
    MAX_RETRIES = 3
    success = False
    while tries <= MAX_RETRIES:
        try:
            with r.transaction() as p:

                if racecount < 2:
                    racecount += 1
                    r2 = repo.Repository(path=tmp)
                    with r2.transaction() as p2:
                        with p2.child('bar').open('a') as f:
                            f.write('racer %d\n' % racecount)

                with p.child('bar').open('a') as f:
                    f.write('loser %d\n' % tries)
        except repo.TransactionRaceLostError:
            tries += 1
        else:
            success = True
            break

    assert success

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
    eq(content, 'orig\nracer 1\nracer 2\nloser 3\n')


def test_no_initial_commit():
    tmp = maketemp()
    commands.init_bare(tmp)

    r = repo.Repository(path=tmp)
    with r.transaction() as p:
        eq(list(p), [])

        with p.child('bar').open('w') as f:
            f.write('THUD')

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
