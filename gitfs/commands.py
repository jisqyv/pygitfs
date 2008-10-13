import errno
import os
import shutil
import subprocess

from cStringIO import StringIO

def init_bare(repo):
    returncode = subprocess.call(
        args=[
            'git',
            '--bare',
            '--git-dir=%s' % repo,
            'init',
            '--quiet',
            ],
        close_fds=True,
        )
    if returncode != 0:
        raise RuntimeError('git init failed')

def init_bare_atomic(repo, tmp):
    """
    Initialize a bare git repository atomically.

    This means the repository is only moved to its final name once the
    initialization is complete. This means other users can
    concurrently use any repository they happen to see at any time
    with a final name; they will not accidentally encounter a
    partially initialized repository, not even if the process
    initializing a repository crashes. Then again, crashes can leave
    temporary directories lying around.

    Caller must guarantee C{tmp} uniqueness. For a single-threaded
    process using a non-networked filesystem, something like this is
    usually sufficient::

	base = 'foo'
	repo = '%s.git' % base
        tmp = '%s.%d.tmp' % (base, os.getpid())
    """
    init_bare(tmp)
    try:
        os.rename(tmp, repo)
    except OSError, e:
        if e.errno in [
            errno.ENOTEMPTY,
            errno.EEXIST,
            ]:
            # lost the race to create it, clean up; where as git init
            # in itself is idempotent, *this* is the reason tmp must
            # be unique
            shutil.rmtree(tmp)
        else:
            raise

def fast_import(
    repo,
    commits,
    ref=None,
    ):
    """
    Create an initial commit.
    """
    if ref is None:
        ref = 'refs/heads/master'
    child = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'fast-import',
            '--quiet',
            ],
        stdin=subprocess.PIPE,
        close_fds=True,
        )

    for commit in commits:
        files = list(commit['files'])
        for index, filedata in enumerate(files):
            child.stdin.write("""\
blob
mark :%(mark)d
data %(len)d
%(content)s
""" % dict(
                mark=index+1,
                len=len(filedata['content']),
                content=filedata['content'],
                ))
        child.stdin.write("""\
commit %(ref)s
author %(author)s %(author_time)s
committer %(committer)s %(commit_time)s
data %(commit_msg_len)d
%(commit_msg)s
""" % dict(
                ref=ref,
                author=commit.get('author', commit['committer']),
                author_time=commit.get('author_time', commit['commit_time']),
                committer=commit['committer'],
                commit_time=commit['commit_time'],
                commit_msg_len=len(commit['message']),
                commit_msg=commit['message'],
                ))
        parent = commit.get('parent')
        if parent is not None:
            assert not parent.startswith(':')
            child.stdin.write("""\
from %(parent)s
""" % dict(
                    parent=parent,
                    ))
        for index, filedata in enumerate(files):
            child.stdin.write(
                'M %(mode)s :%(index)d %(path)s\n' % dict(
                    mode=filedata.get('mode', '100644'),
                    index=index+1,
                    path=filedata['path'],
                    ),
                )

    child.stdin.close()
    returncode = child.wait()
    if returncode != 0:
        raise RuntimeError(
            'git fast-import failed', 'exit status %d' % returncode)

def rev_parse(repo, rev):
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'rev-parse',
            '--default',
            rev,
            ],
        close_fds=True,
        stdout=subprocess.PIPE,
        )
    sha = process.stdout.read()
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git rev-parse failed')
    if not sha:
        return None
    sha = sha.rstrip('\n')
    return sha

def get_symbolic_ref(repo, ref):
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'symbolic-ref',
            ref,
            ],
        close_fds=True,
        stdout=subprocess.PIPE,
        )
    value = process.stdout.read()
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git symbolic-ref failed')
    if not value:
        return None
    value = value.rstrip('\n')
    return value

def ls_tree(
    repo,
    path=None,
    treeish=None,
    children=None,
    ):
    if path is None:
        path = ''
    if treeish is None:
        treeish = 'HEAD'
    if children is None:
        children = False
    assert not path.startswith('/')
    assert not path.endswith('/')
    if children:
        if path:
            path = path+'/'
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'ls-tree',
            '-z',
            '--full-name',
            treeish,
            '--',
            path,
            ],
        close_fds=True,
        stdout=subprocess.PIPE,
        )
    buf = ''
    while True:
        new = process.stdout.read(8192)
        buf += new
        while True:
            try:
                (entry, buf) = buf.split('\0', 1)
            except ValueError:
                break
            meta, filename = entry.split('\t', 1)
            mode, type_, object = meta.split(' ', 2)
            yield dict(
                mode=mode,
                type=type_,
                object=object,
                path=filename,
                )
        if not new:
            break
    if buf:
        raise RuntimeError(
            'git ls-tree output did not end in NUL')
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git ls-tree failed')

def cat_file(repo, object, type_=None):
    if type_ is None:
        type_ = 'blob'
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'cat-file',
            type_,
            object,
            ],
        close_fds=True,
        stdout=subprocess.PIPE,
        )
    # TODO don't read in to RAM
    data = process.stdout.read()
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git cat-file failed')
    return data

