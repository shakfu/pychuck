"""
Tests for CLI argument parsing and commands.
"""
import pytest
import sys


def test_cli_parser_creation():
    """Test CLI parser can be created."""
    from pychuck.cli.main import create_parser

    parser = create_parser()
    assert parser is not None
    assert parser.prog == 'pychuck'


def test_edit_command_parsing():
    """Test edit command argument parsing."""
    from pychuck.cli.main import create_parser

    parser = create_parser()

    # Basic edit
    args = parser.parse_args(['edit'])
    assert args.command == 'edit'
    assert args.files == []
    assert args.project is None
    assert args.start_audio is False

    # Edit with project
    args = parser.parse_args(['edit', '--project', 'myproject'])
    assert args.command == 'edit'
    assert args.project == 'myproject'

    # Edit with files
    args = parser.parse_args(['edit', 'file1.ck', 'file2.ck'])
    assert args.command == 'edit'
    assert args.files == ['file1.ck', 'file2.ck']

    # Edit with start-audio
    args = parser.parse_args(['edit', '--start-audio'])
    assert args.start_audio is True

    # Edit with all options
    args = parser.parse_args([
        'edit', 'file1.ck', 'file2.ck',
        '--project', 'test',
        '--start-audio'
    ])
    assert args.command == 'edit'
    assert args.files == ['file1.ck', 'file2.ck']
    assert args.project == 'test'
    assert args.start_audio is True


def test_repl_command_parsing():
    """Test repl command argument parsing."""
    from pychuck.cli.main import create_parser

    parser = create_parser()

    # Basic repl
    args = parser.parse_args(['repl'])
    assert args.command == 'repl'
    assert args.files == []
    assert args.start_audio is False
    assert args.no_smart_enter is False
    assert args.no_sidebar is False

    # REPL with files
    args = parser.parse_args(['repl', 'file1.ck'])
    assert args.command == 'repl'
    assert args.files == ['file1.ck']

    # REPL with options
    args = parser.parse_args([
        'repl',
        '--start-audio',
        '--no-smart-enter',
        '--no-sidebar',
        '--project', 'myproject'
    ])
    assert args.start_audio is True
    assert args.no_smart_enter is True
    assert args.no_sidebar is True
    assert args.project == 'myproject'


def test_exec_command_parsing():
    """Test exec command argument parsing."""
    from pychuck.cli.main import create_parser

    parser = create_parser()

    # Basic exec
    args = parser.parse_args(['exec', 'file.ck'])
    assert args.command == 'exec'
    assert args.files == ['file.ck']
    assert args.srate == 44100
    assert args.channels == 2
    assert args.silent is False

    # Exec with multiple files
    args = parser.parse_args(['exec', 'file1.ck', 'file2.ck'])
    assert args.files == ['file1.ck', 'file2.ck']

    # Exec with options
    args = parser.parse_args([
        'exec', 'file.ck',
        '--srate', '48000',
        '--channels', '1',
        '--silent',
        '--duration', '10'
    ])
    assert args.srate == 48000
    assert args.channels == 1
    assert args.silent is True
    assert args.duration == 10


def test_version_command_parsing():
    """Test version command parsing."""
    from pychuck.cli.main import create_parser

    parser = create_parser()

    args = parser.parse_args(['version'])
    assert args.command == 'version'


def test_info_command_parsing():
    """Test info command parsing."""
    from pychuck.cli.main import create_parser

    parser = create_parser()

    args = parser.parse_args(['info'])
    assert args.command == 'info'


def test_tui_command_backward_compatibility():
    """Test tui command is still supported for backward compatibility."""
    from pychuck.cli.main import create_parser

    parser = create_parser()

    args = parser.parse_args(['tui'])
    assert args.command == 'tui'
    assert args.start_audio is False

    args = parser.parse_args(['tui', '--start-audio', '--no-smart-enter'])
    assert args.start_audio is True
    assert args.no_smart_enter is True


def test_command_handlers_exist():
    """Test that all command handlers are defined."""
    from pychuck.cli import main

    assert hasattr(main, 'cmd_edit')
    assert hasattr(main, 'cmd_repl')
    assert hasattr(main, 'cmd_exec')
    assert hasattr(main, 'cmd_version')
    assert hasattr(main, 'cmd_info')


def test_version_command_output(capsys):
    """Test version command produces output."""
    from pychuck.cli.main import cmd_version
    from argparse import Namespace

    args = Namespace()
    cmd_version(args)

    captured = capsys.readouterr()
    assert 'pychuck version:' in captured.out
    assert 'ChucK version:' in captured.out


def test_info_command_output(capsys):
    """Test info command produces output."""
    from pychuck.cli.main import cmd_info
    from argparse import Namespace

    args = Namespace()
    cmd_info(args)

    captured = capsys.readouterr()
    assert 'pychuck:' in captured.out
    assert 'ChucK:' in captured.out
    assert 'ChucK int size:' in captured.out
    assert 'Active VMs:' in captured.out
