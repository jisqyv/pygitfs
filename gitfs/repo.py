import errno
import os

from gitfs import commands
from gitfs import indexfs

def maybe_mkdir(*a, **kw):
    try:
        os.mkdir(*a, **kw)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

class TransactionRaceLostError(Exception):
    """Transaction lost the race to update the ref."""

    # caller should retry a fixed number of times, abort if tries
    # exhausted

    def __str__(self):
        return self.__doc__


class Transaction(object):
    def __init__(self, **kw):
        repo = kw.pop('repo', None)
        if repo is None:
            repo = '.'
        self.repo = repo
        ref = kw.pop('ref', None)
        if ref is None:
            ref = 'HEAD'
        self.ref = ref
        index = kw.pop('index', None)
        if index is None:
            gitfs_dir = os.path.join(self.repo.path, 'pygitfs')
            maybe_mkdir(gitfs_dir)
            ident = id(self)
            assert ident >= 0
            index = os.path.join(
                gitfs_dir,
                'index.%d.%d' % (os.getpid(), ident),
                )
        self.index = index
        super(Transaction, self).__init__(**kw)

    def __repr__(self):
        return '%s(repo=%r, ref=%r)' % (
            self.__class__.__name__,
            self.repo,
            self.ref,
            )

    def __enter__(self):
        head = commands.rev_parse(
            repo=self.repo.path,
            rev=self.ref,
            )
        self.original = head
        if head is not None:
            commands.read_tree(
                repo=self.repo.path,
                treeish=self.original,
                index=self.index,
                )
        return indexfs.IndexFS(
            repo=self.repo.path,
            index=self.index,
            )

    def __exit__(self, type_, value, traceback):
        if (type_ is None
            and value is None
            and traceback is None):
            # no exception -> commit transaction
            tree = commands.write_tree(
                repo=self.repo.path,
                index=self.index,
                )
            os.unlink(self.index)
            parents = []
            if self.original is not None:
                parents.append(self.original)
            commit = commands.commit_tree(
                repo=self.repo.path,
                tree=tree,
                parents=parents,
                message='pygitfs',
                committer_name='pygitfs',
                committer_email='pygitfs@invalid',
                )
            try:
                commands.update_ref(
                    repo=self.repo.path,
                    ref=self.ref,
                    newvalue=commit,
                    oldvalue=self.original,
                    reason='pygitfs transaction commit',
                    )
            except RuntimeError:
                # TODO this could be caused by pretty much anything
                # from OOM to invalid input, but as there's no way to
                # tell (with current git), we'll just assume it's
                # always caused by race condition..
                raise TransactionRaceLostError()

class Repository(object):
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return '%s(path=%r)' % (
            self.__class__.__name__,
            self.path,
            )

    def transaction(self, ref=None, index=None):
        return Transaction(repo=self, ref=ref, index=index)
