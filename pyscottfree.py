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

# Todo:
#	More debugging, improve debugging formatting
#	Test availability of imported modules
#	Licensing
#	Remove vestigal code
#	Comment cleanup
#	Release

__author__ = 'Jon Ruttan'
__copyright__ = 'Copyright (C) 2010 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.7.0'

import sys
import os
import signal
import time
import random
import getopt
import curses

LOC_DESTROYED = 0				# Destroyed
LOC_CARRIED = 255				# Carried

ITEM_LIGHT = 9					# Always 9 how odd

FLAG_YOUARE = 0x1				# You are not I am
FLAG_SCOTTLIGHT = 0x2			# Authentic Scott Adams light messages
FLAG_TRS80_STYLE = 0x4			# Display in style used on TRS-80
FLAG_PREHISTORIC_LAMP = 0x8		# Destroy the lamp (very old databases)
FLAG_USE_CURSES = 0x10			# Uses curses terminal output
FLAG_WAIT_ON_EXIT = 0x20		# Wait before exiting
FLAG_VERBOSE = 0x40				# Info from load/save
FLAG_DEBUGGING = 0x80			# Debugging info

FLAG_DARK = 0x8000
FLAG_LIGHT_OUT = 0x10000		# Light gone out

ENV_FILE = 'SCOTTFREE_PATH'
ENV_SAVE = 'SCOTTFREE_SAVE'
DIR_SAVE = '~/.scottfree'

curses_up = False			# Curses up

def end_curses():
	if curses_up:
		curses.nocbreak()
		curses.echo()
		curses.endwin()

def exit(errno = 0, errstr = None):
	end_curses()

	if errstr != None:
		sys.stderr.write(errstr)

	sys.exit(errno)

def fatal(str):
	exit(1, '\n{0}.\n'.format(str))

def aborted(signum, frame):
	fatal('User exit')

signal.signal(signal.SIGINT, aborted)	# For curses
signal.signal(signal.SIGQUIT, signal.SIG_IGN)
signal.signal(signal.SIGTSTP, signal.SIG_IGN)

def random_percent(n):
	return random.randint(0, 99) < n

def read_next_item(file, quote = None, type = None, bytes = 1):
	while not len(read_next_item.string):
		# Read in the next line and strip the whitespace
		read_next_item.string = file.readline().strip()

	if quote != None:
		# If the string doesn't start with a quote, complain and exit
		if not read_next_item.string.startswith(quote):
			fatal('Initial quote({0}) expected -- {1}'.format(quote, read_next_item.string))

		while True:
			end = read_next_item.string[1:].find(quote)
			# If the string doesn't end with a quote, complain and exit
			if end == -1:
				read_next_item.string += '\n' + file.readline().strip()
			else:
				end += 2
				break

		string = read_next_item.string[:end].strip('"').replace('`', '"')

	else:
		end = read_next_item.string.find(' ')
		if end == -1:
			end = len(read_next_item.string)

		string = read_next_item.string[:end]

#		if string == '-1':
#			string = (1 << (bytes << 3)) -1

		if string == str((1 << (bytes << 3)) -1):
			string = '-1'

	read_next_item.string = read_next_item.string[end+1:]

	return string

read_next_item.string = ''

def read_number(file, bytes = 1):
	return int(read_next_item(file))

def read_string(file):
	return read_next_item(file, '"')

# From http://code.activestate.com/recipes/148061/
def wrap_str(text, width = 80):
	'''
	A word-wrap function that preserves existing line breaks
	and most spaces in the text. Expects that existing line
	breaks are posix newlines (\n).
	'''
	return reduce(lambda line, word, width=width: '{0}{1}{2}' \
			.format(line, ' \n'[(len(line)-line.rfind('\n')-1
					+ len(word.split('\n',1)[0]) >= width)], word),
			str(text).split(' '))

class Action:
	def __init__(self):
		self.vocab = None
		self.condition = [None] * 5
		self.action = [None] * 2

	def read(self, file):
		self.vocab = read_number(file)
		self.condition = [read_number(file) for i in range(0, 5)]
		self.action = [read_number(file) for i in range(0, 2)]

	def to_string(self):
		return 'Action(Vocab: {0:d}, Condition: {1}, Action: {2})'.format( \
				self.vocab, \
				self.condition, \
				self.action \
		)

class Room:
	def __init__(self):
		self.text = None
		self.exits = [None] * 6

	def read(self, file):
		self.exits = [read_number(file) for i in range(0, 6)]
		self.text = read_string(file)

	def to_string(self):
		return 'Room(Text: {0}, Exits: {1})'.format( \
				self.text, \
				self.exits \
		)

