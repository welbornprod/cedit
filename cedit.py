#!/usr/bin/env python3
"""
    cedit.py
    Opens proper editor based on file extension..
    Checks file permissions, asks for root access if needed..

Created on Jan 19, 2013

@author: cj
"""

from __future__ import print_function
import os
import stat
import subprocess
import stat
import sys
from collections import namedtuple
from pathlib import Path
from typing import List, Set, Tuple

from docopt import docopt
from easysettings import EasySettings
if sys.version_info.major < 3:
    print('CEdit is designed to run on Python 3.5+ only.', file=sys.stderr)
    sys.exit(1)


NAME = 'CEdit'
__version__ = '3.1.0'
VERSIONSTR = '{} v. {}'.format(NAME, __version__)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])
OPTIONS = {
    'editor': 'editor to open files.',
    'elevcmd': 'elevation command for when root is needed.',
    'rooteditor': 'editor to use when elevation command is used.',
}
CONFIGFILE = os.path.join(SCRIPTDIR, 'cedit.conf')
settings = EasySettings(CONFIGFILE)
settings.name = NAME
settings.version = __version__

USAGESTR = """{ver}

    Opens files with your favorite editor,
    and uses an elevation command automatically when needed for
    write access.

    Usage:
        {script} -h | -l | -v
        {script} -s option...
        {script} PATH... [-- EDITOR_ARGS...]

    Options:
        EDITOR_ARGS             : Extra arguments to pass on to the editor.
                                  The -- separator must be used.
        PATH                    : One or more file names to open or create.
        -h,--help               : Shows this message.
        -l,--list               : Lists current config settings.
        -s option,--set option  : Sets a {name} option.
                                  Use option=value to set a value.
                                  Use option= to remove a setting.
                                  Current options are:
                                    {configopts}
        -v,--version            : Show cedit version and exit.

    {name} will look for a config file at: {configfile}
""".format(
    configfile=CONFIGFILE,
    configopts=', '.join(OPTIONS),
    name=NAME,
    script=SCRIPT,
    scriptdir=SCRIPTDIR,
    ver=VERSIONSTR)


def main(argd) -> int:
    """ Main entry point for cedit """
    settings.configfile_exists()

    if argd['--list']:
        configopts = settings.list_settings()
        if not configopts:
            print('No settings configured.')
            print('    {}'.format('\n    '.join(
                '{:>10}: [not set]'.format(opt) for opt in OPTIONS
            )))
            return 1
        print('Current cedit settings:')
        print('    {}'.format('\n    '.join(
            '{:>10}: {}'.format(k, v) for k, v in configopts)))
        return 0
    elif argd['--set']:
        return 0 if set_option(argd['--set']) else 1

    opaths = parse_filepaths(argd['PATH'])
    return 0 if shell_files(opaths, editorargs=argd['EDITOR_ARGS']) else 1


def build_cmd(editor, paths, as_root=False, editorargs=None) -> List[str]:
    """ Build a shell_file command from an editor, filepaths, and root flag.
        Returns a list of command/argument strings suitable for Popen.
    """
    if as_root:
        # root style.
        elevcmd = get_elevcmd()
        cmd = [quote_arg(elevcmd), quote_arg(editor)]
        print('Using elevation command...')
    else:
        # normal style, no root.
        cmd = [quote_arg(editor)]
    # Use the user's editor args.
    cmd.extend((quote_arg(s) for s in editorargs) if editorargs else [])
    # Quote file names for system().
    cmd.extend(quote_arg(p.with_linenum()) for p in paths)
    return cmd


def filenames_desc(opaths) -> str:
    """ Return a string describing the file names from user args.
        Ex: 'file: /this/that.txt'
            'directory: /this'
            '2 files, and 1 dir.'
    """

    CountDescs = namedtuple('CountDescs', ['files', 'dirs', 'new'])
    descs = CountDescs(
        PathDesc('file', 'files', paths=[]),
        PathDesc('directory', 'directories', paths=[]),
        # Non-existing paths, most editors will create a new file.
        PathDesc('a new file', 'new files', paths=[])
    )

    for op in opaths:
        if op.path.is_file():
            descs.files.count += 1
            descs.files.paths.append(op)
        elif op.path.is_dir():
            descs.dirs.count += 1
            descs.dirs.paths.append(op)
        else:
            descs.new.count += 1
            descs.new.paths.append(op)
    pcs = [str(desc) for desc in descs if desc.count > 0]
    pcslen = len(pcs)
    if pcslen > 1:
        pcs[-1] = 'and {}'.format(pcs[-1])
    return ', '.join(pcs)


def find_executable(name) -> Path:
    """ Look in $PATH for an executable.
        Returns a full Path on success, empty Path on failure.
    """
    namestr = str(name)
    if not namestr.strip():
        return Path()
    if name.exists() and is_executable(name):
        # Full path already passed.
        return name

    envpath = [
        s.strip() for s in os.environ.get('PATH', '/usr/bin').split(':')
    ]
    for trydir in envpath:
        if not trydir:
            continue
        trypath = trydir / name
        if trypath.exists() and is_executable(trypath):
            return trypath
    return Path()


