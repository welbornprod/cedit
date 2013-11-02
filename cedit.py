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
    They can be set using the 'set' command. (see --help).
    If you are using Python2 the pip command can install requirements, 
    otherwise pip3 or a Python3-compatible package installer should be used.
    
    Requires: easysettings 
                  saves configuration, to install: pip3 install easysettings
              docopt 
                  parses arguments, to install: pip3 install docopt
    
    Installation:
    To install cedit as a global terminal command you can use the 'install' command.
    For installing for a single user run:
        ./cedit.py --install --user
    
    For installing in /usr/bin (for all users) run:
        sudo ./cedit.py --install

    Created on Jan 19, 2013

    Christopher Welborn <cj@welbornprod.com>
"""
# Python2 future print function, Python3 current print function.
from __future__ import print_function
import os
import re
import sys
import subprocess

# enable/disable debug mode
DEBUG = False
# determine python version (for better help on required packages/pip)
PYTHON3 = not sys.version < '3'
# determine input function.
if not PYTHON3:
    input = raw_input

# Current version    
_VERSION = '1.3.0'
_VERSIONMINI = '1'
# Name, also used in creating symlinks in cmd_install()
_NAME = 'cedit'
_SCRIPTFILE = sys.argv[0][2:] if sys.argv[0].startswith('./') else sys.argv[0]
# looks better in help to have the real user name, if not found then just use 'user'
_USER = os.environ.get('USER', 'user')

# Usage string
usage_str = """{name} v.{version} (running on Python {pyversion})

    Usage:
        cedit -h | -a | -v
        cedit <filename>... [options]
        cedit -e path_to_editor | -c path_to_elevcmd
        cedit -i [-u | -p dir]
        cedit -l
        cedit -r
        
    Options:
        -a,--about                      : show message about cedit.
        -c filepath,--elevcmd filepath  : set favorite elevation command, where filepath is the path to your elevation command.
        -d,--debug                      : for development, prints random msgs.
        -e filepath,--editor filepath   : set favorite editor, where filepath is the path to your editor.
        -h,--help                       : show this help message.
        -i,--install                    : install cedit, creates symlink in /usr/local/bin, /usr/bin, or home (see -u and -p)
                                          if /usr/local/bin is found in $PATH, it is used. otherwise /usr/bin is used.
                                          if -u or -p is passed also, the install path is determined by the flag.
                                          cedit will ask for confirmation before installing.
        -l,--list                       : list current cedit settings (editor/elevcmd)
        -p dir,--path dir               : when installing, install to specified directory.
        -r,--remove                     : remove the installed symlink for cedit if installed. (may require permissions)
        -s,--shellall                   : shell one process per file, instead of sending all file names at once.
        -u,--user                       : when installing, only install for user.                                       
                                          $PATH is searched for dirs like /home/{user}/bin.
                                          without $PATH, common dirs are looked for. 
        -v,--version                    : show version.
        filename                        : file to open.
                                         
    Settings:
        editor   : path to favorite editor.
        elevcmd  : path to favorite elevation command.
        
    Example:
        cedit myfile.txt
            ...opens myfile.txt, using elevation command if needed.

        cedit myfile1.txt myfile2.txt
            ...opens both files with your editor, using elevation command if at least 1 file needs it.

        cedit *.py
            ...uses your shells expansion to open all .py files in the current directory.

        cedit --editor gedit
            ...sets favorite editor to 'gedit'

        cedit --elevcmd kdesudo
            ...sets favorite elevation command to 'kdesudo'
            
