#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
    cedit.py
    Designed to open files with your favorite editor while using your favorite
    elevation command when needed for permissions.
    Keeps you from seeing 'no permissions' messages, and instead asks you
    for your password.
    If no 'favorites' are set yet, cedit will look for 'popular' editors and
    elevation commands. It will use the first one found.
    If none of the 'popular' commands are found, you have to set your own.
    They can be set using the 'set' command. (see --help).
    
    Requires: easysettings 
                  saves configuration, to install: pip install easysettings
              docopt 
                  parses arguments, to install: pip install docopt
    
    Installation:
    To install cedit as a global terminal command you can use the 'install' command.
    For installing for a single user run:
        ./cedit.py install user
    
    For installing in /usr/bin (for all users) run:
        sudo ./cedit.py install

    Created on Jan 19, 2013

    Christopher Welborn <cj@welbornprod.com>
'''
from __future__ import print_function
import os, os.path, sys
import subprocess

# enable/disable debug mode
DEBUG = True
import_failmsg =  "You need to have {0} installed to use this program.\n" + \
                  "To install {0} run the command:\n" + \
                  "pip install {1}\n"   
# Try importing EasySettings, I doubt that anyone has this installed yet.
try:
    from easysettings import easysettings
except ImportError as ex_es:
    print(import_failmsg.format("EasySettings", "easysettings"))
    sys.exit(1)
# Try importing Docopt, I doubt that anyone has this either.
try:
    from docopt import docopt
except ImportError as ex_es:
    print(import_failmsg.format("Docopt", "docopt"))
    sys.exit(1)

# Current version    
_VERSION = "1.1.2"
_NAME = 'cedit'
_SCRIPTFILE = sys.argv[0][2:] if sys.argv[0].startswith('./') else sys.argv[0]


# Usage string
usage_str = """{{NAME}} v.{{VERSION}}

    Usage:
        cedit -h | -a | -v
        cedit <filename> [options]
        cedit <command> <commandargs>... [options]
        
    Options:
        -h,--help     : show this help message.
        -a,--about    : show message about cedit.
        -v,--version  : show version.
        -d,--debug    : for development, prints random msgs.
        filename      : file to open.
        command       : which command to run.
        commandargs   : arguments for the command.
        
    Commands:
        set <setting> <value>  : set a setting's value.
        list                   : list all current settings.
        install [user]         : installs a symlink to this script in /usr/bin
                                 if 'user' is given, it will try to install in:
                                 /home/USERNAME/.local/bin
                                 
    Settings:
        editor   : path to favorite editor.
        elevcmd  : path to favorite elevation command.
        
    Example:
        cedit myfile.txt
            ...opens myfile.txt, using elevation command if needed.

        cedit set editor gedit
            ...sets favorite editor to 'gedit'

        cedit set elevcmd kdsudo
            ...sets favorite elevation command to 'kdsudo'
            
""".replace("{{NAME}}", _NAME).replace("{{VERSION}}", _VERSION)

# Initialize config
settings = easysettings.easysettings(os.path.join(sys.path[0], "cedit.conf"))
settings.name = "cedit"
settings.version = _VERSION

# stupid trick to fix docopt thinking these are filenames.
short_commands = ("list", "set", "install")
# only allow these options to be written to config.
good_options = ("editor", "elevcmd")

def main(dargs):
    """ Main entry point for cedit.
        Expects docopt argument dict.
    """

    filename = dargs['<filename>']
    
    # show about message?
    if dargs['--about']:
        print(__doc__)
        return 0
    # show version?
    elif dargs['--version']:
        print(_NAME + " version " + _VERSION)
        return 0
    
    # catch short commands.
    if filename in short_commands:
        return do_command(filename, args=None)
    
    # catch commands
    elif dargs['<command>'] is not None:
        return do_command(dargs['<command>'], args=dargs['<commandargs>'])
    
    # opening file.
    elif filename is None:
        print("No file name to open!")
        return 1
    # Open it.
    if check_file(filename):
        return shell_file(filename)
    else:
        return 1

def do_command(cmdname, args=None):
    cmdname = cmdname.lower()
    if cmdname == 'list':
        cmd_list()
    elif cmdname == 'set':
        return cmd_set(args)
    elif cmdname == 'install':
        if args is None:
            installtype = None
        else:
            installtype = args[0].lower()
            if installtype.lower() == 'global':
                installtype = None
            else:
                if installtype not in ("global", "user"):
                    print("unknown install type!: " + installtype + '\n' + \
                      "expecting: user or global\n")
                    return 1
        return cmd_install(installtype)
    else:
        print("cedit command not found: " + cmdname)
        return 1
    return 0

def parse_set(values):
    """ parses command args for set command. catches the use of '='. """
    
    if values is None: return None
    argcount_msg = " arguments for 'set' command.\n" + \
                   "proper usage is: cedit set setting value\n" + \
                   "or: cedit set setting=value\n"
    if len(values) == 1:
        if '=' in values[0]:
            values = values[0].split('=')
    # try fixed values again, or normal values for the first time.
    if len(values) < 2:
        print("\nnot enough" + argcount_msg)
        sys.exit(1)
    elif len(values) > 2:
        print("\ntoo many" + argcount_msg)
        sys.exit(1)
    
    return values

def cmd_set(options):
    """ set an option. """
    values = parse_set(options)
    if values[0].lower() not in good_options:
        print("not a valid option!: " + values[0])
        print("expecting one of:\n    " + '\n    '.join(good_options) + '\n')
        return 1
    oldsetting = settings.get(values[0].lower(), default=None)
    if oldsetting == values[1]:
        print(values[0].lower() + " already set to " + values[1] + '\n')
        return 1
    settings.setsave(values[0].lower(), values[1])
    print("set " + values[0] + " to " + values[1] + '\n')
    return 0

def cmd_list():
    """ list command. """
    
    currentsettings = settings.list_settings()
    if len(currentsettings) == 0:
        # no settings
        print("no settings yet.\n" + \
              "use 'cedit set' to set your favorite editor or elevation command.")
    else:
        # print current settings   
        print("current settings:")
        for setting_ in currentsettings:
            print('    ' + setting_.replace('=', ' : '))
            

def cmd_install(installtype):
    """ installs cedit globally by default,
        passing 'user'  will try to install for only this user.
    """
    scriptfile = os.path.realpath(__file__)
    if installtype is None:
        # global install  
        location = '/usr/bin'

    else:
        # local install
        uname = get_username()
        if uname is None:
            print("unable to find user name!\n" + \
                  "create a symlink from this file to your user directory.\n" + \
                  "ln -s " + scriptfile + " /home/YOURNAME/.local/bin\n" + \
                  "** make sure your home/bin is in the PATH environment variable.\n" + \
                  "   put 'PATH=/home/YOURNAME/.local/bin:$PATH' in bashrc or .profile.\n" + \
                  "   make sure path is exported with: export PATH\n")
            return 1
        location = '/home/' + uname + '/.local/bin'

        if not os.path.isdir(location):
            print("not a directory: " + location + '\n' + \
                  "create the directory and try again.\n" + \
                  "make sure the directory is included in your PATH environment variable.\n")
            return 1
    
    # already installed?    
    filename = os.path.join(location, _NAME)
    from commands import getoutput
    installed_loc = getoutput('which ' + _NAME)
    
    if installed_loc != '':
        print("it seems that cedit is already installed at: " + installed_loc + '\n' + \
              "you will need to remove it if you want to re-install cedit.\n")
        return 1
    try:
        print("trying to create symlink in: " + location)
        os.symlink(scriptfile, filename)
        print("success!\n" + \
              "...you may have to restart your terminal to use the command '" + _NAME + "'")
    except OSError as exos:
        print("error:\n" + str(exos) + '\n\n' + \
              "try running 'cedit install' as root for global installation.\n" + \
              "example: sudo cedit install\n")
        return 1
    except Exception as ex:
        print("unable to create symlink with: " + filename + '\n' + str(ex))
        return 1
    
    return 0

def get_username():
    """ trys several different ways to get user name """
    
    uname = os.environ.get("USER", None)
    if uname is None:
        uname = os.environ.get("LOGNAME", None)
        if uname is None:
            uname = os.environ.get("HOME", None)
            if uname is not None:
                uname = os.path.split(uname)[1]
    return uname
 

def get_editor():
    if settings.get('editor') == "":
        # no editor set
        print("Be sure to set your favorite editor with: cedit set editor=[editor]")
        # look for common editor
        lst_editors = ['kate', 'gedit', 'leafpad', 'kwrite']
        for editor in lst_editors:
            spath = os.path.join('/usr/bin/', editor)
            if os.path.isfile(spath) or os.path.islink(spath):
                print("Found common editor: " + spath)
                return spath
        print("No common editors found! You must set one using the above command.")
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
        print("Cannot find editor! Make sure you set a valid editor with:\n" + \
              "cedit set editor=[editor or /path/to/editor]")
        sys.exit(1)
        
def get_elevcmd():
    if settings.get('elevcmd') == "":
        # no editor set
        print("Be sure to set your favorite elevation command with: cedit set elevcmd=[elevation command]")
        # look for common elevation command
        lst_elevs = ['kdesudo', 'gksudo', 'sudo']
        for elevcmd in lst_elevs:
            spath = os.path.join('/usr/bin/', elevcmd)
            if os.path.isfile(spath) or os.path.islink(spath):
                print("Found common elevation cmd: " + spath)
                return spath
        print("No common elevation commands found! You must set one using the above command.")
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
        print("Cannot find elevcmd! Make sure you set a valid elevation command with:\n" + \
              "cedit set elevcmd=[elevcmd or /path/to/elevcmd]")
        sys.exit(1)

            
def needs_root(sfilename):
    try:
        if (os.stat(sfilename).st_uid == 0):
            print_debug("os.stat said root.")
            return True
        else:
            # check files that aren't owned by root.
            # we may not be able to write to them.
            c_w = can_write(sfilename)
            print_debug("os.stat said not root, can_write=" + str(c_w))
            return (not c_w)
    except OSError as exos: #@UnusedVariable: exos
        return True
    except Exception as ex:
        print("needs_root(): Error: \n" + str(ex))
        # i dunno.
        return True

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
        print("file does not exist!: " + filename)
        print("\nsome editors will automatically create this file...")
        response = raw_input("would you like to continue anyway? (y/n): ")
        return (response.lower().strip(' ').strip('\t').startswith('y'))
    
def shell_file(sfilename):
    editor = get_editor()
    if (not editor.startswith("/")) and (not os.path.isfile(editor)):
        # try /usr/bin... (location for most popular editors)
        editor = "/usr/bin/" + editor
    if not os.path.isfile(editor):
        print("Editor not found!: " + editor)
        return 1
       
    print("Using editor: " + editor)
    if needs_root(sfilename):
        # root style.
        elevcmd = get_elevcmd()
        cmd = [elevcmd, editor, sfilename]
        print("Using elevation command: " + elevcmd)
    else:
        # normal style, no root.
        cmd = [editor, sfilename]
    try:
        # try running
        run_exec(cmd)
        print("Ran " + ' '.join(cmd))
    except Exception as ex:
        print("Unable to run command: " + str(' '.join(cmd)))
        print("Error:\n" + str(ex))
        return 1
    return 0

def run_exec(cmdlist):
    # runs a command with arguments.
    #os.system(' '.join(cmdlist))
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


def print_debug(s):
    if DEBUG: print("DEBUG: " + s)
    
def printdict(dict_):
    print(str(dict_).replace(',','\n').strip('{').strip('}'))

             
if __name__ == '__main__':
    dargs = docopt(usage_str)

    ret = main(dargs)
    sys.exit(ret)
        
            