def get_config_path(option, pathtype, defaults) -> Path:
    pathtype = pathtype or option
    configpathstr = settings.get(option, None)
    if not configpathstr:
        # no editor set
        print_err('\n'.join((
            'Be sure to set your favorite {pathtype} with:',
            '    cedit -s {editoropt}=[path_to_{pathtype}]'
        )).format(editoropt=option, pathtype=pathtype))
        # look for common editor
        for defaultname in (defaults or []):
            defaultpath = Path(defaultname)
            # Find executable, either absolute already, or in PATH.
            binpath = find_executable(defaultpath)
            if str(binpath):
                print('Found common {pathtype}: {path}'.format(
                    pathtype=pathtype,
                    path=binpath))
                return binpath
        raise InvalidConfig('\n'.join((
            'No common {pathtype}s found!',
            'You must set one using the above command.'
        )).format(pathtype=pathtype))

    # Have config, find the executable (either absolute, or in PATH).
    configpath = find_executable(Path(configpathstr))
    if str(configpath):
        return configpath

    raise InvalidConfig('\n'.join((
        'Cannot find editor! Make sure you set a valid editor with:'
        'cedit -s editor=[editor or /path/to/editor]'
    )))


def get_editor(as_root=False) -> Path:
    default_editors = ('kate', 'gedit', 'atom', 'leafpad', 'kwrite', 'vim')
    if as_root and settings.get('rooteditor', None):
        # Root editor config/defaults.
        return get_config_path(
            'rooteditor',
            'editor',
            defaults=default_editors
        )
    # Get normal editor config/defaults.
    return get_config_path(
        'editor',
        'editor',
        defaults=default_editors
    )


def get_elevcmd() -> Path:
    default_cmds = ('kdesudo', 'gksudo', 'sudo')
    return get_config_path(
        'elevcmd',
        'elevation command',
        defaults=default_cmds)


def is_executable(path) -> bool:
    """ Return True if the file is executable.
        Returns False on errors.
    """
    filepath = str(path)
    try:
        st = os.stat(filepath)
    except EnvironmentError as ex:
        print_err(
            'Error checking executable stat: {}\n{}'.format(filepath, ex))
        return False
    return bool(
        stat.S_ISREG(st.st_mode) and
        st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    )


def needs_root(opath) -> bool:
    """ Return True if a file needs root write permissions. """
    filepath = str(opath)
    if not filepath:
        print_err('Empty file path in needs_root(), using /.')
        filepath = '/'
        opath = OpenPath('/')

    if not opath.path.exists():
        # Determine write-status by directory for new files.
        return needs_root(opath.path.parent)

    try:
        if os.access(filepath, os.W_OK):
            # User already has write access.
            return False
        # File is owned by root?
        return (os.stat(filepath).st_uid == 0)
    except OSError as ex:
        print_err('Unable to stat path: {}\n{}'.format(filepath, ex))
        return False


def parse_args():
    """ Parse args with docopt, but manually set EDITOR_ARGS.
        Because PATHS.. -- ARGS.. doesn't seem to work. It thinks -- is a
        path argument.
    """
    argv = sys.argv[1:]
    try:
        argsep = argv.index('--')
    except ValueError:
        editorargs = []
    else:
        editorargs = argv[argsep + 1:]
        argv = argv[:argsep]

    argd = docopt(USAGESTR, argv=argv, version=VERSIONSTR)
    argd['EDITOR_ARGS'] = editorargs
    return argd


def parse_filepaths(filenames) -> Set['OpenPath']:
    """ Ensure that file/path names exist. Confirm any non-existing path
        names.
        Returns a set of OpenPath() if paths exist or user confirms,
        otherwise raises a UserCancelled() exception.
    """
    userpaths = set()
    for filename in filenames:
        p = OpenPath(filename)
        if not p.path.exists():
            print('Path does not exist: {}'.format(p))
            res = input('Would you like to use it anyway? (y/n): ').strip()
            if not res.lower().startswith('y'):
                raise UserCancelled()
        userpaths.add(p)
    return userpaths


def print_err(*args, **kwargs) -> None:
    """ Wrapper for print() that uses stderr by default. """
    if kwargs.get('file', None) is None:
        kwargs['file'] = sys.stderr
    print(*args, **kwargs)  # type: ignore
    return None


def quote_arg(s):
    """ Quote a file path, for a system() call. """
    return '"{}"'.format(str(s).replace('"', '\\"'))


def run_exec(cmdlist) -> int:
    # runs a command with arguments.
    return os.system(' '.join(str(p) for p in cmdlist))