class Item:
	def __init__(self):
		self.text = None
		self.location = None
		self.initial_loc = None
		self.auto_get = None

	def read(self, file):
		words = read_string(file).split('/')
		self.text = words[0]

		# Some games use // to mean no auto get/drop word!
		if len(words) > 1 and len(words[1]) and not words[1][1] in ('/', '*'):
			self.auto_get = words[1]
		else:
			self.auto_get = ''

		self.initial_loc = self.location = read_number(file)

	def to_string(self):
		return 'Item(Text: "{0}", Location: {1}, Initial Location: {2}, Auto Get: {3})'.format( \
				self.text, \
				self.location, \
				self.initial_loc, \
				self.auto_get, \
		)

class Tail:
	def __init__(self):
		self.version = None
		self.adventure_number = None
		self.unknown = None

class Saga:
	def __init__(self, filename = None, options = None, seed = None):
		self.filepath = None
		self.filename = None
		self.savepath = None
		self.savename = None

		# From Header
		self.unknown1 = None
		self.max_carry = None
		self.player_room = None
		self.treasures = None
		self.word_length = None
		self.time_light = None
		self.treasure_room = None

		# From GameTail
		self.version = None
		self.adventure = None
		self.unknown2 = None

		# State
		self.items = None
		self.verbs = None
		self.nouns = None
		self.messages = None
		self.actions = None
		self.light_refill = None
		self.noun_text = None
		self.counters = [0] * 16		# Range unknown
		self.current_counter = 0
		self.saved_room = 0
		self.room_saved = [0] * 16		# Range unknown
		self.options = options			# Options flags set
		self.bit_flags = 0
		self.redraw = False			# Update item window
		self.width = 80					# 80 column display

		# For curses
		self.win = [None, None]
		self.win_height = (10, 14)		# Height of the curses windows

		if options != None:
			# Terminal width
			if options & FLAG_TRS80_STYLE:
				self.width = 64
				self.win_height = (11, 13)

			if options & FLAG_USE_CURSES:
				curses.initscr()
				globals()['curses_up'] = True
				self.win[0] = curses.newwin(self.win_height[0], self.width, 0, 0)
				self.win[1] = curses.newwin(self.win_height[1], self.width, self.win_height[0], 0)
				self.win[0].leaveok(True)
				self.win[1].scrollok(True)
				self.win[1].leaveok(False)
				self.win[1].idlok(True)
				curses.noecho()
				curses.cbreak()
				self.win[1].move(self.win_height[1] -1, 0)

		self.last_synonym = None

		self.shortforms = {
			'n': 'north', 'e': 'east',
			's': 'south', 'w': 'west',
			'u': 'up', 'd': 'down',
			# Brian Howarth interpreter also supports this
			'i': 'inventory'
		}
		self.strings = {
			# Names used for direction labels
			'exit names': ['North', 'South', 'East', 'West', 'Up', 'Down' ],

			# Separator used for lists; second entry tied to FLAG_TRS80_STYLE flag
			'list separator': [' - ', '. '],

			# Light out message; second entry tied to FLAG_SCOTTLIGHT flag
			'light out': ['Your light has run out. ', 'Light has run out! '],

			# Perform action responses
			'perform_actions': [
				"I don't understand your command. ",
				"I can't do that yet. "
			],

			# Rest of list is messages; second entry tied to FLAG_YOUARE flag
			'trs80 line': '\n<------------------------------------------------------------>\n',
			'none': 'none',
			'file error': "Can't open '{0}'",
			'too dark': ["I can't see. It is too dark!", "You can't see. It is too dark!"],
			'look': ["I'm in a {0}\n", "You are {0}\n"],
			'exits': "\nObvious exits: {0}.\n\n",
			'also see': ["I can also see: ", "You can also see: "],
			'input': "\nTell me what to do ? ",
			'unknown word': "You use word(s) I don't know! ",
			'filename': "Filename [{0}]: ",
			'save error': "Unable to create save file.\n",
			'save ok': "Saved.\n",
			'load error': "Unable to restore game.",
			'game over': "The game is now over.\n",
			'overloaded': ["I've too much to carry ", "You are carrying too much. "],
			'dead': ["I am dead.\n", "You are dead.\n"],
			'treasures': "{0}stored {1} treasures.  On a scale of 0 to 100, that rates {2}.\n",
			'well done': "Well done.\n",
			'nothing': "Nothing",
			'have': ["I've ", "You have "],
			'carry': ["I'm carrying:\n{0}.\n", "You are carrying:\n{0}.\n"],
			'need dir': "Give me a direction too.",
			'dark warning': "Dangerous to move in the dark! ",
			'broke neck': ["I fell down and broke my neck. ", "You fell down and broke your neck. "],
			'blocked': ["I can't go in that direction. ", "You can't go in that direction. "],
			'dark': "It is dark.\n",
			'take':  "{0}: O.K.\n",
			'drop':  "{0}: O.K.\n",
			'nothing taken': "Nothing taken.",
			'nothing dropped': "Nothing dropped.\n",
			'what': "What ? ",
			'unable': ["It's beyond my power to do that. ", "It is beyond your power to do that. "],
			'ok': "O.K. ",
			'light out in': "Light runs out in {0:d} turns. ",
			'light dim': "Your light is growing dim. "
		}

		if os.environ.has_key(ENV_FILE):
			self.filepath = os.environ.get(ENV_FILE)
		else:
			self.filepath = ''

		if os.environ.has_key(ENV_SAVE):
			self.savepath = os.environ.get(ENV_SAVE)
		elif os.environ.has_key('HOME'):
			self.savepath = os.path.join(os.path.expanduser(DIR_SAVE))
			if not os.path.exists(self.savepath):
				os.mkdir(self.savepath)
		else:
			self.savepath = ''

		if filename != None:
			self.load_database(filename)

		# Initialize the random number generator, None will use the system time
		random.seed(seed)

		self.output('''PyScottFree, A Scott Adams game driver in Python.
Release {0}, {1}.
Based on Scott Free A Scott Adams game driver in C.
Release 1.14, (c) 1993,1994,1995 Swansea University Computer Society.
{2}

'''.format(__version__, __copyright__, __license__))


	def dump(self):
		print '''
--Game--
Items: [{1}]
Actions: [{2}]
Verbs: {0.verbs}
Nouns: {0.nouns}
Rooms: [{3}]
Max Carry: {0.max_carry}
Player Room: {0.player_room}
Treasures: {0.treasures}
Word Length: {0.word_length}
Light Time: {0.light_time}
Messages: [{0.messages}]
Treasure Room: {0.treasure_room}

Version: {0.version}
Adventure: {0.adventure}
'''.format( \
				self, \
				', \n'.join(map(lambda obj: obj.to_string(), self.items)),
				', \n'.join(map(lambda obj: obj.to_string(), self.actions)),
				', \n'.join(map(lambda obj: obj.to_string(), self.rooms))
		)

	def exit(self, errno = 0, str = None):
		if self.options & FLAG_WAIT_ON_EXIT:
			time.sleep(5)
		elif self.options & FLAG_USE_CURSES:
			self.input('\nPress Enter to continue...')

		exit(errno, str)

	def fatal(self, str):
		self.exit(1, '\n{0}.\n'.format(str))

	def string(self, name, option_flag = None):
		if option_flag == None:
			return self.strings[name]
		return self.strings[name][self.options & option_flag and 1 or 0]

	def clear_screen(self):
		if self.options & FLAG_USE_CURSES:
			for win in self.win:
				win.erase()

	def output_reset(self, win = 1, scroll = False):
		if self.options & FLAG_USE_CURSES:
			if scroll:
				self.win[win].scroll
			self.win[win].move(self.win_height[win] -1, 0)
			self.win[win].clrtoeol()

	def curses_addstr(self, str, win = 1):
		try:
			self.win[win].addstr(str)
		except curses.error:
			pass

	def output(self, str, win = 1, scroll = True, wrap = True):
		if self.options & FLAG_USE_CURSES:
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
		else:
			sys.stdout.write(wrap_str(str, self.width))

	def input(self, str = '', win = 1):
		if self.options & FLAG_USE_CURSES:
			self.output(str, win, False)
			curses.doupdate()
			curses.echo()
			str = self.win[win].getstr()
			curses.noecho()
			self.output_reset()
		else:
			str = raw_input(str)

		return str.strip()

	def count_carried(self):
		return reduce(lambda count, item: count + item.location == LOC_CARRIED and 1 or 0, self.items, 0)

	def map_synonym(self, word):
		for noun in self.nouns:
			if not len(noun):
				continue

			if noun.startswith('*'):
				noun = noun[1:]
			else:
				self.last_synonym = noun

			if word[:self.word_length].lower() == noun[:self.word_length].lower():
				return self.last_synonym

		return None

	def match_up_item(self, text, loc):
		word = self.map_synonym(text)

		if word == None:
			word = text

		for (i, item) in enumerate(self.items):
			if item.auto_get and item.location == loc \
					and item.auto_get[:self.word_length].lower() == word[:self.word_length].lower():
				return i

		return -1


	def load_database(self, filename = None):
		if filename == None:
			filename = self.input('Filename: ').strip()

		if not os.path.exists(filename):
			filename = os.path.join(self.filepath, filename)

		# Try to open the file
		try:
			file = open(filename, 'r')
		except IOError:
			self.fatal(self.string('file error').format(filename))

		self.filename = filename

		# Generate a savename from the filename by replacing the extension
		self.savename = os.path.join(self.savepath,
				 os.path.splitext(os.path.basename(filename))[0] + '.sav')

		keys = [0, 'ni', 'na', 'nw', 'nr', 'mc', 'pr', 'tr', 'wl', 'lt', 'mn', 'trm']
		data = {}
		for key in keys:
			data[key] = read_number(file)

		self.items = [Item() for i in range(0, data['ni'] + 1)]
		self.actions = [Action() for i in range(0, data['na'] + 1)]
		self.verbs = [None] * (data['nw'] + 1)
		self.nouns = [None] * (data['nw'] + 1)
		self.rooms = [Room() for i in range(0, data['nr'] + 1)]
		self.max_carry = data['mc']
		self.player_room = data['pr']
		self.treasures = data['tr']
		self.word_length = data['wl']
		self.light_time = self.light_refill = data['lt']
		self.messages = [None] * (data['mn'] + 1)
		self.treasure_room = data['trm']

		if self.options & FLAG_VERBOSE or self.options & FLAG_DEBUGGING:
			print 'Reading {0:d} actions.'.format(data['na'])
		for action in self.actions:
			action.read(file)

		if self.options & FLAG_VERBOSE or self.options & FLAG_DEBUGGING:
			print 'Reading {0:d} word pairs.'.format(data['nw'])
		for i in range(0, data['nw'] + 1):
			self.verbs[i] = read_string(file)
			self.nouns[i] = read_string(file)

		if self.options & FLAG_VERBOSE or self.options & FLAG_DEBUGGING:
			print 'Reading {0:d} rooms.'.format(data['nr'])
		for room in self.rooms:
			room.read(file)

		if self.options & FLAG_VERBOSE or self.options & FLAG_DEBUGGING:
			print 'Reading {0:d} messages.'.format(data['mn'])
		for i in range(0, data['mn'] + 1):
			self.messages[i] = read_string(file)

		if self.options & FLAG_VERBOSE or self.options & FLAG_DEBUGGING:
			print 'Reading {0:d} items. '.format(data['ni'])
		for item in self.items:
			item.read(file)

		# Discard Comment Strings
		for i in range(0, data['na'] + 1):
			read_string(file)

		self.version = read_number(file)
		self.adventure = read_number(file)

		if self.options & FLAG_VERBOSE or self.options & FLAG_DEBUGGING:
			print 'Version {0:d}.{1:02d} of Adventure {2:d}\nLoad Complete.\n' \
					.format(self.version / 100, self.version % 100, self.adventure)

		file.close

		if self.options & FLAG_DEBUGGING:
			self.dump()

		self.redraw = True


	def look(self):
		if self.options & FLAG_USE_CURSES:
			self.win[0].erase()
			self.win[0].move(0, 0)

		if self.bit_flags & FLAG_DARK \
				and self.items[ITEM_LIGHT].location != LOC_CARRIED \
				and self.items[ITEM_LIGHT].location != self.player_room:
			self.output(self.string('too dark', FLAG_YOUARE), 0, False)

			if self.options & FLAG_TRS80_STYLE:
				self.output(self.string('trs80 line'), 0, False)

			return

		r = self.rooms[self.player_room]
		if r.text.startswith('*'):
			self.output(r.text[1:] + '\n', 0, False)
		else:
			self.output(self.string('look', FLAG_YOUARE).format(r.text), 0, False)

		exits = []
		for (i, exit) in enumerate(r.exits):
			if exit != 0:
				exits.append(self.string('exit names')[i])

		exits = len(exits) and ', '.join(exits) or self.string('none')
		self.output(self.string('exits').format(exits), 0, False)

		items = map(lambda item: item.text, filter(lambda item: item.location == self.player_room, self.items))
		if len(items):
			separator = self.string('list separator', FLAG_TRS80_STYLE)
