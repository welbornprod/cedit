cedit
=====

Basic command-line tool to open files with your favorite editor.
If root permissions are needed to open the file, your favorite elevation command
is used. This way, you will never see another 'no permissions' message again.

If root-permissions are required, your elevation command will ask you for the 
password. If they are not required, your editor command will be used alone.


Usage:
------
	
	cedit <filename>
		...to open a file.
	
	cedit list
		...lists current configuration (editor and elevation command)
		
	cedit set editor=[your editor command]
	cedit set elevcmd=[your elevation command]
		...sets your favorite commands so cedit will remember what to use.

If you favorite editor isn't in the same directory as cedit or /usr/bin, then
you will need to set the editor like this:

	cedit set editor=/my/path/to/myeditor
	
	
With no settings:
-----------------

If no settings are set, cedit will try to look for a few 'popular' commands to
work with. 

cedit will look for these editors if your favorite isn't set:
	kate
	gedit
	leafpad
	kwrite

cedit will look for these elevation commands if your favorite isn't set:
	kdesudo
	gksudo
	sudo

Without any settings, if you have both `kate` and `kdesudo` installed, cedit will
open your 'root-permissions' file by running: `kdesudo kate <filename>`
If the file doesn't require root permissions then just: `kate <filename>`

Future:
-------

There may be plans to allow different editors to be chosen for different file-types.
Right now cedit works as expected, as long as you only use one editor most often.
I may add the ability to set favorite editors for favorite file-types like:

	cedit set .py=geany


	
