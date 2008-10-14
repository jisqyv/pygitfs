from __future__ import with_statement

import errno
import hashlib
import os
from cStringIO import StringIO

from fs import (
    InsecurePathError,
    WalkMixin,
    CrossDeviceRenameError,
    )

from gitfs import commands

class ContextManagedFile(object):
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return StringIO(self.data)

    def __exit__(self, type_, value, traceback):
        pass

class ReadOnlyGitFS(WalkMixin):
    """
    Readonly filesystem reading from a git repository.
    """

    def __init__(self, **kw):
        self.repo = kw.pop('repo')
        rev = kw.pop('rev', None)
        if rev is None:
            rev = 'HEAD'
        self.rev = rev
        path = kw.pop('path', None)
        if path is None:
            path = ''
        self.path = path
        super(ReadOnlyGitFS, self).__init__(**kw)

    def __repr__(self):
        return '%s(path=%r, repo=%r, rev=%r)' % (
            self.__class__.__name__,
            self.path,
            self.repo,
            self.rev,
            )

    def name(self):
        """Return last segment of path."""
        return os.path.basename(self.path)

    def join(self, relpath):
        if relpath.startswith(u'/'):
            raise InsecurePathError('path name to join must be relative')
        return self.__class__(
            repo=self.repo,
            rev=self.rev,
            path=os.path.join(self.path, relpath),
            )

    def child(self, *segments):
        p = self
        for segment in segments:
            if u'/' in segment:
                raise InsecurePathError(
                    'child name contains directory separator')
            # this may be too naive
            if segment == u'..':
                raise InsecurePathError(
                    'child trying to climb out of directory')
            p = p.join(segment)
        return p

    def __enter__(self):
        """
        Entering a context takes a snapshot.
        """
        rev = commands.rev_parse(
            repo=self.repo,
            rev=self.rev,
            )
        if rev is None:
            # no initial commit but you ask for a snapshot?
            # i'm going to give you the empty tree..
            rev = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
        return self.__class__(
            repo=self.repo,
            rev=rev,
            path=self.path,
            )

    def __exit__(self, type_, value, traceback):
        pass

    def open(self, mode='r'):
        if mode not in ['r', 'rb']:
            raise IOError(
                errno.EROFS,
                os.strerror(errno.EROFS),
                )
        # TODO don't read big files fully into RAM
        data = commands.cat_file(
            repo=self.repo,
            type_='blob',
            object='%s:%s' % (self.rev, self.path),
            )
        return ContextManagedFile(data)

    def __iter__(self):
        for data in commands.ls_tree(
            repo=self.repo,
            path=self.path,
            treeish=self.rev,
            children=True,
            ):
            if self.path == '':
                prefix = ''
            else:
                prefix = self.path + '/'
                assert data['path'][:len(prefix)] == prefix
            relative = data['path'][len(prefix):]
            if relative == '.gitfs-placeholder':
                # hide the magic
                continue
            yield self.child(relative)


    def parent(self):
        head, tail = os.path.split(self.path)
        return self.__class__(
            repo=self.repo,
            rev=self.rev,
            path=head,
            )

    def __eq__(self, other):
        if not isinstance(other, ReadOnlyGitFS):
            return NotImplemented
        if (self.repo != other.repo
            or self.rev != other.rev):
            return False
        if self.path != other.path:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, ReadOnlyGitFS):
            return NotImplemented
        if (self.repo != other.repo
            or self.rev != other.rev):
            return NotImplemented
        return self.path < other.path

    def __le__(self, other):
        if not isinstance(other, ReadOnlyGitFS):
            return NotImplemented
        return self < other or self == other

    def __gt__(self, other):
        if not isinstance(other, ReadOnlyGitFS):
            return NotImplemented
        if (self.repo != other.repo
            or self.rev != other.rev):
            return NotImplemented
        return self.path > other.path

    def __ge__(self, other):
        if not isinstance(other, ReadOnlyGitFS):
            return NotImplemented
        return self > other or self == other

    def mkdir(self, may_exist=False, create_parents=False):
        raise IOError(
            errno.EROFS,
            os.strerror(errno.EROFS),
            )

    def remove(self):
        raise IOError(
            errno.EROFS,
            os.strerror(errno.EROFS),
            )

    def unlink(self):
        self.remove()

    def isdir(self):
        for data in commands.ls_tree(
            repo=self.repo,
            path=self.path,
            treeish=self.rev,
            children=True,
            ):
            return True

        # i have no children, therefore i am not a directory
        return False

    def exists(self):
        if self.path == '':
            # root directory always exists
            return True
        for data in commands.ls_tree(
            repo=self.repo,
            path=self.path,
            treeish=self.rev,
            children=False,
            ):
            return True
        return False

    def rmdir(self):
        raise IOError(
            errno.EROFS,
            os.strerror(errno.EROFS),
            )

    def islink(self):
        if self.path == '':
            # root directory is never a link
            return False
        for data in commands.ls_tree(
            repo=self.repo,
            path=self.path,
            treeish=self.rev,
            children=False,
            ):
            return data['mode'] == '120000'

        # didn't match anything -> don't even exist
        return False

    def rename(self, new_path):
        raise IOError(
            errno.EROFS,
            os.strerror(errno.EROFS),
            )

    def size(self):
        if self.path == '':
            object = commands.rev_parse(
                repo=self.repo,
                rev='%s^{tree}' % self.rev,
                )
        for data in commands.ls_tree(
            repo=self.repo,
            path=self.path,
            treeish=self.rev,
            children=False,
            ):
            object = data['object']
            break

        return commands.get_object_size(
            repo=self.repo,
            object=object,
            )