#			self.output(self.string('also see', FLAG_YOUARE).format(joiner.join(items)), 0, False, self.width -10)
			lines = [self.string('also see', FLAG_YOUARE)]
			for item in items:
				if len(lines[-1]) + len(item) > self.width - 10:
					lines.append('')
				lines[-1] += item + separator

			lines = '\n'.join(lines)

			if not self.options & FLAG_TRS80_STYLE:
				lines = lines[:-len(separator)]

			self.output(lines + '\n', 0, False)

		if self.options & FLAG_TRS80_STYLE:
			self.output(self.string('trs80 line'), 0, False)


	def which_word(self, word, list):
		if not word:
			return -1

		id = 0
		for i, str in enumerate(list):
			if not len(str):
				continue

			if str.startswith('*'):
				str = str[1:]
			else:
				id = i

			if word[:self.word_length].lower() == str[:self.word_length].lower():
				return id

		return -1


	def get_input(self):
		while True:
			while True:
				buf = self.input(self.string('input'))
				self.output_reset()

				if len(buf):
					break

			words = buf.split(' ')
			verb = words[0]

			noun = len(words) > 1 and words[1] or None

			if verb.startswith(':'):
				actions = {
					'load': lambda filename: self.load_database(filename),
					'restore': lambda filename: self.load_game(filename),
					'save': lambda filename: self.save_game(filename)
				}
				if verb[1:].lower() in actions:
					actions[verb[1:].lower()](noun)
					return None

			if(noun == None and len(verb) == 1):
				for k, v in self.shortforms.iteritems():
					if k == verb.lower():
						verb = v
						break

			noun_id = self.which_word(verb, self.nouns)
			# The Scott Adams system has a hack to avoid typing 'go'
			if noun_id >= 1 and noun_id <= 6:
				verb_id = 1
			else:
				verb_id = self.which_word(verb, self.verbs)
				noun_id = self.which_word(noun, self.nouns)

			if verb_id == -1:
				self.output(self.string('unknown word'))
			else:
				break

		self.noun_text = noun	# Needed by GET/DROP hack
		return (verb_id, noun_id)

	def save_game(self, filename = None):
		if filename == None:
			filename = self.input(self.string('filename').format(self.savename)).strip()

		if len(filename):
			self.savename = filename
		else:
			filename = self.savename

		if self.options & FLAG_VERBOSE:
			print 'Saving to "{0}"'.format(filename),

		try:
			file = open(filename, 'w')
		except IOError:
			self.output(self.string('save error'))

		for i in range(0, 16):
			file.write('{0:d} {1:d}\n'.format(self.counters[i], self.room_saved[i]))

		file.write('{0:d} {1:d} {2:d} {3:d} {4:d} {5:d}\n'.format(self.bit_flags, \
				self.bit_flags & FLAG_DARK and 1 or 0, \
				self.player_room, \
				self.current_counter, \
				self.saved_room, \
				self.light_time))

		for item in self.items:
			file.write('{0:d}\n'.format(item.location))

		file.close()
		self.output(self.string('save ok'))


	def load_game(self, filename = None):
		if filename == None:
			filename = self.input(self.string('filename').format(self.savename)).strip()

		if len(filename):
			self.savename = filename
		else:
			filename = self.savename

		try:
			file = open(filename,'r')
		except IOError:
			self.fatal(self.string('load error'))

		self.savename = filename

		if self.options & FLAG_VERBOSE:
			print 'Loading from "{0}"'.format(filename)

		for i in range(0, 16):
			self.counters[i] = read_number(file)
			self.room_saved[i] = read_number(file)

		self.bit_flags = read_number(file)
		dark_flag = read_number(file)
		self.player_room = read_number(file)
		self.current_counter = read_number(file)
		self.saved_room = read_number(file)
		self.light_time = read_number(file)

		# Backward compatibility
		if dark_flag:
			self.bit_flags |= FLAG_DARK

		for item in self.items:
			item.location = read_number(file)

		file.close()

		if self.options & FLAG_VERBOSE:
			print 'Loaded.'


	def done_game(self):
		self.output(self.string('game over'))
		self.exit(0)


	def test_light(self, *locations):
		if ITEM_LIGHT < len(self.items) \
				and self.items[ITEM_LIGHT].location in locations:
			return True

		return False

	def perform_line(self, action):
		continuation = 0
		params = [None] * 5
		param_id = 0
		for i in action.condition:
			(dv, cv) = divmod(i, 20)

			if self.options & FLAG_DEBUGGING:
				sys.stderr.write('Perform Line - cv: {0}, dv: {1}'.format(cv, dv))

			if cv == 0:
				params[param_id] = dv
				param_id += 1
			elif [
				lambda: self.items[dv].location != LOC_CARRIED,
				lambda: self.items[dv].location != self.player_room,
				lambda: self.items[dv].location != LOC_CARRIED \
						and self.items[dv].location != self.player_room,
				lambda: self.player_room != dv,
				lambda: self.items[dv].location == self.player_room,
				lambda: self.items[dv].location == LOC_CARRIED,
				lambda: self.player_room == dv,
				lambda: self.bit_flags & (1 << dv) == 0,
				lambda: self.bit_flags & (1 << dv),
				lambda: self.count_carried() == 0,
				lambda: self.count_carried(),
				lambda: self.items[dv].location == LOC_CARRIED \
						or self.items[dv].location == self.player_room,
				lambda: self.items[dv].location == 0,
				lambda: self.items[dv].location,
				lambda: self.current_counter > dv,
				lambda: self.current_counter <= dv,
				lambda: self.items[dv].location != self.items[dv].initial_loc,
				lambda: self.items[dv].location == self.items[dv].initial_loc,
				# Only seen in Brian Howarth games so far
				lambda: self.current_counter != dv
			][cv - 1]():
				return 0

		# Actions
		param_id = 0
		for action in action.action:
			for act in divmod(action, 150):
				if self.options & FLAG_DEBUGGING:
					sys.stderr.write('Action - {0}'.format(act))

				if act >= 1 and act < 52:
					self.output(self.messages[act] + '\n')
				elif act > 101:
					self.output(self.messages[act - 50] + '\n')
				elif act == 0: # NOP
					pass
				elif act == 52:
					if self.count_carried() == self.max_carry:
						self.output(self.string('overloaded', FLAG_YOUARE))
					else:
						if self.items[params[param_id]].location == self.player_room:
							self.redraw = True
						self.items[params[param_id]].location = LOC_CARRIED
						param_id += 1
				elif act == 53:
					self.redraw = True
					self.items[params[param_id]].location = self.player_room
					param_id += 1
				elif act == 54:
					self.redraw = True
					self.player_room = params[param_id]
					param_id += 1
				elif act == 55 or act == 59:
					if self.items[params[param_id]].location == self.player_room:
						self.redraw = True
					self.items[params[param_id]].location = 0
					param_id += 1
				elif act == 56:
					self.bit_flags |= FLAG_DARK
				elif act == 57:
					self.bit_flags &= ~FLAG_DARK
				elif act == 58:
					self.bit_flags |= (1 << params[param_id])
					param_id += 1
				elif act == 60:
					self.bit_flags &= ~(1 << params[param_id])
					param_id += 1
				elif act == 61:
					self.output(self.string('dead', FLAG_YOUARE))
					self.bit_flags &= ~FLAG_DARK
					self.player_room = len(self.rooms) -1	# It seems to be what the code says!
					self.look()
				elif act == 62:
					# Bug fix for some systems - before it could get parameters wrong
					self.items[params[param_id]].location = params[param_id + 1]
					param_id += 2
					self.redraw = True
				elif act == 63:
					self.done_game()
				elif act == 64:
					self.look()
				elif act == 65:
					treasures = reduce(lambda count, item:
								count + (item.location == self.treasure_room
										and item.text.startswith('*') and 1 or 0),
							self.items, 0)
					self.output(self.string('treasures').format(
							self.string('have', FLAG_YOUARE),
							treasures,
							treasures * 100 / self.treasures
						))

					if treasures == self.treasures:
						self.output(self.string('well done'))
						self.done_game()
				elif act == 66:
					carry = map(lambda item: item.text, filter(lambda item: item.location == LOC_CARRIED, self.items))
					if len(carry):
						carry = self.string('list separator', FLAG_TRS80_STYLE).join(carry)
					else:
						carry = self.string('nothing')

					self.output(self.string('carry', FLAG_YOUARE).format(carry))
				elif act == 67:
					self.bit_flags |= 1
				elif act == 68:
					self.bit_flags &= ~1
				elif act == 69:
					self.light_time = self.light_refill
					if self.test_light(self.player_room):
						self.redraw = True

					self.items[ITEM_LIGHT].location = LOC_CARRIED
					self.bit_flags &= ~FLAG_DARK
				elif act == 70:
					self.clear_screen()	# pdd.
					self.output_reset()
				elif act == 71:
					self.save_game()
				elif act == 72:
					i = params[param_id:param_id +2]
					param_id += 2
					if self.items[i[0]].location == self.player_room \
							or self.items[i[1]].location == self.player_room:
						self.redraw = True

					(self.items[i[0]].location, self.items[i[1]].location) \
							= (self.items[i[1]].location, self.items[i[0]].location)
				elif act == 73:
					continuation = 1
				elif act == 74:
					if self.items[params[param_id]].location == self.player_room:
						self.redraw = True
					self.items[params[param_id]].location = LOC_CARRIED
					param_id += 1
				elif act == 75:
					i = params[param_id:param_id +2]
					param_id += 2
					if self.items[i[0]].location == self.player_room \
							or self.items[i[1]].location == self.player_room:
						self.redraw = True
					self.items[i[0]].location = self.items[i[1]].location
				elif act == 76:		# Looking at adventure ..
					self.look()
				elif act == 77:
					if self.current_counter >= 0:
						self.current_counter -= 1
				elif act == 78:
					self.output(self.current_counter)
				elif act == 79:
					self.current_counter = params[param_id]
					param_id += 1
				elif act == 80:
					(self.player_room, self.saved_room) \
							= (self.saved_room, self.player_room)
					self.redraw = True
				elif act == 81:
					# This is somewhat guessed. Claymorgue always
					# seems to do select counter n, thing, select counter n,
					# but uses one value that always seems to exist. Trying
					# a few options I found this gave sane results on aging
					(self.current_counter, self.counters[params[param_id]]) \
							= (self.counters[params[param_id]], self.current_counter)
					param_id += 1
				elif act == 82:
					self.current_counter += params[param_id]
					param_id += 1
				elif act == 83:
					self.current_counter -= params[param_id]
					# Note: This seems to be needed. I don't yet
					# know if there is a maximum value to limit too
					if self.current_counter < -1:
						self.current_counter = -1
					param_id += 1
				elif act == 84:
					self.output(self.noun_text)
				elif act == 85:
					self.output(self.noun_text)
					self.output('\n')
				elif act == 86:
					self.output('\n')
				elif act == 87:
					# Changed this to swap location<->roomflag[x]
					# not roomflag 0 and x
					(self.player_room, self.room_saved[params[param_id]]) \
							= (self.room_saved[params[param_id]], self.player_room)
					param_id += 1
					self.redraw = True
				elif act == 88:
					if self.options & FLAG_USE_CURSES:
						for win in self.win:
							win.refresh()

					time.sleep(2)	# DOC's say 2 seconds. Spectrum times at 1.5
				elif act == 89:
					param_id += 1
					# SAGA draw picture n
					# Spectrum Seas of Blood - start combat ?
					# Poking this into older spectrum games causes a crash
				else:
					sys.stderr.write('Unknown action {0:d} [Param begins {1:d} {2:d}]\n' \
							.format(act, params[param_id], params[param_id + 1]))

		return 1 + continuation


	def perform_actions(self, verb_id, noun_id, enable_sysfunc = True):
		dark = bool(self.bit_flags & FLAG_DARK)

		if verb_id == 1 and noun_id == -1:
			self.output(self.string('need dir'))
			return 0

		if verb_id == 1 and noun_id in range(1, 7):
			if self.test_light(self.player_room, LOC_CARRIED):
				dark = False

			if dark:
				self.output(self.string('dark warning'))

			room = self.rooms[self.player_room].exits[noun_id - 1]
			if room != 0:
				self.player_room = room
				self.look()
				return 0

			if dark:
				self.output(self.string('broke neck', FLAG_YOUARE))
				self.exit(0)

			self.output(self.string('blocked', FLAG_YOUARE))
			return 0

		fl = -1
		do_again = False
		for action in self.actions:
			if self.options & FLAG_DEBUGGING:
				sys.stderr.write(action.to_string())

			vv = nv = action.vocab

			if vv != 0:
				do_again = False

			# Think this is now right. If a line we run has an action73
			# run all following lines with vocab of 0, 0
			if verb_id != 0 and do_again and vv != 0:
				break
			# Oops.. added this minor cockup fix 1.11
			if verb_id != 0 and not do_again and fl == 0:
				break

			nv %= 150
			vv /= 150

			if self.options & FLAG_DEBUGGING:
				sys.stderr.write('Verb: {0}, Noun: {1}, Action(Verb: {2}, Noun: {3})'.format(verb_id, noun_id, vv, nv))

			if vv == verb_id or (do_again and action.vocab == 0):
				if (vv == 0 and random_percent(nv)) \
						or do_again \
						or (vv != 0 and (nv == noun_id or nv == 0)):
					if fl == -1:
						fl = -2

					f2 = self.perform_line(action)
					if f2 > 0:
						# ahah finally figured it out !
						fl = 0
						if f2 == 2:
							do_again = True
						if verb_id != 0 and not do_again:
							return 0

		if fl != 0 and enable_sysfunc:
			if self.test_light(self.player_room, LOC_CARRIED):
			   	dark = 0

			if verb_id == 10 or verb_id == 18:
				# Yes they really _are_ hardcoded values
				if verb_id == 10:
					if self.noun_text != None and self.noun_text.lower() == 'all':
						if dark:
							self.output(self.string('dark'))
							return 0

						f = 0
						for item in self.items:
							if item.location == self.player_room \
									and len(item.auto_get) \
									and not item.auto_get.startswith('*'):
								noun_id = self.which_word(item.auto_get, self.nouns)
								# Recursively check each items table code
								self.perform_actions(verb_id, noun_id, False)
								if self.count_carried() == self.max_carry:
									self.output(self.string('overloaded', FLAG_YOUARE))
									return 0

							 	item.location = LOC_CARRIED
							 	self.redraw = True
							 	self.output(self.string('take').format(item.text))
							 	f = 1

						if f == 0:
							self.output(self.string('nothing taken'))
						return 0

					if noun_id == -1:
						self.output(self.string('what'))
						return 0

					if self.count_carried() == self.max_carry:
						self.output(self.string('overloaded', FLAG_YOUARE))
						return 0

					i = self.match_up_item(self.noun_text, self.player_room)
					if i == -1:
						self.output(self.string('unable', FLAG_YOUARE))
						return 0

					self.items[i].location = LOC_CARRIED
					self.output('O.K. ')
					self.redraw = True
					return 0

				if verb_id == 18:
					if self.noun_text != None and self.noun_text.lower() == 'all':
						f = 0
						for item in self.items:
							if item.location == LOC_CARRIED \
									and len(item.auto_get) \
									and not item.auto_get.startswith('*'):
								noun_id = self.which_word(item.auto_get, self.nouns)
								self.perform_actions(verb_id, noun_id, False)
								item.location = self.player_room
								self.output(self.string('drop').format(item.text))
								self.redraw = True
								f = 1

						if f == 0:
							self.output(self.string('nothing dropped'))
						return 0

					if noun_id == -1:
						self.output(self.string('what'))
						return 0

					i = self.match_up_item(self.noun_text, LOC_CARRIED)
					if i == -1:
						self.output(self.string('unable', FLAG_YOUARE))
						return 0

					self.items[i].location = self.player_room
					self.output(self.string('ok'))
					self.redraw = True
					return 0

		return fl


	def game_loop(self):
		while True:
			if self.redraw:
				self.look()
				self.redraw = False

			self.perform_actions(0, 0)
			if self.redraw:
				self.look()
				self.redraw = False
			input = self.get_input()
			if input == None:
				continue;
			(verb, noun) = input
			ret = self.perform_actions(verb, noun)
			if ret < 0:
				self.output(self.string('perform_actions')[abs(ret) -1])

			# Brian Howarth games seem to use -1 for forever
			if not self.test_light(LOC_DESTROYED) and self.light_time != -1:
				self.light_time -= 1
				if self.light_time < 1:
					self.bit_flags |= FLAG_LIGHT_OUT
					if self.test_light(LOC_CARRIED, self.player_room):
						output(self.string('light out', FLAG_SCOTTLIGHT))

					if self.options & FLAG_PREHISTORIC_LAMP:
						self.items[ITEM_LIGHT].location = LOC_DESTROYED

				elif self.light_time < 25:
					if self.test_light(LOC_CARRIED, self.player_room):
						if(self.options & FLAG_SCOTTLIGHT):
							self.output(self.string('light out in').format(self.light_time))
						elif(self.light_time % 5 == 0):
							self.output(self.string('light dim'))

