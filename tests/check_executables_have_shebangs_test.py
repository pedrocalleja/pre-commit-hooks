import os
import sys

import pytest

from pre_commit_hooks import check_executables_have_shebangs
from pre_commit_hooks.check_executables_have_shebangs import main
from pre_commit_hooks.util import cmd_output

skip_win32 = pytest.mark.skipif(
    sys.platform == 'win32',
    reason="non-git checks aren't relevant on windows",
)


@skip_win32  # pragma: win32 no cover
@pytest.mark.parametrize(
    'content', (
        b'#!/bin/bash\nhello world\n',
        b'#!/usr/bin/env python3.6',
        b'#!python',
        '#!☃'.encode(),
    ),
)
def test_has_shebang(content, tmpdir):
    path = tmpdir.join('path')
    path.write(content, 'wb')
    assert main((path.strpath,)) == 0


@skip_win32  # pragma: win32 no cover
@pytest.mark.parametrize(
    'content', (
        b'',
        b' #!python\n',
        b'\n#!python\n',
        b'python\n',
        '☃'.encode(),
    ),
)
def test_bad_shebang(content, tmpdir, capsys):
    path = tmpdir.join('path')
    path.write(content, 'wb')
    assert main((path.strpath,)) == 1
    _, stderr = capsys.readouterr()
    assert stderr.startswith(f'{path}: marked executable but')


def test_check_git_filemode_passing(tmpdir):
    with tmpdir.as_cwd():
        cmd_output('git', 'init', '.')

        f = tmpdir.join('f')
        f.write('#!/usr/bin/env bash')
        cmd_output('chmod', '+x', f)
        cmd_output('git', 'add', f)
        cmd_output('git', 'update-index', '--chmod=+x', f)

        g = tmpdir.join('g').ensure()
        cmd_output('git', 'add', g)

        # this is potentially a problem, but not something the script intends
        # to check for -- we're only making sure that things that are
        # executable have shebangs
        h = tmpdir.join('h')
        h.write('#!/usr/bin/env bash')
        cmd_output('git', 'add', h)

        files = (f, g, h)
        assert check_executables_have_shebangs._check_git_filemode(files) == 0


def test_check_git_filemode_failing(tmpdir):
    with tmpdir.as_cwd():
        cmd_output('git', 'init', '.')

        f = tmpdir.join('f').ensure()
        cmd_output('chmod', '+x', f)
        cmd_output('git', 'add', f)
        cmd_output('git', 'update-index', '--chmod=+x', f)

        assert check_executables_have_shebangs._check_git_filemode((f,)) == 1


@pytest.mark.parametrize(
    ('content', 'mode', 'expected'),
    (
        pytest.param(b'#!python', '+x', 0, id='shebang with executable'),
        pytest.param(b'#!python', '-x', 0, id='shebang without executable'),
        pytest.param(b'', '+x', 1, id='no shebang with executable'),
        pytest.param(b'', '-x', 0, id='no shebang without executable'),
    ),
)
def test_git_executable_shebang(temp_git_dir, content, mode, expected):
    with temp_git_dir.as_cwd():
        path = temp_git_dir.join('path')
        path.write(content, 'wb')
        cmd_output('git', 'add', path)
        cmd_output('chmod', mode, path)
        cmd_output('git', 'update-index', f'--chmod={mode}', path)

        # simulate how identify choses that something is executable
        filenames = [path for path in [str(path)] if os.access(path, os.X_OK)]

        assert main(filenames) == expected
