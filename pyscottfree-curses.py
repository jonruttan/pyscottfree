#!/usr/bin/env python
#
#	PyScottFree
#
#	A free Scott Adams style adventure interpreter
#
#	Copyright:
#		This software is placed under the GNU license.
#
#	Statement:
#		Everything in this program has been deduced or obtained solely
#	from published material. No game interpreter code has been
#	disassembled, only published BASIC sources (PC-SIG, and Byte Dec
#	1980) have been used.
#
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License
#	as published by the Free Software Foundation; either version
#	2 of the License, or (at your option) any later version.
#

__author__ = 'Jon Ruttan'
__copyright__ = 'Copyright (C) 2010 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.1.3'

from pyscottfree import Saga, wrap_str, main

import sys
import curses
import signal

class CursesSaga(Saga):
	def __init__(self, options=0, seed=None, name=None, file=None, greet=True):
		curses_up = False			# Curses up

		Saga.__init__(self, options, seed, name, file, False)

		self.win = [None, None]
		self.win_height = (10, 14)		# Height of the curses windows

		curses.initscr()
		self.curses = True

		signal.signal(signal.SIGINT, self.aborted)	# For curses
		signal.signal(signal.SIGQUIT, signal.SIG_IGN)
		signal.signal(signal.SIGTSTP, signal.SIG_IGN)


		self.win[0] = curses.newwin(self.win_height[0], self.width, 0, 0)
		self.win[1] = curses.newwin(self.win_height[1], self.width, self.win_height[0], 0)
		self.win[0].leaveok(True)
		self.win[1].scrollok(True)
		self.win[1].leaveok(False)
		self.win[1].idlok(True)
		curses.noecho()
		curses.cbreak()
		self.win[1].move(self.win_height[1] -1, 0)
		self.output(self.greeting())

	def aborted(self, signum, frame):
		self.exit(1, '\nUser exit\n')

	def exit(self, errno = 0, str = None):
		if self.curses:
			curses.nocbreak()
			curses.echo()
			curses.endwin()
			self.curses = False

		Saga.exit(self, errno, str)

	def clear_screen(self):
		Saga.clear_screen(self)
		for win in self.win:
			win.erase()


	def output_reset(self, win=1, scroll=False):
		Saga.output_reset(self, win, scroll)
		if scroll:
			self.win[win].scroll
		self.win[win].move(self.win_height[win] -1, 0)
		self.win[win].clrtoeol()

	def curses_addstr(self, str, win=1):
		try:
			self.win[win].addstr(str)
		except curses.error:
			pass

	def output(self, str, win=1, scroll=True, wrap=True):
		if wrap is True:
			wrap = self.width -2

		if wrap:
			lines = wrap_str(str, wrap).split('\n')

			for line in lines[:-1]:
				self.curses_addstr(line + '\n', win)
				if scroll:
					self.output_reset(win, True)

			self.curses_addstr(lines[-1], win)
		else:
			self.curses_addstr(str, win)

		self.win[win].refresh()

	def input(self, str='', win=1):
		self.output(str, win, False)
		curses.doupdate()
		curses.echo()
		str = self.win[win].getstr()
		curses.noecho()
		self.output_reset()

		return str.strip()

	def look(self):
		self.win[0].erase()
		self.win[0].move(0, 0)
		Saga.look(self)


if __name__ == '__main__':
	main(sys.argv, CursesSaga)