def set_option(args) -> bool:
    def invalid_arg_exc(useropt, msg=None):
        """ Returns an InvalidArg with a custom message, pertaining to an
            invalid option name given by the user.
        """
        return InvalidArg('\n'.join((
            msg or '{useropt} is not a valid option!',
            'Accepted options are:',
            '    {accepted}'
        )).format(
            useropt=useropt,
            accepted='\n    '.join(
                '{}: {}'.format(opt, desc)
                for opt, desc in OPTIONS.items()
            )
        ))

    for sarg in args:
        try:
            sopt, sval = (s.lower().strip() for s in sarg.split('='))
        except ValueError:
            sopt = sarg.lower().strip()
            if sopt in OPTIONS:
                # Removing an option.
                sval = None
            else:
                raise invalid_arg_exc(
                    sarg,
                    msg='Unknown option, or wrong format: {useropt}')

        if (not sopt) or (sopt not in OPTIONS):
            raise invalid_arg_exc(sopt or '[no option given]')

        if not sval:
            # No value, we are removing an option.
            if not settings.remove(sopt):
                raise invalid_arg_exc(
                    sopt,
                    msg=', '.join((
                        'Unable to remove {useropt!r}',
                        'probably already removed.'))
                )

            if settings.save():
                print('    removed: {}'.format(sopt))
                return True

            print('    unable to remove: {}'.format(sopt))
            return False

        # Have value, we are setting an option.

        spath = str(find_executable(Path(sval)))
        if not spath:
            raise InvalidArg(
                'Cannot set option \'{}\', path not found: {}'.format(
                    sopt, sval
                )
            )
        # Found absolute path for config setting.
        sval = spath

        if settings.get(sopt) == sval:
            raise InvalidArg('{} already set to: {}'.format(sopt, sval))
        # valid setting, set it
        settings.setsave(sopt, sval)
        print('    set {} = {}'.format(sopt, sval))
    return True


def shell_files(opaths, editorargs=None) -> bool:
    as_root = any(needs_root(p) for p in opaths)
    editor = get_editor(as_root=as_root)
    print('Using editor: {}'.format(editor))
    print('Opening {}'.format(filenames_desc(opaths)))
    cmd = build_cmd(editor, opaths, as_root=as_root, editorargs=editorargs)
    try:
        # try running
        run_exec(cmd)
        print('Ran {}'.format(' '.join(cmd)))
    except Exception as ex:
        print('Unable to run command: {}\nError: {}'.format(
            ' '.join(cmd),
            ex))
        return False
    return True


class InvalidConfig(ValueError):
    """ Raised when bad config values cause an error. """
    pass


class InvalidArg(InvalidConfig):
    """ Raised when bad arguments cause an error. """
    pass


class OpenPath(object):
    """ Extends pathlib.Path to include linenumber/column in the
        filepath:line:col format, only revealing them when with_linenum()
        is called.
    """
    def __init__(self, *args, **kwargs) -> None:
        pcs = list(args)
        if pcs:
            # Allow line numbers and columns in the path.
            pcs[-1], linenum, column = self.parse_line_col(pcs[-1])
        else:
            linenum = column = None

        self.linenum = linenum or None
        self.column = column or None
        self.path = Path(*pcs, **kwargs)

    def __str__(self) -> str:
        """ Returns str(self.path). For linenums/cols use with_linenum(). """
        return str(self.path)

    @staticmethod
    def parse_line_col(s) -> Tuple[str, str, str]:
        """ Parse a line and column number from a file path, in the style:
                mydir/myfile.txt:LINE
                mydir/myfile.txt:LINE:COL
            Returns a tuple of (filepath, line, column).
        """
        filepath, _, col = s.rpartition(':')
        if not filepath:
            return s, '', ''
        trypath, _, line = filepath.rpartition(':')
        if trypath:
            filepath = trypath
        else:
            line = col
            col = ''
        return filepath, line, col

    def with_linenum(self) -> str:
        """ Recreate the filepath:line:col style if this CeditPath has
            line numbers/columns in it.
        """
        s = str(self.path)
        if self.linenum:
            s = ':'.join((s, self.linenum))
        if self.column:
            s = ':'.join((s, self.column))
        return s


class PathDesc(object):
    """ Manages user arg path counts and descriptions. """
    def __init__(self, name, plural, paths) -> None:
        self.count = 0
        self.name = name
        self.plural = plural
        self.paths = paths or []

    def __str__(self) -> str:
        self.count = len(self.paths)
        if self.count == 1:
            return '{} {}: {}'.format(
                self.count,
                self.name,
                self.paths[0]
            )
        return '{} {}'.format(
            self.count,
            self.name if self.count == 1 else self.plural,
        )


class UserCancelled(KeyboardInterrupt):

    def __init__(self, msg=None) -> None:
        self.msg = msg or 'User cancelled.'

    def __str__(self) -> str:
        return str(self.msg)


if __name__ == '__main__':
    try:
        mainret = main(parse_args())
    except (UserCancelled, KeyboardInterrupt, EOFError) as ex:
        msg = getattr(ex, 'msg', UserCancelled().msg)
        print_err(msg)
        mainret = 2
    except (InvalidArg, InvalidConfig) as ex:
        print_err(str(ex))
        mainret = 1
    # except Exception as ex:
    #     print_err('General error: {}'.format(ex))
    #     mainret = 1
    sys.exit(mainret)