if __name__ == '__main__':
	def usage(argv):
		sys.stderr.write('''Usage: {0} [options] <gamename> [savedgame]
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
'''.format(argv[0]))


	def main(argv):
		options = 0
		seed = None

		try:
			opts, args = getopt.getopt(argv[1:], 'hyivdstpwcr:', ['help'])
		except getopt.GetoptError, err:
			# print help information and exit:
			sys.stderr.write(str(err)) # will print something like "option -a not recognized"
			usage()
			sys.exit(2)

		for opt, arg in opts:
			if opt in ('-h', '--help'):
				usage(argv)
				sys.exit(0)
			elif opt == '-y':
				options |= FLAG_YOUARE
			elif opt == '-i':
				options &= ~FLAG_YOUARE
			elif opt == '-v':
				options |= FLAG_VERBOSE
			elif opt == '-d':
				options |= FLAG_DEBUGGING
			elif opt == '-s':
				options |= FLAG_SCOTTLIGHT
			elif opt == '-t':
				options |= FLAG_TRS80_STYLE
			elif opt == '-p':
				options |= FLAG_PREHISTORIC_LAMP
			elif opt == '-w':
				options |= FLAG_WAIT_ON_EXIT
			elif opt == '-c':
				options |= FLAG_USE_CURSES
			elif opt == '-c':
				seed = arg
			else:
				usage(argv[0])
				sys.exit(2)

		if not len(args):
			#usage(argv[0])
			#sys.exit(1)
			filename = raw_input('Filename: ').strip()

		else:
			filename = args[0]

		saga = Saga(filename, options, seed)

		if len(args) > 1:
			saga.load_game(args[1])
		elif os.path.exists(saga.savename):
			if saga.input('Found saved game "{0}" Restore [Y/n]? '.format(saga.savename)).lower() != 'n':
				saga.load_game(saga.savename)

		saga.game_loop()

	main(sys.argv)
