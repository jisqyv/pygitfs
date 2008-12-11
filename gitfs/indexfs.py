from __future__ import with_statement

import errno
import hashlib
import os
import posix
import stat

from fs import (
    InsecurePathError,
    WalkMixin,
    CrossDeviceRenameError,
    )

from gitfs import commands

class NotifyOnCloseFile(file):
    def __init__(self, *a, **kw):
        self.__callback = kw.pop('callback')
        super(NotifyOnCloseFile, self).__init__(*a, **kw)

    def close(self):
        self.__callback(self)
        super(NotifyOnCloseFile, self).close()

    def __exit__(self, *a, **kw):
        self.__callback(self)
        return super(NotifyOnCloseFile, self).__exit__(*a, **kw)

class IndexFS(WalkMixin):
    """
    Filesystem using a git index file for tracking.

    File contents are stored in a git repository.  As files are not
    (necessarily) reachable from any refs, a ``git gc`` will prune
    them after two weeks. Do not use this filesystem for periods
    longer than this; it is meant for preparing a tree to be
    committed, and that should not take that long.

    Note that files starting with the index filename and a dot are
    used as temporary files. These may be left around due to a crash,
    but can be purged after two weeks, because of the above pruning
    mechanism.

    Do not start two seperate IndexFS instances with the same index
    file, that will result in file corruption and exceptions.
    """

    def __init__(self, repo, index, path=None, _open_files=None):
        self.repo = repo
        self.index = index
        if path is None:
            path = ''
        self.path = path
        if _open_files is None:
            _open_files = {}
        self.open_files = _open_files

    def __repr__(self):
        return '%s(path=%r, index=%r, repo=%r)' % (
            self.__class__.__name__,
            self.path,
            self.index,
            self.repo,
            )

    def name(self):
        """Return last segment of path."""
        return os.path.basename(self.path)

    def join(self, relpath):
        if relpath.startswith(u'/'):
            raise InsecurePathError('path name to join must be relative')
        return self.__class__(
            repo=self.repo,
            index=self.index,
            path=os.path.join(self.path, relpath),
            _open_files=self.open_files,
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

    def git_get_sha1(self):
        """
        Get the git sha1 for the object.

        Does not work on ope
        """
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            children=False,
            ):
            if data['path'] != self.path:
                continue
            return data['object']

        # not found
        raise OSError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            )

    def git_mass_set_sha1(self, edits):
        """
        Set the git sha1 for many objects.

        C{edits} is an iterable of 2-tuples, with an C{IndexFS}
        instance and a sha1.

        See also C{git_set_sha1}.
        """
        def g(edits):
            for edit in edits:
                (p, object) = edit
                if not isinstance(p, IndexFS):
                    raise RuntimeError(
                        'Path must be an IndexFS path.')
                if (p.repo != self.repo
                    or p.index != self.index):
                    raise RuntimeError(
                        'Path is from a different IndexFS.')
                yield dict(
                    # TODO mode
                    path=p.path,
                    object=object,
                    )
        commands.update_index(
            repo=self.repo,
            index=self.index,
            files=g(edits),
            )

    def git_set_sha1(self, object):
        """
        Set the git sha1 for this object.

        Effectively, replace the content here with the content of
        another object. The new content has to be in the repository
        already; this is not verified in any way.
        """
        self.git_mass_set_sha1([
                (self, object),
                ])

    def open(self, mode='r'):
        path_sha = hashlib.sha1(self.path).hexdigest()
        work = os.path.extsep.join([
                self.index,
                path_sha,
                'work',
                ])

        current_users = self.open_files.get(self.path)
        if current_users is None:

            try:
                object = self.git_get_sha1()
            except OSError, e:
                if e.errno == errno.ENOENT:
                    content = ''
                else:
                    raise
            else:
                # it exists
                content = commands.cat_file(
                    repo=self.repo,
                    object=object,
                    )
            tmp = os.path.extsep.join([
                    self.index,
                    path_sha,
                    'tmp',
                    ])
            with file(tmp, 'wb') as f:
                f.write(content)
            os.rename(tmp, work)
            current_users = self.open_files[self.path] = dict(
                users=set(),
                writable=False,
                )

        f = NotifyOnCloseFile(work, mode, callback=self._close_file)
        current_users['users'].add(f)
        if mode not in ['r', 'rb']:
            current_users['writable'] = True
        return f

    def _close_file(self, f):
        if f.mode not in ['r', 'rb']:
            # flush it so we can open it by name and actually see the
            # data
            f.flush()
        current_users = self.open_files[self.path]
        current_users['users'].remove(f)
        if (current_users['writable']
            and not current_users['users']):
            # last user closed a file that has been writable at some
            # point, write it to git object storage and update index
            with file(f.name, 'rb') as slurp:
                content = slurp.read()
            os.unlink(f.name)
            object = commands.write_object(
                repo=self.repo,
                content=content,
                )
            self.git_set_sha1(object)
            del self.open_files[self.path]

    def __iter__(self):
        last_subdir = None
        saw_children = False
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            children=True,
            ):
            saw_children = True

            # TODO OMG THIS IS STUPID, always retrieves full subtree
            # (so for root, always dumps whole index)
            if self.path == '':
                prefix = ''
            else:
                prefix = self.path + '/'
                assert data['path'][:len(prefix)] == prefix
            relative = data['path'][len(prefix):]

            if relative == '.gitfs-placeholder':
                # hide the magic
                continue

            if '/' in relative:
                # it's a subdir, really; combine multiple files into
                # one dir entry
                head = relative.split(os.path.sep, 1)[0]
                if head == last_subdir:
                    # already handled this one
                    continue
                else:
                    last_subdir = head
                    yield self.child(head)
            else:
                yield self.child(relative)

        if not saw_children:
            # it's either not a dir or it doesn't exist..
            # TODO make tests differentiate between those
            if self.path == '':
                # except root always exists
                return
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT))

    def parent(self):
        head, tail = os.path.split(self.path)
        return self.__class__(
            repo=self.repo,
            index=self.index,
            path=head,
            _open_files=self.open_files,
            )

    def __eq__(self, other):
        if not isinstance(other, IndexFS):
            return NotImplemented
        if (self.repo != other.repo
            or self.index != other.index):
            return False
        if self.path != other.path:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, IndexFS):
            return NotImplemented
        if (self.repo != other.repo
            or self.index != other.index):
            return NotImplemented
        return self.path < other.path

    def __le__(self, other):
        if not isinstance(other, IndexFS):
            return NotImplemented
        return self < other or self == other

    def __gt__(self, other):
        if not isinstance(other, IndexFS):
            return NotImplemented
        if (self.repo != other.repo
            or self.index != other.index):
            return NotImplemented
        return self.path > other.path

    def __ge__(self, other):
        if not isinstance(other, IndexFS):
            return NotImplemented
        return self > other or self == other

    def mkdir(self, may_exist=False, create_parents=False):
        if not may_exist:
            if self.exists():
                raise OSError(errno.EEXIST, os.strerror(errno.EEXIST))

        # path has no children, therefore it is an empty directory
        # and do not exist in the git world; put in a placeholder
        # file
        if not create_parents:
            # make sure parents exist
            if self.parent() != self:
                if not self.parent().exists():
                    raise OSError(
                        errno.ENOENT,
                        os.strerror(errno.ENOENT),
                        )

        empty = commands.write_object(
            repo=self.repo,
            content='',
            )
        commands.update_index(
            repo=self.repo,
            index=self.index,
            files=[
                dict(
                    mode='100644',
                    object=empty,
                    path=self.child('.gitfs-placeholder').path,
                    ),
                ],
            )

    def remove(self):
        commands.update_index(
            repo=self.repo,
            index=self.index,
            files=[
                dict(
                    mode='0',
                    object=40*'0',
                    path=self.path,
                    ),
                ],
            )

    def unlink(self):
        self.remove()

    def isdir(self):
        if self.path == '':
            return True
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            ):
            return True

        # i have no children, therefore i am not a directory
        return False

    def isfile(self):
        if self.path == '':
            # root directory is never a file
            return False
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            children=False,
            ):
            if data['path'] == self.path:
                return data['mode'] in ['100644', '100755']
            else:
                # if current path has children, it can't be a file
                assert data['path'].startswith(self.path + '/')
                return False

        # didn't match anything -> don't even exist
        return False

    def exists(self):
        if self.path == '':
            # root directory always exists
            return True
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            children=False,
            ):
            # doesn't matter if it matches the file itself, or files
            # in a subdirectory; anyway, current path exists
            return True
        return False

    def rmdir(self):
        self.child('.gitfs-placeholder').remove()

    def islink(self):
        if self.path == '':
            # root directory is never a link
            return False
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            children=False,
            ):
            if data['path'] == self.path:
                return data['mode'] == '120000'
            else:
                # if current path has children, it can't be a symlink
                assert data['path'].startswith(self.path + '/')
                return False

        # didn't match anything -> don't even exist
        return False

    def stat(self):
        if self.path == '':
            return posix.stat_result(
                [stat.S_IFDIR + 0777, 0,0,0,0,0,0,0,0,0])
        for data in commands.ls_files(
            repo=self.repo,
            index=self.index,
            path=self.path,
            children=False,
            ):
            if data['path'] == self.path:
                mode = int(data['mode'], 8)
                size = commands.get_object_size(
                    repo=self.repo,
                    object=data['object'],
                    )
                return posix.stat_result([mode, 0,0,0,0,0,size,0,0,0])
            else:
                # if current path has children, it must be a dir
                assert data['path'].startswith(self.path + '/')
                return posix.stat_result(
                    [stat.S_IFDIR + 0777, 0,0,0,0,0,0,0,0,0])

        # not found
        raise OSError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            )

    def rename(self, new_path):
        if not isinstance(new_path, IndexFS):
            raise CrossDeviceRenameError()

        def g():
            for data in commands.ls_files(
                repo=self.repo,
                index=self.index,
                path=self.path,
                children=False,
                ):
                if data['path'] == self.path:
                    # delete the old one
                    delete = {}
                    delete.update(data)
                    delete['mode'] = '0'
                    yield delete

                    # add the new one
                    data['path'] = new_path.path
                    yield data
                else:
                    prefix = self.path + '/'
                    assert data['path'][:len(prefix)] == prefix

                    # delete the old one
                    delete = {}
                    delete.update(data)
                    delete['mode'] = '0'
                    yield delete

                    # add the new one
                    data['path'] = new_path.path + '/' + data['path'][len(prefix):]
                    yield data

        commands.update_index(
            repo=self.repo,
            index=self.index,
            files=g(),
            )

        self.path = new_path.path

    def size(self):
        object = self.git_get_sha1()
        # it exists
        return commands.get_object_size(
            repo=self.repo,
            object=object,
            )