""".format(name=_NAME, version=_VERSION, pyversion=sys.version.split()[0], user=_USER)


# I hate putting these functions here, but for better help I will.
def cmd_exists(shortname):
    """ Determines if link/alias/shortname of command is available using 'which' command.
        returns True, False
    """

    whichcmd = ['which', shortname]
    retcode = subprocess.call(whichcmd, stdout=subprocess.PIPE)
    return retcode == 0


def get_pip_name():
    """ determine if pip is installed, if it is find whether or not pip3 is installed.
        return string containing desired pip version, or '' if none is found.
    """
    pip3versions = '3', '3.1', '3.2', '3.3'
    pip2versions = '', '2', '2.7'
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
    modulewarning = ['You need to have {propername} installed to use cedit.'.format(propername=importname)]
    if pipver:
        modulewarning.append('To install it run:')
    else:
        # no pip installed
        modulewarning.append('After installing a python-package manager,')
        modulewarning.append('Install the module with:')
    modulewarning.append('{pip} install {pkgname}'.format(pip=pipver,
                                                          pkgname=importname.lower()))
    print('\n'.join(modulewarning))


def warn_pip(importname):
    """ Module couldn't be imported, so show a message about it.
        Also, show a warning about needing pip installed if it isn't already, 
        or having only pip2 installed while using Python3.
        If all pip requirements are met, it doesn't show a warning about it, just the module.
        Returns: True if warning was printed, False if not. (return isn't used right now)
    """

     # Check pip info
    pipname = get_pip_name()
    pipsuggested = 'pip3' if PYTHON3 else 'pip'
    pypkg = 'python-{}'.format(pipsuggested)

    # No pip installed.
    if not pipname:
        print('You don\'t have pip installed, you can install packages using something else if you want,\n' +
              'but I would recommend installing {pippkgver} to get the required packages for cedit.'.format(pippkgver=pypkg))
        warn_module(importname, pipsuggested)
        return True

    if PYTHON3:
        ver = '3'
        noversionokay = False
    else:
        ver = '2'
        noversionokay = True
    pyver = 'Python{}'.format(ver)

    if not ver in pipname and (not noversionokay):
        print('You have \'pip\' installed, but it doesn\'t look like a {pyver}-compatible version.\n'.format(pyver=pyver) +
              'You may need to install {pippkgver} (if \'pip\' already points to a valid version ignore this.)'.format(pippkgver=pypkg))
        warn_module(importname, pipname)
        return True

    # No warnings were shown.
    warn_module(importname, pipname)
    return False


# Try importing EasySettings, I doubt that anyone has this installed yet.
try:
    from easysettings import easysettings
except ImportError as ex_es:
    warn_pip('EasySettings')
    sys.exit(1)
# Try importing Docopt, I doubt that anyone has this either.
try:
    from docopt import docopt
except ImportError as ex_es:
    warn_pip('Docopt')
    sys.exit(1)


def can_write(filename):
    """ checks for write access on a file. """
 
    return (os.access(filename, os.W_OK))


def check_file(filename):
    """ checks if a file exists, if not asks user if we should continue.
        returns True if user says yes, otherwise False.
    """
    
    if os.path.isfile(filename):
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
    # All existed, or all were created.
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


def cmd_list():
    """ list command. """
    
    alloptions = settings.list_options()
    if not alloptions:
        print('no settings yet.\nuse cedit -e (or -c) to set your favorite editor or elevation command.')
        return 1

    namelengths = [len(o) for o in alloptions]
    longestnamelen = max(namelengths)

    # print current settings   
    print('current settings:')
    for optname in alloptions:
        val = settings.get(optname)
        if not val:
            val = '(not set yet!)'
        spacinglen = (longestnamelen - len(optname)) + 1
        spacing = (' ' * spacinglen)
        print('  {}{}: {}'.format(optname, spacing, val))
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
            print('not a directory: ' + location + '\n' +
                  'create the directory and try again.\n' +
                  'also make sure the directory is included in your PATH environment variable.\n' +
                  'otherwise, the symlink won\'t work.')
            return 1
    else:
        # Global
        if check_path('/usr/local/bin') and os.path.isdir('/usr/local/bin'):
            location = '/usr/local/bin'
        else:
            location = '/usr/bin'

    # already installed?
    finalname = os.path.join(location, _NAME)
    installedloc = cmd_location(_NAME)
    if not installedloc:
        # Try full path.
        installedloc = cmd_location(finalname)
    if installedloc:
        print('it seems that cedit is already installed at: ' + installedloc + '\n' +
              'you will need to remove it if you want to re-install cedit.\n')
        return 1

    # Confirm installation.
    doinstall = input('cedit will install to: {}\ncontinue with installation? (yes/no): '.format(location))
    if not doinstall.lower().strip().strip('\t').startswith('y'):
        print('\ninstallation canceled.\n')
        return 1

    # Try Installation.
    try:
        print('trying to create symlink in: ' + location)
        os.symlink(scriptfile, finalname)
        print('success!\n' +
              '...you may have to restart your terminal to use the command \'' + _NAME + '\'')
    except OSError as exos:
        print('error:\n' + str(exos) + '\n\n' +
              'try running \'cedit install\' as root for global installation.\n' +
              'example: sudo cedit install\n')
        return 1
    except Exception as ex:
        print('unable to create symlink with: ' + finalname + '\n' + str(ex))
        return 1
    
    return 0


def cmd_remove():
    """ Trys to uninstall/remove the cedit symlink (if any exists) """

    loc = cmd_location(_NAME)
    if not loc:
        print('\ncan\'t finc {} installed anywhere.\n'.format(_NAME))
        return 1

    # Confirm removal.
    doremove = input('this will remove {} from: {}\n'.format(_NAME, loc) +
                     'you will need to have the permissions required to do this.\n' +
                     '\ncontinue with removal? (yes/no): ')
    if not doremove.lower().strip().strip('\t').startswith('y'):
        print('\nremoval canceled.\n')
        return 1

    # Try removing it.
    try:
        os.remove(loc)
    except OSError as exos:
        print('\nunable to remove {}!:\n{}'.format(_NAME, exos))
        return 1

    # Success.
    print('\n{} was successfully removed from: {}\n'.format(_NAME, loc))
    return 0


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
 

def get_editor():
    if not settings.get('editor', ''):
        # no editor set
        print('Be sure to set your favorite editor with: cedit --editor path_to_editor')
        # look for common editor
        lst_editors = ['kate', 'gedit', 'leafpad', 'kwrite']
        for editor in lst_editors:
            spath = os.path.join('/usr/bin/', editor)
            if os.path.isfile(spath) or os.path.islink(spath):
                print('Found common editor: ' + spath)
                return spath
        print('No common editors found! You must set one using the above command.')
        sys.exit(1)
    else:
        editor = settings.get('editor')
        if os.path.isfile(editor) or os.path.islink(editor):
            return editor
        else:
            # try /usr/bin
            spath = os.path.join('/usr/bin', editor)
            if os.path.isfile(spath) or os.path.islink(spath):
                return spath
        print('Cannot find editor! Make sure you set a valid editor with:\n' +
              'cedit set editor=[editor or /path/to/editor]')
        sys.exit(1)

        
def get_elevcmd():
    if not settings.get('elevcmd', ''):
        # no editor set
        print('Be sure to set your favorite elevation command with: cedit --elevcmd path_to_elevation_command')
        # look for common elevation command
        lst_elevs = ['kdesudo', 'gksudo', 'sudo']
        for elevcmd in lst_elevs:
            spath = os.path.join('/usr/bin/', elevcmd)
            if os.path.isfile(spath) or os.path.islink(spath):
                print('Found common elevation cmd: ' + spath)
                return spath
        print('No common elevation commands found! You must set one using the above command.')
        sys.exit(1)
    else:
        elevcmd = settings.get('elevcmd')
        if os.path.isfile(elevcmd) or os.path.islink(elevcmd):
            return elevcmd
        else:
            # try /usr/bin
            spath = os.path.join('/usr/bin', elevcmd)
            if os.path.isfile(spath) or os.path.islink(spath):
                return spath
        print('Cannot find elevcmd! Make sure you set a valid elevation command with:\n' +
              'cedit set elevcmd=[elevcmd or /path/to/elevcmd]')
        sys.exit(1)


def good_return(returnvalue):
    """ Just returns True if returnvalue == 0, used in list comprehension in main() """
    goodret = True if returnvalue == 0 else False
    return goodret


def needs_root(sfilename):
    try:
        # already root user
        if os.getuid() == 0:
            return False
        # file is owned by root.
        if (os.stat(sfilename).st_uid == 0):
            print_debug('os.stat said root.')
            return True
        else:
            # check files that aren't owned by root.
            # we may not be able to write to them.
            c_w = can_write(sfilename)
            print_debug('os.stat said not root, can_write=' + str(c_w))
            return (not c_w)
    except OSError:
        return True
    except Exception as ex:
        print('needs_root(): Error: \n' + str(ex))
        # i dunno.
        return True


def print_debug(s):
    if DEBUG: 
        print('DEBUG: ' + s)

    
def printdict(dict_):
    print(str(dict_).replace(',', '\n').strip('{').strip('}'))

             
def run_exec(cmdlist):
    # runs a command with arguments.
    if hasattr(cmdlist, 'lower'):
        # string was passed? but why?
        cmdlist = cmdlist.split(' ')

    try:
        # use subprocess so cedit can return control to the user.
        ret = subprocess.Popen(cmdlist)
    except:
        try:
            # try system-command method. (does not return control)
            ret = os.system(' '.join(cmdlist))
        except Exception as ex:
            raise Exception(ex)
        
    return ret


def set_setting_safe(opt, val):
    """ Sets a setting, but not if its already set to the same thing,
        and not if the value (which is a filepath to editor/elevcmd) doesn't exist.
    """
    oldval = settings.get(opt)
    if oldval == val:
        print('\n{} is already set to \'{}\''.format(opt, oldval))
        return 1

    if not os.path.isfile(val):
        val = os.path.join('/usr/bin', val)
        if not os.path.isfile(val):
            print('\nthat {} doesn\'t exist!: {}'.format(opt, val))
            return 1

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
    editor = get_editor()
    if (not editor.startswith('/')) and (not os.path.isfile(editor)):
        # try /usr/bin... (location for most popular editors)
        editor = '/usr/bin/' + editor
    if not os.path.isfile(editor):
        print('Editor not found!: ' + editor)
        return 1   
    print('Using editor: ' + editor)

    # Start building command args.
    finalcmd = [editor]
    # See if it needs root.
    for filename in filenames:
        if needs_root(filename):
            # root style.
            elevcmd = get_elevcmd()
            finalcmd.insert(0, elevcmd)
            print('Using elevation command: {}\nFile needs root: {}\n'.format(elevcmd, filename))
            break
    # Append list of filenames.
    finalcmd = finalcmd + filenames
    cmdstr = ' '.join(finalcmd)
    try:
        # try running
        run_exec(finalcmd)
        print('Ran: {}'.format(cmdstr))
    except Exception as ex:
        print('Unable to run command: {}'.format(cmdstr))
        print('Error:\n{}'.format(str(ex)))
        return 1
    return 0


# MAIN ----
def main(argd):
    """ Main entry point for cedit.
        Expects docopt argument dict.
    """
   
    # show about message?
    if argd['--about']:
        print(__doc__)
        return 0
    # show version?
    elif argd['--version']:
        print(_NAME + ' version ' + _VERSION)
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
    if not filenames:
        print('No file to open!')
        return 1
        
    # Open files separately (where some stupid editors don't support multi-file opening.)
    if argd['--shellall']:
        returns = []
        for filename in filenames:
            if check_file(filename):
                returns.append(good_return(shell_file([filename])))
            else:
                returns.append(1)
        return 0 if all(returns) else 1

    # Send all file names to one process.
    if check_files(filenames):
        return shell_file(filenames)


if __name__ == '__main__':
    mainargd = docopt(usage_str, version='cedit v. {}'.format(_VERSION))
    # Initialize config
    settings = easysettings.easysettings(os.path.join(sys.path[0], 'cedit.conf'))
    settings.name = 'cedit'
    settings.version = _VERSION
    mainret = main(mainargd)
    sys.exit(mainret)
