#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    cedit.py
    Designed to open files with your favorite editor while using your favorite
    elevation command when needed for permissions.
    Keeps you from seeing 'no permissions' messages, and instead asks you
    for your password.

    If no 'favorites' are set yet, cedit will look for 'popular' editors and
    elevation commands. It will use the first one found.
    If none of the 'popular' commands are found, you have to set your own.
    They can be set using the 'set' flags (-e, -c). (see --help).

    Search paths are now included, so you can save typing long paths for your
    most commonly used directories. Set your 'favorite' directories with the
    -d flag, and cedit will check those dirs when a file name isn't found in
    the current dir, or relative to the current dir.
    Example:
        # Current dir contains 'myfile2.py'
        $ ls
        $     myfile2.py

        # Project dir contains 'myfile1.py' and 'myfile2.py'
        $ ls /home/me/workspace/myproject/src
        $     myfile1.py    myfile2.py    myfile3.py

        # Add project dir to cedit search paths
        $ cedit -d "/home/me/workspace/myproject/src"

        # open /home/me/workspace/myproject/src/myfile1.py
        $ cedit myfile1.py

        # open ./myfile2.py (current dir)
        $ cedit myfile2.py

        # open /home/me/workspace/myproject/src/myfile2.py
        # (provided the the parent dir doesn't also contain a 'myfile2.py')
        $ cd ..
        $ cedit myfile2.py


    If you are using Python2 the pip command can install requirements,
    otherwise pip3 or a Python3-compatible package installer should be used.

    Requires:
        easysettings
                saves configuration, to install: pip3 install easysettings
        docopt
                parses arguments, to install: pip3 install docopt

    Installation:
        To install cedit as a global terminal command you can use
        the 'install' command.

        For installing for a single user run:
            ./cedit.py --install --user

        For installing in /usr/bin (for all users) run:
            sudo ./cedit.py --install

    Created on Jan 19, 2013

    Christopher Welborn <cj@welbornprod.com>
"""
from __future__ import print_function
import json
import os
import re
import sys
import subprocess

# enable/disable debug mode
DEBUG = False
# determine python version (for better help on required packages/pip)
PYTHON3 = (sys.version[0] == '3')
# determine input function.
if not PYTHON3:
    input = raw_input  # noqa

# Name, also used in creating symlinks in cmd_install()
NAME = 'cedit'
VERSION = '1.5.0'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(sys.argv[0])[1]

# looks better in help to have the real user name,
# if not found then just use 'user'
USER = os.environ.get('USER', 'user')

# List of dirs to search for files in, before giving up with 'File Not Found'.
# The current dir, or an existing full path always comes first.
# These dirs are searched after those fail.
CEDITPATHS = []

# Usage string args (for formatting, filling in blanks.)
usage_args = {
    'verstr': VERSIONSTR,
    'name': NAME,
    'script': SCRIPT,
    'pyversion': sys.version.split()[0],
    'user': USER
}
# Usage string
usage_str = """{verstr} (running on Python {pyversion})

    Usage:
        {script} <filename>... [options]
        {script} -a <alias_name> <alias_value> [-D]
        {script} [-A | -h | -v]
        {script} -d directories [-o] [-D]
        {script} (-e path_to_editor | -c path_to_elevcmd) [-D]
        {script} -i [-u | -p dir] [-D]
        {script} -l [-D]
        {script} -r [-D]

    Options:
        -a,--alias                      : Set an alias. This is useful for
                                          calling your editor with certain
                                          arguments (using only a simple name).
        -A,--about                      : show message about {name}.
        -c file,--elevcmd file          : set favorite elevation command, where
                                          filepath is the path to your
                                          elevation command.
        -D,--debug                      : for development, prints random msgs.
        -d dirs,--dirs dirs             : comma-separated list of directories
                                          to search for files.
                                          current dir or an existing full path
                                          always has priority.
                                          dirs are searched when those fail.
                                          you can pass 'none' or '-' to clear
                                          dirs, or just edit the config file.
        -e file,--editor file           : set favorite editor, where filepath
                                          is the path to your editor.
        -h,--help                       : show this help message.
        -i,--install                    : install {name}, creates symlink in
                                          /usr/local/bin, /usr/bin, or home
                                          (see -u and -p)
                                          /usr/local/bin is used if found in
                                          $PATH, otherwise /usr/bin is used.
                                          if -u or -p is passed also, the
                                          install path is determined by the
                                          flag. cedit will ask for confirmation
                                          before installing.
        -l,--list                       : list current {name} settings.
        -o,--overwrite                  : when setting dirs with -d, overwrite
                                          the current settings.
        -p dir,--path dir               : when installing, install to specified
                                          directory.
        -q,--quiet                      : Don't warn about non-existing files.
        -r,--remove                     : remove the installed symlink for
                                          {name} if installed.
                                          (may require permissions)
        -s,--shellall                   : shell one process per file, instead
                                          of sending all file names at once.
        -u,--user                       : when installing, only install for
                                          user. $PATH is searched for dirs like
                                          /home/{user}/bin.
                                          without $PATH, common dirs are looked
                                          for.
        -v,--version                    : show version.
        alias_name                      : alias name to create or change.
        alias_value                     : file name or {name} args to save.
        filename                        : file to open, or an alias to use.

    Notes:
        You can pass arguments on to the editor using the '--' option.
        Any arguments after the '--' are passed on to your editor.
        Example:
            {script} -- --help
            ..this would send the --help flag to your editor.

    Settings:
        editor   : path to favorite editor.
        elevcmd  : path to favorite elevation command.

    Example:
        cedit myfile.txt
            ...opens myfile.txt, using elevation command if needed.

        cedit myfile1.txt myfile2.txt
            ...opens both files with your editor, using elevation command if
               at least 1 file needs it.

        cedit *.py
            ...uses your shells expansion to open all .py files in
               the current directory.

        cedit --editor gedit
            ...sets favorite editor to 'gedit'

        cedit --elevcmd kdesudo
            ...sets favorite elevation command to 'kdesudo'

        cedit --dirs /home/{user},/home/{user}/dump
            ...adds 2 directories to cedit's search path.

