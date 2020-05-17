import os

import pytest

from pre_commit_hooks.check_executables_have_shebangs import main
from pre_commit_hooks.util import cmd_output

skip_nt = pytest.mark.skipif(
    os.name == 'nt', reason="non-git checks aren't relevant on windows",
)
skip_posix = pytest.mark.skipif(
    os.name != 'nt', reason='git checks only run on windows',
)


@skip_nt  # pragma: win32 no cover
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


@skip_nt  # pragma: win32 no cover
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


@skip_posix  # pragma: no cover (windows)
@pytest.mark.parametrize(
    ('content', 'mode', 'expected'),
    (
        pytest.param(b'#!python', '+x', 0, id='shebang with executable'),
        pytest.param(b'#!python', '-x', 1, id='shebang without executable'),
        pytest.param(b'', '+x', 1, id='no shebang with executable'),
        pytest.param(b'', '-x', 0, id='no shebang without executable'),
    ),
)
def test_git_executable_shebang(temp_git_dir, content, mode, expected):
    with temp_git_dir.as_cwd():
        path = temp_git_dir.join('path')
        path.write(content, 'wb')
        cmd_output('git', 'add', path.strpath)
        cmd_output('git', 'update-index', f'--chmod={mode}', path.strpath)

        assert main((path.strpath,)) == expected
