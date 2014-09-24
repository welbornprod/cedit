cedit
=====

Basic command-line tool to open files with your favorite editor.
If root permissions are needed to open the file, your favorite elevation command
is used. This way, you will never see another 'no permissions' message again.

If root-permissions are required, your elevation command will ask you for the
password. If they are not required, your editor command will be used alone.

Cedit does not save your password, that wouldn't be very smart.
It only shells your favorite elevation command to allow you to enter your password
before opening the editor.

(something i always forgot to do before using cedit :P)


Usage:
------

	cedit <filename>
		...to open a file.

    cedit <file1> <file2>
    cedit *.py
        ...to open multiple files manually, or open all .py files using shell expansion.

	cedit -l
		...lists current configuration (editor and elevation command)

	cedit --editor path_to_editor
	cedit --elevcmd path_to_elevcmd
		...sets your favorite commands so cedit will remember what to use.
           short options also available (-e, and -c).
           if the executable is in /usr/bin, you don't have to type the full path.


If your favorite editor isn't in the same directory as cedit or /usr/bin, then
you will need to set the editor like this:

	cedit --editor /my/path/to/editor
	(same for --elevcmd)


Installation:
-------------

You can create a symlink to the cedit.py script yourself, or you can use the builtin 'install' command.

To install cedit in /usr/local/bin or /usr/bin (for all users) run:

    sudo ./cedit.py -i
    or: sudo ./cedit.py --install

    ** cedit will search $PATH and if /usr/local/bin is found (and exists as a dir) then it is used.
    ** otherwise, /usr/bin is used.


To install cedit for a single user run:

    ./cedit.py -i -u
    or: ./cedit.py --install --user

    ** this will try to install cedit to /home/USERNAME/bin, ../local/bin, ../.local/bin
    ** or whatever /home/USERNAME/???/bin that is found in $PATH.
    ** first valid and existing dir found is used.


To specify where to install cedit:

    ./cedit.py --install --path /my/path/for/cedit

    ** this must be an existing directory, and you must have the required permissions to
    ** create a symlink there.


If everything went well, or you manually created the symlink yourself, you should be able to run
cedit like this from anywhere:

    cedit /root/needs_sudo.txt


With no settings:
-----------------

If no settings are set, cedit will try to look for a few 'popular' commands to
work with.

cedit will look for these editors if your favorite isn't set:

* subl
* kate
* gedit
* leafpad
* kwrite

cedit will look for these elevation commands if your favorite isn't set:

* kdesudo
* gksudo
* sudo

Without any settings, if you have both `kate` and `kdesudo` installed, cedit will
open your 'root-permissions' file by running: `kdesudo kate <filename>`
If the file doesn't require root permissions then just: `kate <filename>`


Changes:
--------

Version 1.3.0:
    Added better installer options (more global dirs, $PATH search for good dir for symlinks)
    Added --remove (uninstaller) (removes the cedit symlink)

Version 1.2.2:
    Changed flags used when setting options, code is clearer.
    Added more help for when required modules aren't installed. (better messages)
    Added multi-file ability (something 1.0 should've had to begin with.)
    ...if your favorite editor doesn't support multi-files like "file1 file2 file3",
       you can use --shellall and a new process will be shelled for each file.
       (most editors will at least group them in the same window, if not you will
        have multiple windows opened.)


Bug Fixes:
----------

Fixed stupid error where `needs_root()` returned `can_write()` instead of
`needs_root() = (not can_write())`. My bad.


Future:
-------

There may be plans to allow different editors to be chosen for different file-types.
Right now cedit works as expected, as long as you only use one editor most often.
I may add the ability to set favorite editors for favorite file-types like:

	cedit --set .py,geany



