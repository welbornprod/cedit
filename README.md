# cedit

Basic command-line tool to open files with your favorite editor.
If root permissions are needed to open the file, your favorite elevation command
is used. This way, you will never see another 'no permissions' message again.

If root-permissions are required, your elevation command will ask you for the
password. If they are not required, your editor command will be used alone.

Cedit does not save your password, that wouldn't be very smart.
It only shells your favorite elevation command to allow you to enter your password
before opening the editor.

## Usage:
```
cedit <filename>
	...to open a file.

cedit <file1> <file2>
cedit *.py
    ...to open multiple files manually, or open all .py files using shell expansion.

cedit -l
	...lists current configuration (editor and elevation command)

cedit --set editor=path_to_editor
cedit --set rooteditor=path_to_editor_when_root
cedit --set elevcmd=path_to_elevcmd
	...sets your favorite commands so cedit will remember what to use.
       if the executable is in /usr/bin, you don't have to type the full path.
```

If your favorite editor isn't in the same directory as cedit or /usr/bin, then
you will need to set the editor like this:
```bash
	cedit --set editor=/my/path/to/editor
```
(same for elevcmd)

You can also just edit the `cedit.json` config file.

## Installation:

I recommend creating a symlink to this script somewhere in `$PATH`:
```bash
cd cedit
ln -s "$PWD/cedit.py" ~/.local/bin/cedit
```

With a symlink to `cedit.py` in `$PATH`, you should be able to run
cedit like this from anywhere:
```bash
cedit /root/needs_sudo.txt
```

## With no settings:

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
