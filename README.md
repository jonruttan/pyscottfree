# PyScottFree

PyScottFree is a Python program to run Scott Adams databases used primarily
by Adventure International and Brian Howarth. The original version was written
in C by Alan Cox. The current version was translated from C into Python by
Jon Ruttan.

This code has been tested on GNU/Linux and Python2.7 and Python3.5

## Operation

PyScottFree reads and executes TRS80 format Scott Adams datafiles. It is
possible to run other formats either by writing a loader for that format or
a convertor to TRS80 format. Remember the Scott Adams games are still
copyright - you need to buy or obtain the games legally for use with this
interpreter. Some Scott Adams material is available fairly freely . Dec 1980
Byte contains a game driver and also a program to write a version of Pirate
Adventure. A PC-SIG disk contains Adventureland in BASIC with a database in
DATA statements. The file 'Definition' in this archive explains the TRS80
format as I believe it exists. Much of this definition comes from P.D.Doherty
who provided a lot of information.

PyScottFree should run all the Scott Adams, Brian Howarth and some other
Adventure International games. (Gremlins and Supergran have a compressed
action table,  Robin Of Sherwood and Seas Of Blood have both a compressed
action table and compressed text.  Seas Of Blood won't run straight off due
to the bizarre Fighting Fantasy (tm) combat system built into it.)

## Command Options

Usage: `./pyscottfree.py [options] <gamename> [savedgame]`

    Options:
      -h  Print this message and exit
      -y  Generate 'You are', 'You are carrying' type messages for games that
    	  use these instead (eg Robin Of Sherwood)
      -i  Generate 'I am' type messages (default)
      -v  Verbose info on file operations
      -d  Debugging info
      -p  Force lamp destruction when empty
      -s  Generate authentic Scott Adams driver light messages rather than
    	  other driver style ones (Light goes out in %%d turns..)
      -t  Generate TRS80 style display (terminal width is 64 characters; a
    	  line <-----------------> is displayed after the top stuff; objects
    	  have periods after them instead of hyphens
      -w  Wait five seconds before exiting
      -c  Use curses for terminal output
      -r  Randomizer seed


## Original Statement Of Copyright/License

    This software is supplied subject to the GNU software copyleft (version 2)
    available from GNU or for FTP from prep.ai.mit.edu. All material in this
    program was developed by Swansea University Computer Society without
    disassembly of any other game drivers, only of game databases as permitted
    by EEC law (for purposes of compatibility). It is your responsibility not
    to transfer this software to any country where such reverse engineering is
    not permitted. This software license does not include any rights with
    regards to the Scott Adams games themselves. These games are copyright and
    you should obtain them from a legal source.

The following information sources were used to produce the game driver:

- PC-SIG disk of Adventureland:
	This gives the Adventureland database as well as about 80% of the
full interpreter system. The core of the gamedriver was written using this
as a reference to the game code.

- Byte Dec 1980:
	This contains a good article about Scott and his games, as well as
a TRS80 driver and datafile writer for the 'Pirate Adventure' game. This
filled in some more answers as well as bits of the TRS80 data format

- P.D.Doherty:
	Many thanks go to him for figuring out a load more actions, testing,
hunting for games which used unknown actions and for writing a Scott Adams
database to readable text convertor. This helped resolve several other
actions.

## To Do

- Tidy up *TAKE ALL / DROP ALL*. They match the Spectrum version -
	which appears to be buggy. Also note that using *GET ALL / DROP ALL*
	with older games _MAY BREAK THINGS_. Maybe this should be a flagged
	option.

