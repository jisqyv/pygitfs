import nose

from gitfs.test.util import (
    maketemp,
    )

from filesystem.test import test_roundtrip

import os

from gitfs import indexfs
from gitfs import commands

class Index_Tests(test_roundtrip.OperationsMixin):
    def setUp(self):
        tmp = maketemp()
        repo = os.path.join(tmp, 'repo')
        index = os.path.join(tmp, 'index')
        commands.init_bare(repo)
        self.path = indexfs.IndexFS(
            repo=repo,
            index=index,
            )

    def test_rmdir_bad_notdir(self):
        raise nose.SkipTest('TODO')

    def test_rmdir_bad_notfound(self):
        raise nose.SkipTest('TODO')

    def test_unlink_notfound(self):
        raise nose.SkipTest('TODO')

    def test_remove_notfound(self):
        raise nose.SkipTest('TODO')