""".format(**usage_args)


# I hate putting these functions here, but for better help I will.
def cmd_exists(shortname):
    """ Determines if link/alias/shortname of command
        is available using 'which' command.
        returns True, False
    """

    whichcmd = ['which', shortname]
    retcode = subprocess.call(whichcmd, stdout=subprocess.PIPE)
    return retcode == 0


def get_pip_name():
    """ determine if pip is installed,
        if it is find whether or not pip3 is installed.
        return string containing desired pip version, or '' if none is found.
    """

    # Support python 3 pip-executables for many years to come :P
    pip3versions = ['3'] + ['3.{}'.format(i) for i in range(10)]
    # py2 pip-executables to support.
    pip2versions = ['', '2', '2.6', '2.7']
    pip2exes = []
    for pver in pip2versions:
        pip2exes.append('pip{}'.format(pver))
        pip2exes.append('pip-{}'.format(pver))
    pip3exes = []
    for pver in pip3versions:
        pip3exes.append('pip{}'.format(pver))
        pip3exes.append('pip-{}'.format(pver))

    if PYTHON3:
        # Try all pip3 executables, break if we find one.
        for pipexe in pip3exes:
            if cmd_exists(pipexe):
                return pipexe
    # For python3, we will fall through to see if ANY pip is installed,
    # so we can warn the user that they need a pip that works with Python3.
    # Try all pip2 executables...
    for pipexe in pip2exes:
        if cmd_exists(pipexe):
            return pipexe
    # No pip command found.
    return ''


def warn_module(importname, pipver):
    """ Module couldn't be imported, show a message about it
        with recommended pip version for install instructions.
    """
    modulewarning = [''.join(['You need to have {} '.format(importname),
                              'installed to use cedit.'])]
    if pipver:
        modulewarning.append('To install it run:')
    else:
        # no pip installed
        modulewarning.append('After installing a python-package manager,')
        modulewarning.append('Install the module with:')
    modulewarning.append('{} install {}'.format(pipver, importname.lower()))
    print('\n'.join(modulewarning))


def warn_pip(importname):
    """ Module couldn't be imported, so show a message about it.
        Also, show a warning about needing pip installed if it isn't already,
        or having only pip2 installed while using Python3.
        If all pip requirements are met,
        it doesn't show a warning about it, just the module.
        Returns: True if warning was printed, False if not.
        (return isn't used right now)
    """

    # Check pip info
    pipname = get_pip_name()
    pipsuggested = 'pip3' if PYTHON3 else 'pip'
    pypkg = 'python-{}'.format(pipsuggested)

    # No pip installed.
    if not pipname:
        print(''.join(['You don\'t have pip installed, ',
                       'you can install packages using something ',
                       'else if you want,\n',
                       'but I would recommend installing ',
                       '{} '.format(pypkg),
                       'to get the required packages for cedit.']))
        warn_module(importname, pipsuggested)
        return True

    if PYTHON3:
        ver = '3'
        noversionokay = False
    else:
        ver = '2'
        noversionokay = True
    pyver = 'Python{}'.format(ver)

    if (ver not in pipname) and (not noversionokay):
        print(''.join(['You have \'pip\' installed, ',
                       'but it doesn\'t look like a ',
                       '{}-compatible version.\n'.format(pyver),
                       'You may need to install {} '.format(pypkg),
                       '(if \'pip\' already points to a valid ',
                       'version ignore this.)']))
        warn_module(importname, pipname)
        return True

    # No warnings were shown.
    warn_module(importname, pipname)
    return False


# Try importing EasySettings, I doubt that anyone has this installed yet.
try:
    from easysettings import EasySettings
except ImportError as ex_es:
    warn_pip('EasySettings')
    sys.exit(1)
# Try importing Docopt, some people still prefer the old ways.
try:
    import docopt
except ImportError as ex_es:
    warn_pip('Docopt')
    sys.exit(1)


def can_write(filename):
    """ checks for write access on a file/dir. """

    return (os.access(filename, os.W_OK))


def check_file(filename):
    """ checks if a file exists, if not asks user if we should continue.
        returns True if user says yes, otherwise False.
    """

    if os.path.isfile(filename):
        return True
    elif os.path.exists(filename):
        # Directory, just pass it through. Some editors can handle this.
        print('Trying to open a directory: {}'.format(find_dir(filename)))
        return True
    else:
        print('File does not exist!: ' + filename)
        print('\nsome editors will automatically create this file...')
        response = input('would you like to continue anyway? (y/n): ')
        return (response.lower().strip(' ').strip('\t').startswith('y'))


def check_files(filenames):
    for filename in filenames:
        if not check_file(filename):
            return False
    # All existed, or some/all were created.
    return True


def check_path(sdir):
    """ Checks users $PATH to see if directory is in it. """

    paths = get_userpath()
    if paths:
        if sdir in paths:
            return True
        else:
            if sdir.endswith('/'):
                if sdir[:-1] in paths:
                    return True
    return False


def clear_cedit_paths():
    """ Remove cedit search paths from settings. (if any are set.) """
    global CEDITPATHS

    if CEDITPATHS:
        CEDITPATHS = []
        success = settings.setsave('paths', '')
        if success:
            print('\nCleared all cedit search directories.')
            return 0

        # Error saving settings.
        print('\nUnable to save cleared search directories.')
        return 1

    # No paths set  yet.
    print('\nNo cedit search directories set yet.\n'
          'use {} -d /my/dir to set some.'.format(SCRIPT))
    return 1


def cmd_alias_add(name, args):
    """ Save an alias to config.
        Arguments:
            name  : Name for the alias (overwrites existing names)
            args  : List/Tuple of arguments for this alias.
    """
    if not args:
        print('\nAn alias needs arguments.\n')
        return 1

    aliases = load_aliases()
    if name in aliases:
        msg = '\n'.join((
            'This alias already exists: {}\n'.format(name),
            'Would you like to overwrite it?'))
        if not confirm(msg):
            print('\nUser cancelled.\n')
            return 1
    aliases[name] = args
    try:
        aliasjson = json.dumps(aliases)
    except (TypeError, ValueError) as ex:
        print('\nError converting aliases to json: {}'.format(ex))
        return 1

    if settings.setsave('aliases', aliasjson):
        print('\nSaved alias: {}'.format(name))
        print('      value: {}'.format(' '.join(args)))
        return 0

    print('\nUnable to save alias: {}'.format(name))
    return 1


def cmd_list():
    """ list command. """

    alloptions = sorted(settings.list_options())
    if not alloptions:
        print(''.join(['no settings yet.\n'
                       'use {} -e (or -c) '.format(SCRIPT),
                       'to set your favorite editor or elevation command.']))
        return 1

    longestnamelen = len(max(alloptions, key=len))

    # print current settings
    print('current settings:')
    for optname in alloptions:
        val = settings.get(optname)
        if optname == 'paths':
            # Special care taken when printing paths (if paths are set).
            if val:
                print('  {} :'.format(optname.ljust(longestnamelen)))
                for p in sorted(val.split(':')):
                    print('  {}   {}'.format((' ' * longestnamelen), p))
                continue
        # Normal setting. print opt : val.
        if not val:
            val = '(not set yet!)'
        print('  {} : {}'.format(optname.ljust(longestnamelen), val))
    return 0


def cmd_location(shortname):
    """ Like cmd_exists() except, it returns the output from 'which'.
        On failure, returns None.
    """

    try:
        output = subprocess.check_output(['which', shortname])
        return output.decode('utf-8').strip('\n').strip()
    except subprocess.CalledProcessError:
        return None


def cmd_install(userdir=None):
    """ installs cedit globally by default,
        userdir == ('auto' or '') will look for users /bin directory.
        userdir == '/path/to/dir'  will try to install in that directory.
        userdir == None will try to install in /usr/bin
    """
    scriptfile = os.path.realpath(__file__)
    if not scriptfile:
        print('\nunable to determine full path to cedit script!\n')
        return 1

    if userdir is not None:
        # local install, try auto first.
        if userdir == 'auto' or userdir == '':
            userbin = get_userbin()
            if userbin:
                location = userbin
            else:
                location = None
        # manual dir was set.
        else:
            location = userdir

        if not os.path.isdir(location):
            print(''.join(['not a directory: {}\n'.format(location),
                           'create the directory and try again.\n',
                           'also make sure the directory is included ',
                           'in your PATH environment variable.\n',
                           'otherwise, the symlink won\'t work.']))
            return 1
    else:
        # Global
        if check_path('/usr/local/bin') and os.path.isdir('/usr/local/bin'):
            location = '/usr/local/bin'
        else:
            location = '/usr/bin'

    # already installed?
    finalname = os.path.join(location, NAME)
    installedloc = cmd_location(NAME)
    if not installedloc:
        # Try full path.
        installedloc = cmd_location(finalname)
    if installedloc:
        print(''.join(['it seems that cedit is already '
                       'installed at: {}\n'.format(installedloc),
                       'you will need to remove it if you want '
                       'to re-install cedit.\n']))
        return 1

    # Confirm installation.
    doinstall = input(''.join(['cedit will install to: {}\n'.format(location),
                               'continue with installation? (yes/no): ']))
    if not doinstall.lower().strip().strip('\t').startswith('y'):
        print('\ninstallation canceled.\n')
        return 1

    # Try Installation.
    try:
        print('trying to create symlink in: {}'.format(location))
        os.symlink(scriptfile, finalname)
        print(''.join(['success!\n',
                       '...you may have to restart your terminal to use ',
                       'the command \'{}\''.format(NAME)]))
    except OSError as exos:
        print(''.join(['error:\n{}\n\n'.format(exos),
                       'try running \'{} install\' '.format(SCRIPT),
                       'as root for global installation.\n',
                       'example: sudo {} install\n'.format(SCRIPT)]))
        return 1
    except Exception as ex:
        print('unable to create symlink with: {}\n{}'.format(finalname, ex))
        return 1

    return 0


def cmd_remove():
    """ Trys to uninstall/remove the cedit symlink (if any exists) """

    loc = cmd_location(NAME)
    if not loc:
        print('\ncan\'t finc {} installed anywhere.\n'.format(NAME))
        return 1

    # Confirm removal.
    doremove = input(''.join(['this will remove {} from: ',
                              '{}\n'.format(NAME, loc),
                              'you will need to have the permissions ',
                              'required to do this.\n\n',
                              'continue with removal? (yes/no): ']))
    if not doremove.lower().strip().strip('\t').startswith('y'):
        print('\nremoval canceled.\n')
        return 1

    # Try removing it.
    try:
        os.remove(loc)
    except OSError as exos:
        print('\nunable to remove {}!:\n{}'.format(NAME, exos))
        return 1

    # Success.
    print('\n{} was successfully removed from: {}\n'.format(NAME, loc))
    return 0


def confirm(question):
    """ Confirm a question using input.
        Returns True for yes, False for no.
    """
    if not question.endswith('?'):
        question = ''.join((question, '?'))
    question = '\n{} (y/N): '.format(question)
    answer = input(question).lower().strip()
    return answer.startswith('y')


def find_dir(s):
    """ Uses os.path.expanduser and os.path.abspath to get actual dir names
        from paths like: "~/cedit/.."
        Example:
            ~ == '/home/me'
            print(find_dir('~/cedit/../../'))
            # prints: '/home'
    """
    if '~' in s:
        # Expand user, then parse relative paths.
        return os.path.abspath(os.path.expanduser(s))
    else:
        # No home needed, and expanduser without ~ returns relative to home.
        return os.path.abspath(s)


def find_filename(s):
    """ Finds a file path by filename.
        Checks current dir/full existing path:
            If os.path.exists(s), return s.
        Checks CEDITPATHS:
            If os.path.exists(path + s for path in CEDITPATHS), return path + s
        Returns s (original filename) on failure to match any of these.
    """
    if os.path.exists(s):
        return s

    for ceditpath in [os.path.join(p, s) for p in CEDITPATHS]:
        print_debug('Checking against cedit path: {}'.format(ceditpath))
        if os.path.exists(ceditpath):
            return ceditpath

    # Couldn't find it.
    return s


def get_cedit_paths():
    """ Retrieve current config for cedit paths. """

    configstr = settings.get('paths', None)
    if not configstr:
        return []
    return sorted(configstr.split(':'))


def get_editor():
    """ Return the user's editor args, or the default args.
        Exit the program on complete failure.
    """
    editorstr = settings.get('editor', '')
    if not editorstr:
        return get_editor_default()

    userargs = editorstr.split()
    if os.path.isfile(userargs[0]) or os.path.islink(userargs[0]):
        return userargs

    # try /usr/bin
    spath = os.path.join('/usr/bin', userargs[0])
    if os.path.isfile(spath) or os.path.islink(spath):
        userargs[0] = spath
        return userargs

    print('\n'.join((
        'Cannot find editor!',
        'Make sure you set a valid editor with:',
        '{} set editor=[editor or /path/to/editor]'
    )).format(SCRIPT))
    sys.exit(1)


def get_editor_default():
    """ Return the default editor args if available,
        otherwise exit the program.
    """
    # no editor set
    print('\n'.join((
        'Be sure to set your favorite editor with:',
        '{} --editor path_to_editor'
    )).format(SCRIPT))
    # look for common editor (current only uses /usr/bin)
    lst_editors = ('subl', 'kate', 'gedit', 'leafpad', 'kwrite')
    for editor in lst_editors:
        spath = os.path.join('/usr/bin/', editor)
        if os.path.isfile(spath) or os.path.islink(spath):
            print('Found common editor: {}'.format(spath))
            return [spath]
    print('\n'.join((
        'No common editors found!',
        'You must set one using the above command.'
    )))
    sys.exit(1)


def get_elevcmd():
    """ Return the  user's elevation command args as a list,
        or the default elevation command args.
        Exits the program on complete failure.
    """
    elevcmdstr = settings.get('elevcmd', '')
    if not elevcmdstr:
        # no editor set
        return get_elevcmd_default()

    elevcmdargs = elevcmdstr.split(' ')
    if os.path.isfile(elevcmdargs[0]) or os.path.islink(elevcmdargs[0]):
        return elevcmdargs

    # try /usr/bin
    spath = os.path.join('/usr/bin', elevcmdargs[0])
    if os.path.isfile(spath) or os.path.islink(spath):
        elevcmdargs[0] = spath
        return elevcmdargs

    print('\n'.join((
        'Cannot find elevcmd!',
        'Make sure you set a valid elevation command with:',
        '{} set elevcmd=[elevcmd or /path/to/elevcmd]'
    )).format(SCRIPT))
    sys.exit(1)


def get_elevcmd_default():
    """ Return the first available elevation command as a list of arguments.
        Exit the program on failure.
    """
    print('\n'.join((
        'Be sure to set your favorite elevation command with: ',
        '    {} --elevcmd path_to_elevation_command'
    )).format(SCRIPT))
    # look for common elevation command
    lst_elevs = ['kdesudo', 'gksudo', 'sudo']
    for elevcmd in lst_elevs:
        spath = os.path.join('/usr/bin/', elevcmd)
        if os.path.isfile(spath) or os.path.islink(spath):
            print('Found common elevation cmd: {}'.format(spath))
            return [spath]
    print('\n'.join((
        'No common elevation commands found! ',
        'You must set one using the above command.'
    )))
    sys.exit(1)


def get_userpath():
    """ Trys to retrieve a list of $PATH entries, returns None on failure.
    """
    ospath = os.environ.get('PATH', None)
    paths = None
    if ospath:
        paths = ospath.split(':') if ':' in ospath else [ospath]
    return paths


def get_userbin():
    """ trys to retrieve the users /home/user/*/bin, if one is available.
        returns: String containing path to known /bin, or None on failure.
    """

    # Try getting username for finding a bin later.
    username = get_username()
    # Try getting $PATH, for finding a bin later.
    ospath = os.environ.get('PATH', None)
    if ospath:
        paths = ospath.split(':') if ':' in ospath else [ospath]
    else:
        paths = None

    if username:
        # Try finding it in $PATH
        ospath = os.environ.get('PATH', None)
        if paths:
            repat = re.compile(r'/home/{}.+/bin'.format(username))
            for pathentry in paths:
                rematch = repat.search(pathentry)
                if rematch:
                    # Found /home/username/bin or /home/username/dir/bin
                    if os.path.isdir(pathentry):
                        return pathentry
        # Try brute forcing
        possiblepaths = 'bin', 'local/bin', '.local/bin'
        for possiblepath in possiblepaths:
            fullpath = os.path.join('/home', username, possiblepath)
            if os.path.isdir(fullpath):
                # Found existing /home/user/bin dir.
                return fullpath

    # No user name to go on, try sketchy environ search.
    # (may return someone elses /home/bin if they are using it in PATH)
    elif paths:
        repat = re.compile('/home/.+/bin')
        for pathentry in paths:
            rematch = repat.search(pathentry)
            if rematch:
                # Found someones /home/?/bin...
                return pathentry

    # Nothing to go on. no username, no paths.
    return None


def get_userhome():
    """ trys a couple methods to get the users /home directory.
        returns string path, or None on failure.
    """

    homedir = os.environ.get('HOME', None)
    if homedir is None:
        username = get_username()
        if username:
            tryhomedir = os.path.join('/home', username)
            if os.path.isdir(tryhomedir):
                homedir = tryhomedir

    return homedir


def get_username():
    """ trys several different ways to get user name """

    uname = os.environ.get('USER', None)
    if uname is None:
        uname = os.environ.get('LOGNAME', None)
        if uname is None:
            uname = os.environ.get('HOME', None)
            if uname is not None:
                uname = os.path.split(uname)[1]
    return uname


def good_return(returnvalue):
    """ Just returns True if returnvalue == 0,
        used in list comprehension in main()
    """
    # This is kinda dumb, should be replaced.
    goodret = True if returnvalue == 0 else False
    return goodret


def init_args(args):
    """ Initialize editor args, and parse cedit args with docopt.
        Sets CEDITARGS, EDITORARGS (through init_editor_args())
        Returns a docopt arg dict.
    """
    # Handle editor args.
    init_editor_args(args)
    # Handle cedit args.
    return docopt.docopt(usage_str, argv=CEDITARGS, version=VERSIONSTR)


def init_editor_args(args):
    """ Grabs extra editor args to hack around docopt.
        Sets global EDITORARGS if any are found.
        Sets global CEDITARGS if any are found.
    """
    global EDITORARGS, CEDITARGS, DEBUG
    if ('-a' in args) or ('--alias' in args):
        # Handle adding aliases (docopt sucks when aliases have args in them)
        # TODO: Rewrite arg parsing, remove docopt (since it can't do what
        #       I need it to do), it will make the code much cleaner and
        #       and easier to read. This is getting out of hand. It started
        #       with '--' and 'EDITORARGS', and now this 'alias' stuff.
        args = args[1:]
        try:
            args.remove('-a')
        except ValueError:
            args.remove('--alias')
        # Allow debug mode when adding an alias.
        if ('-D' in args) or ('--debug' in args):
            DEBUG = True
            try:
                args.remove('-D')
            except ValueError:
                args.remove('--debug')
        if len(args) < 2:
            # Not enough arguments for -a,--alias
            usage = docopt.printable_usage(usage_str)
            print(usage)
            sys.exit(1)

        exitcode = cmd_alias_add(args[0], args[1:])
        sys.exit(exitcode)
    elif '--' in args:
        # Hack around docopt to pass args onto the actual editor app.
        CEDITARGS = args[1:args.index('--')]
        if not CEDITARGS:
            CEDITARGS = ['!ARGPASS']
        EDITORARGS = args[args.index('--') + 1:]
    else:
        # Normal cedit args.
        CEDITARGS = args[1:]
        EDITORARGS = []


def load_aliases():
    """ Load aliases from config. """
    aliasjson = settings.get('aliases', '')
    if not aliasjson:
        return {}
    try:
        aliases = json.loads(aliasjson)
    except ValueError as ex:
        print('\nAlias config is invalid json!: {}'.format(ex))
        return {}
    return aliases


def needs_root(sfilename):
    # already root user
    if os.getuid() == 0:
        return False

    # If the file doesn't exist, stat the directory instead.
    if os.path.exists(sfilename):
        statpath = sfilename
    else:
        statpath = os.path.split(sfilename)[0]
        if not statpath:
            statpath = os.getcwd()
        print_debug('new file, stat() dir: {}'.format(statpath))

    try:
        # file is owned by root.
        if (os.stat(statpath).st_uid == 0):
            print_debug('os.stat said root.')
            return True
        else:
            # check files that aren't owned by root.
            # we may not be able to write to them.
            c_w = can_write(statpath)
            print_debug('os.stat said not root, can_write={}'.format(c_w))
            return (not c_w)
    except OSError:
        return True
    except Exception as ex:
        print('needs_root(): Error: \n{}'.format(ex))
        # i dunno.
        return True


def plural(word, number):
    """ Return word if number == 1, else word + 's' """
    return word if number == 1 else '{}s'.format(word)


def print_debug(s):
    if DEBUG:
        print('DEBUG: {}'.format(s))


def printdict(d, indention=0):
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                printdict(v, indention=indention + 4)
            else:
                print('{}{}: {}'.format((' ' * indention), k, v))
    else:
        print('{}{}'.format((' ' * indention), d))


def run_alias_args(aliasargs, extra_args=None):
    """ Run cedit with a new set of args (from an alias). """
    # Re-initialize all user args based on this alias.
    args = aliasargs or []
    if extra_args:
        args.extend(extra_args)
    args.insert(0, SCRIPT)
    argd = init_args(args)
    # Re-run with these alias args.
    return main(argd)


def run_exec(cmdlist):
    """ runs a command with arguments. """

    try:
        # use subprocess so cedit can return control to the user.
        ret = subprocess.call(cmdlist)
    except Exception as exsub:
        print('Error running with subprocess:\n{}'.format(exsub))
        print('Falling back to system call.')
        try:
            # try system-command method. (does not return control)
            ret = os.system(' '.join(cmdlist))
        except Exception as ex:
            raise Exception(ex)

    return ret


def set_cedit_paths(s, overwrite=False):
    """ Add to current cedit paths, or create a new list of paths.
        Saves the paths in config.

        Arguments:
            s          : Comma-separated string of paths/dirs to set.
            overwrite  : Overwrite any current settings.
                         Default: False
    """
    global CEDITPATHS
    # Shortcut for clearing all paths if '-' or 'none' is passed.
    if s.lower() in ('-', 'none'):
        return clear_cedit_paths()

    if overwrite:
        # Start a new set of paths.
        paths, oldpaths = [], []
    else:
        # Append to current settings, compare changes later.
        paths, oldpaths = CEDITPATHS[:], CEDITPATHS[:]

    newpaths = []
    for userpath in [find_dir(p.strip()) for p in s.split(',')]:
        if not os.path.isdir(userpath):
            print('Invalid directory: {}'.format(userpath))
            continue
        elif userpath in paths:
            print('Already set: {}'.format(userpath))
            continue
        paths.append(userpath)
        newpaths.append(userpath)

    if not paths:
        # No paths.
        print('\nNo cedit paths are set.')
        return 1
    elif not newpaths:
        print('\nNo changes were made to the cedit search directories.')
        return 1

    if paths:
        # Have paths to save.
        CEDITPATHS = sorted(list(set(paths[:])))
        success = settings.setsave('paths', ':'.join(CEDITPATHS))
        if success:
            newlen = len(newpaths)
            pathstr = plural('path', newlen)
            print('\nSaved {} new cedit {}:'.format(newlen, pathstr))
            print('    {}'.format('\n    '.join(sorted(newpaths))))
            if oldpaths:
                oldlen = len(oldpaths)
                pathstr = plural('path', oldlen)
                print('\nAnd {} existing cedit {}:'.format(oldlen, pathstr))
                print('    {}'.format('\n    '.join(sorted(oldpaths))))
            return 0
        else:
            print('\nUnable to save cedit paths.')
            return 1


def set_setting_safe(opt, val):
    """ Sets a setting, but not if its already set to the same thing,
        and not if the value, the filepath to editor/elevcmd, doesn't exist.
    """
    oldval = settings.get(opt)
    if oldval == val:
        print('\n{} is already set to \'{}\''.format(opt, oldval))
        return 1

    # Allow spaces for adding arguments to the editor.
    args = val.split()
    if not os.path.isfile(args[0]):
        args[0] = os.path.join('/usr/bin', args[0])
        if not os.path.isfile(args[0]):
            print('\nthat {} doesn\'t exist!: {}'.format(opt, args[0]))
            return 1
        val = ' '.join(args)

    if settings.setsave(opt, val):
        print('\n{} is now set to: {}'.format(opt, val))
        return 0
    else:
        print('\nUnable to set option: {}'.format(opt))
        return 1


def shell_file(filenames):
    """ Shell an editor to open a list of filenames. (list length may be 1).
        Arguments:
            filenames  : List of filenames to open.
    """
    # Grab current editor.
    usereditor = get_editor()
    editor = usereditor[0]
    if (not editor.startswith('/')) and (not os.path.isfile(editor)):
        # try /usr/bin... (location for most popular editors)
        editor = '/usr/bin/{}'.format(editor)
    if not os.path.isfile(editor):
        print('Editor not found!: {}'.format(editor))
        return 1
    usereditor[0] = editor
    usereditorstr = ' '.join(usereditor)
    print('Using editor: {}'.format(usereditorstr))

    # Start building command args.
    finalcmd = usereditor
    if filenames:
        # See if any of the files need root.
        for filename in filenames:
            if needs_root(filename):
                # root style.
                elevcmdargs = get_elevcmd()
                finalcmd = elevcmdargs + finalcmd
                print('\n'.join((
                    'Using elevation command: {}',
                    'File needs root: {}\n'
                )).format(elevcmdargs[0], filename))
                break
        # Append list of filenames.
        finalcmd.extend(filenames)

    # Append editor args (from -- cmdline switch)
    if EDITORARGS:
        finalcmd.extend(EDITORARGS)
    cmdstr = ' '.join(finalcmd)
    try:
        # try running
        run_exec(finalcmd)
        print('Ran: {}'.format(cmdstr))
    except Exception as ex:
        print('Unable to run command: {}'.format(cmdstr))
        print('Error:\n{}'.format(ex))
        return 1
    return 0


# MAIN ----
def main(argd):
    """ Main entry point for cedit.
        Expects docopt argument dict.
    """
    global DEBUG, CEDITPATHS
    DEBUG = argd['--debug']

    CEDITPATHS = get_cedit_paths()

    # show about message?
    if argd['--about']:
        print(__doc__)
        return 0
    # install
    elif argd['--install']:
        if argd['--path']:
            # User-specified path
            return cmd_install(userdir=argd['--path'])
        elif argd['--user']:
            # Auto user-dir.
            return cmd_install(userdir='auto')
        else:
            # Global dir.
            return cmd_install()
    # set dirs
    elif argd['--dirs']:
        return set_cedit_paths(argd['--dirs'], overwrite=argd['--overwrite'])
    # set editor
    elif argd['--editor']:
        return set_setting_safe('editor', argd['--editor'])
    # set elevcmd
    elif argd['--elevcmd']:
        return set_setting_safe('elevcmd', argd['--elevcmd'])
    # list current settings.
    elif argd['--list']:
        return cmd_list()
    # remove (uninstall)
    elif argd['--remove']:
        return cmd_remove()

    # get filenames, check existence
    filenames = argd['<filename>']
    # Hack around docopt to pass args on to the editor.
    # EDITORARGS has already been set, now remove this ARGPASS flag.
    if '!ARGPASS' in filenames:
        filenames.pop(filenames.index('!ARGPASS'))

    if filenames:
        # Check for aliases.
        aliases = load_aliases()
        alias_args = aliases.get(filenames[0], '')
        if alias_args:
            extra_args = filenames[1:] if len(filenames) > 1 else None
            return run_alias_args(alias_args, extra_args=extra_args)

        # Use cedit search paths to locate some files. Others are left alone.
        filenames = [find_filename(f) for f in filenames]
        # Open files separately
        # (where some editors don't support multi-file opening.)
        if argd['--shellall']:
            returns = []
            for filename in filenames:
                if argd['--quiet'] or check_file(filename):
                    returns.append(good_return(shell_file([filename])))
                else:
                    returns.append(1)
            return 0 if all(returns) else 1

        # Send all file names to one process.
        if argd['--quiet'] or check_files(filenames):
            return shell_file(filenames)
    else:
        # No cedit args, run editor (possibly with EDITORARGS)
        return shell_file(None)

if __name__ == '__main__':
    # Initialize config
    configfile = os.path.join(sys.path[0], '{}.conf'.format(NAME))
    settings = EasySettings(configfile)
    settings.name = NAME
    settings.version = VERSION
    # Initialize editor args and cedit args.
    CEDITARGS = None
    EDITORARGS = None
    mainargd = init_args(sys.argv)

    mainret = main(mainargd)
    sys.exit(mainret)
