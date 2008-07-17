from gitfs.test.util import (
    maketemp,
    )

from fs.test import test_roundtrip

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