def batch_cat_file(repo):
    def do_batch_cat_file(repo):
        process = subprocess.Popen(
            args=[
                'git',
                '--git-dir=%s' % repo,
                'cat-file',
                '--batch',
                ],
            close_fds=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            )
        answer = None
        try:
            while True:
                want_object = (yield answer)
                process.stdin.write('%s\n' % want_object)
                process.stdin.flush()
                response = process.stdout.readline()
                if (not response
                    or response[-1] != '\n'):
                    # eof with possible partial line
                    # TODO get exit status & process
                    raise RuntimeError('git cat-file exited early')
                response = response[:-1]
                got_object, rest = response.split(' ', 1)
                if rest == 'missing':
                    answer = dict(
                        object=got_object,
                        type=rest,
                        )
                else:
                    type_, size = rest.split(' ', 1)
                    size = int(size)
                    data = process.stdout.read(size)
                    if len(data) != size:
                        raise RuntimeError('git cat-file exited early')
                    lf = process.stdout.read(1)
                    if lf != '\n':
                        raise RuntimeError('git cat-file missing newline')
                    answer = dict(
                        object=got_object,
                        type=type_,
                        size=size,
                        contents=StringIO(data),
                        )
        except GeneratorExit:
            process.stdin.close()
            data = process.stdout.read()
            if data:
                raise RuntimeError('git cat-file gave weird trailer data')
            returncode = process.wait()
            if returncode != 0:
                raise RuntimeError('git cat-file failed')
    g = do_batch_cat_file(repo)
    g.next()
    return g

def get_object_size(repo, object):
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'cat-file',
            '-s',
            object,
            ],
        close_fds=True,
        stdout=subprocess.PIPE,
        )
    data = process.stdout.read()
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git cat-file failed')
    data = int(data)
    return data

def write_object(repo, content):
    # TODO don't require content to be in RAM
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'hash-object',
            '-w',
            '--stdin',
            ],
        close_fds=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        )
    process.stdin.write(content)
    process.stdin.close()
    sha = process.stdout.read().rstrip('\n')
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git hash-object failed')
    if not sha:
        raise RuntimeError('git hash-object did not return a hash')
    return sha

def read_tree(repo, treeish, index):
    env = {}
    env.update(os.environ)
    env['GIT_INDEX_FILE'] = index
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'read-tree',
            '%s' % treeish,
            ],
        close_fds=True,
        env=env,
        )
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git read-tree failed')

def update_index(repo, index, files):
    env = {}
    env.update(os.environ)
    env['GIT_INDEX_FILE'] = index
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'update-index',
            '-z',
            '--index-info',
            ],
        close_fds=True,
        env=env,
        stdin=subprocess.PIPE,
        )
    for filedata in files:
        process.stdin.write(
            "%(mode)s %(type)s %(object)s %(stage)s\t%(path)s\0"
            % dict(
                mode=filedata.get('mode', '100644'),
                type=filedata.get('type', 'blob'),
                object=filedata['object'],
                stage=filedata.get('stage', '0'),
                path=filedata['path'],
                ),
            )
    process.stdin.close()
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git read-tree failed')

def ls_files(
    repo,
    index,
    path=None,
    children=None,
    ):
    if path is None:
        path = ''
    if children is None:
        children = True
    assert not path.startswith('/')
    assert not path.endswith('/')
    if children:
        if path:
            path = path+'/'
    env = {}
    env.update(os.environ)
    env['GIT_INDEX_FILE'] = index
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'ls-files',
            '--stage',
            '--full-name',
            '-z',
            '--',
            path,
            ],
        close_fds=True,
        env=env,
        stdout=subprocess.PIPE,
        )
    buf = ''
    while True:
        new = process.stdout.read(8192)
        buf += new
        while True:
            try:
                (entry, buf) = buf.split('\0', 1)
            except ValueError:
                break
            meta, filename = entry.split('\t', 1)
            mode, object, stage = meta.split(' ', 2)
            assert stage == '0', 'unprepared to handle merges'
            yield dict(
                mode=mode,
                object=object,
                path=filename,
                )
        if not new:
            break
    if buf:
        raise RuntimeError(
            'git ls-files output did not end in NUL')
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git ls-files failed')

def write_tree(repo, index):
    env = {}
    env.update(os.environ)
    env['GIT_INDEX_FILE'] = index
    process = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % repo,
            'write-tree',
            ],
        close_fds=True,
        env=env,
        stdout=subprocess.PIPE,
        )
    sha = process.stdout.read().rstrip('\n')
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git write-tree failed')
    if not sha:
        raise RuntimeError('git write-tree did not return a hash')
    return sha

def commit_tree(
    repo,
    tree,
    parents=None,
    message=None,
    author_name=None,
    author_email=None,
    author_date=None,
    committer_name=None,
    committer_email=None,
    committer_date=None,
    ):
    if parents is None:
        parents = []
    if message is None:
        message = ''
    env = {}
    env.update(os.environ)
    if author_name is not None:
	env['GIT_AUTHOR_NAME'] = author_name
    if author_email is not None:
	env['GIT_AUTHOR_EMAIL'] = author_email
    if author_date is not None:
	env['GIT_AUTHOR_DATE'] = author_date
    if committer_name is not None:
	env['GIT_COMMITTER_NAME'] = committer_name
    if committer_email is not None:
	env['GIT_COMMITTER_EMAIL'] = committer_email
    if committer_date is not None:
	env['GIT_COMMITTER_DATE'] = committer_date

    args = [
        'git',
        '--git-dir=%s' % repo,
        'commit-tree',
        tree,
        ]
    for p in parents:
        args.extend(['-p', p])
    process = subprocess.Popen(
        args=args,
        close_fds=True,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        )
    process.stdin.write(message)
    process.stdin.close()
    sha = process.stdout.read().rstrip('\n')
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git commit-tree failed')
    if not sha:
        raise RuntimeError('git commit-tree did not return a hash')
    return sha

def update_ref(
    repo,
    ref,
    newvalue,
    oldvalue=None,
    reason=None,
    ):
    args = [
            'git',
            '--git-dir=%s' % repo,
            'update-ref',
            ref,
            newvalue,
            ]
    if oldvalue is not None:
        args.append(oldvalue)
    process = subprocess.Popen(
        args=args,
        close_fds=True,
        )
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError('git update-ref failed')
