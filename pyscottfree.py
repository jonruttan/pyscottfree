#!/usr/bin/env python
#
#   PyScottFree
#
#   A free Scott Adams style adventure interpreter
#
#   Copyright:
#       This software is placed under the GNU license.
#
#   Statement:
#       Everything in this program has been deduced or obtained solely
#   from published material. No game interpreter code has been
#   disassembled, only published BASIC sources (PC-SIG, and Byte Dec
#   1980) have been used.
#
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version
#   2 of the License, or (at your option) any later version.
#

import sys
import os
import getopt
import time
import random
import textwrap

from functools import reduce

__author__ = 'Jon Ruttan'
__copyright__ = 'Copyright (C) 2016 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.8.6'

DIR_APP = 'scottfree'
ENV_FILE = 'SCOTTFREE_PATH'
ENV_SAVE = 'SCOTTFREE_SAVE'
home = os.getenv('HOME', './')
DIR_SAVE = '%s/.scottfree/' % home
EXT_SAVE = '.sav'


def random_percent(n):
    return random.randint(0, 99) < n


class Database:
    def __init__(self, file):
        self.file = file
        self.next_string = ''

    def read_next(self, quote=None, type=None, bytes=1):
        while not len(self.next_string):
            # Read in the next line and strip the whitespace
            string = self.file.readline()
            if not len(string):
                return None
            self.next_string = string.strip()

        if quote is not None:
            # If the string doesn't start with a quote, complain and exit
            if not self.next_string.startswith(quote):
                # self.fatal('Initial quote({0}) expected -- {1}'
                #            .format(quote, self.next_string))
                return None

            while True:
                end = self.next_string[1:].find(quote)
                # If the string doesn't end with a quote, complain and exit
                if end == -1:
                    self.next_string += '\n' + self.file.readline().strip()
                else:
                    end += 2
                    break

            string = self.next_string[:end].strip('"').replace('`', '"')

        else:
            end = self.next_string.find(' ')
            if end == -1:
                end = len(self.next_string)

            string = self.next_string[:end]

            if string == str((1 << (bytes << 3)) - 1):
                string = '-1'

        self.next_string = self.next_string[end+1:]

        return string

    def read_number(self, bytes=1):
        val = self.read_next()
        return val is not None and int(val) or 0

    def read_string(self):
        return self.read_next('"')

    def read_any(self):
        string = self.read_string()
        return string is not None and string or self.read_number()


class Action:
    def __init__(self):
        self.vocab = None
        self.condition = [None] * 5
        self.action = [None] * 2

    def read(self, database):
        self.vocab = database.read_number()
        self.condition = [database.read_number() for i in range(0, 5)]
        self.action = [database.read_number() for i in range(0, 2)]
        return self

    def to_string(self):
        return 'Action(Vocab: {0:d}, Condition: {1}, Action: {2})'.format(
                self.vocab,
                self.condition,
                self.action
        )


class Room:
    def __init__(self):
        self.text = None
        self.exits = [None] * 6

    def read(self, database):
        self.exits = [database.read_number() for i in range(0, 6)]
        self.text = database.read_string()
        return self

    def to_string(self):
        return 'Room(Text: {0}, Exits: {1})'.format(
                self.text,
                self.exits
        )


class Item:
    def __init__(self):
        self.text = None
        self.location = None
        self.initial_loc = None
        self.auto_get = None

    def read(self, database):
        words = database.read_string().split('/')
        self.text = words[0]

        # Some games use // to mean no auto get/drop word!
        if len(words) > 1 and len(words[1]) > 1 and not words[1][1] in ('/', '*'):
            self.auto_get = words[1]
        else:
            self.auto_get = ''

        self.initial_loc = self.location = database.read_number()
        return self

    def to_string(self):
        return 'Item(Text: "{0}", Location: {1}, Initial Location: {2}, Auto Get: {3})'.format(
                self.text,
                self.location,
                self.initial_loc,
                self.auto_get,
        )


class Saga:
    LOC_DESTROYED = 0               # Destroyed
    LOC_CARRIED = 255               # Carried

    ITEM_LIGHT = 9                  # Always 9 how odd

    FLAG_YOUARE = 0x1               # You are not I am
    FLAG_SCOTTLIGHT = 0x2           # Authentic Scott Adams light messages
    FLAG_TRS80_STYLE = 0x4          # Display in style used on TRS-80
    FLAG_PREHISTORIC_LAMP = 0x8     # Destroy the lamp (very old databases)
    FLAG_WAIT_ON_EXIT = 0x20        # Wait before exiting
    FLAG_VERBOSE = 0x40             # Info from load/save
    FLAG_DEBUGGING = 0x80           # Debugging info

    FLAG_DARK = 0x8000
    FLAG_LIGHT_OUT = 0x10000        # Light gone out

    STATE_ERR = -1                  # Error
    STATE_NONE = 0                  # Uninitialised
    STATE_INIT = 1                  # Initialized
    STATE_RUN = 2                   # Database loaded, game running
    STATE_WAIT = 3                  # Waiting for external process

    def __init__(self, options=0, seed=None, name=None, file=None, greet=True):
        self.name = name
        self.state = Saga.STATE_NONE

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
        self.counters = [0] * 16        # Range unknown
        self.current_counter = 0
        self.saved_room = 0
        self.room_saved = [0] * 16      # Range unknown
        self.options = options          # Options flags set
        self.bit_flags = 0
        self.redraw = False             # Update item window
        self.width = 80                 # 80 column display

        if options is not None:
            # Terminal width
            if options & Saga.FLAG_TRS80_STYLE:
                self.width = 64
                self.win_height = (11, 13)

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
            'exit names': ['North', 'South', 'East', 'West', 'Up', 'Down'],

            # Separator used for lists; second entry tied to FLAG_TRS80_STYLE
            'list separator': [' - ', '. '],

            # Light out message; second entry tied to FLAG_SCOTTLIGHT flag
            'light out': ['Your light has run out. ', 'Light has run out! '],

            # Perform action responses
            'perform_actions': [
                "I don't understand your command. ",
                "I can't do that yet. "
            ],

            # Rest of list is messages; second entry tied to FLAG_YOUARE flag
            'trs80 line': '\n<' + '-' * (self.width - 4) + '>\n',
            'none': 'none',
            'file error': "Can't open '{0}'",
            'too dark': [
                "I can't see. It is too dark!",
                "You can't see. It is too dark!"
            ],
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
            'overloaded': [
                "I've too much to carry ",
                "You are carrying too much. "
            ],
            'dead': ["I am dead.\n", "You are dead.\n"],
            'treasures': "{0}stored {1} treasures.  On a scale of 0 to 100, that rates {2}.\n",
            'well done': "Well done.\n",
            'nothing': "Nothing",
            'have': ["I've ", "You have "],
            'carry': ["I'm carrying:\n{0}.\n", "You are carrying:\n{0}.\n"],
            'need dir': "Give me a direction too.",
            'dark warning': "Dangerous to move in the dark! ",
            'broke neck': [
                "I fell down and broke my neck. ",
                "You fell down and broke your neck. "
            ],
            'blocked': [
                "I can't go in that direction. ",
                "You can't go in that direction. "
            ],
            'dark': "It is dark.\n",
            'take':  "{0}: O.K.\n",
            'drop':  "{0}: O.K.\n",
            'nothing taken': "Nothing taken.",
            'nothing dropped': "Nothing dropped.\n",
            'what': "What ? ",
            'unable': [
                "It's beyond my power to do that. ",
                "It is beyond your power to do that. "
            ],
            'ok': "O.K. ",
            'light out in': "Light runs out in {0:d} turns. ",
            'light dim': "Your light is growing dim. "
        }

        # Initialize the random number generator, None will use the system time
        random.seed(seed)

        self.state = Saga.STATE_INIT
        self.load_database(file)

        if greet:
            self.output(self.greeting())

    def greeting(self):
        return '''PyScottFree, A Scott Adams game driver in Python.
Release {0}, {1}.
Based on Scott Free A Scott Adams game driver in C.
Release 1.14, (c) 1993,1994,1995 Swansea University Computer Society.
{2}

'''.format(__version__, __copyright__, __license__)

    def dump(self):
        print('''
--Game--
Items: [
{1}
]
Actions: [
{2}
]
Verbs: {0.verbs}
Nouns: {0.nouns}
Rooms: [
{3}
]
Max Carry: {0.max_carry}
Player Room: {0.player_room}
Treasures: {0.treasures}
Word Length: {0.word_length}
Light Time: {0.light_time}
Messages: [
{4}
]
Treasure Room: {0.treasure_room}

Version: {0.version}
Adventure: {0.adventure}
'''.format(self,
            ', \n'.join(map(lambda obj: "\t"+obj.to_string(), self.items)),
            ', \n'.join(map(lambda obj: "\t"+obj.to_string(), self.actions)),
            ', \n'.join(map(lambda obj: "\t"+obj.to_string(), self.rooms)),
            ', \n'.join(map(lambda s: "\t"+s, self.messages)),
           ))

    def do_exit(self, errno=0, errstr=None):
        if errstr is not None:
            sys.stderr.write(errstr)

    def exit(self, errno=0, errstr=None):
        if self.options & Saga.FLAG_WAIT_ON_EXIT:
            time.sleep(5)

        self.do_exit(errno, errstr)
        sys.exit(errno)

    def aborted(self):
        self.exit(0, '\nUser exit\n')

    def fatal(self, str):
        self.state = Saga.STATE_ERR
        self.exit(1, '\n{0}.\n'.format(str))

    def option(self, *options):
        return reduce(lambda x, y: x | y, options) & self.options

    def string(self, name, option_flag=None):
        if option_flag is None:
            return self.strings[name]
        return self.strings[name][self.options & option_flag and 1 or 0]

    def clear_screen(self):
        return self

    def output_reset(self, win=1, scroll=False):
        return self

    def output_write(self, str, win=1, scroll=True):
        sys.stdout.write(str)
        return self

    def output(self, obj, win=1, scroll=True, wrap=True):
        string = str(obj)

        if not string[-1].isspace():
            string += ' '

        if wrap is True:
            wrap = self.width - 2

        if(wrap):
            wrapper = textwrap.TextWrapper(
                width=wrap,
                replace_whitespace=False,
                drop_whitespace=False
            )
            string = ''.join(
                [wrapper.fill(string) for string in string.splitlines(True)]
            )

        self.output_write(string, win, scroll)
        return self

    def input_read(self, str='', win=1):
        try:
            return raw_input(str)
        except(KeyboardInterrupt, EOFError):
            self.aborted()

    def input(self, str='', win=1):
        return self.input_read(str, win).strip()

    def count_carried(self):
        return reduce(lambda count, item: count + item.location == Saga.LOC_CARRIED and 1 or 0, self.items, 0)

    def test_light(self, *locations):
        if Saga.ITEM_LIGHT < len(self.items) \
                and self.items[Saga.ITEM_LIGHT].location in locations:
            return True

        return False

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

        if word is None:
            word = text

        for (i, item) in enumerate(self.items):
            if item.auto_get and item.location == loc \
                    and item.auto_get[:self.word_length].lower() == word[:self.word_length].lower():
                return i

        return -1

    def load_database(self, file=None, name=None):
        if file is None:
            return False

        if name is None:
            name = os.path.splitext(os.path.split(file.name)[1])[0]

        database = Database(file)
        self.name = database.read_any()
        if type(self.name) is not 'str':
            self.name = name

        keys = ['ni', 'na', 'nw', 'nr', 'mc', 'pr', 'tr', 'wl', 'lt', 'mn', 'trm']
        data = {}
        for key in keys:
            data[key] = database.read_number()

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

        if self.option(Saga.FLAG_VERBOSE, Saga.FLAG_DEBUGGING):
            print('Reading {0:d} actions.'.format(data['na']))
        for action in self.actions:
            action.read(database)

        if self.option(Saga.FLAG_VERBOSE, Saga.FLAG_DEBUGGING):
            print('Reading {0:d} word pairs.'.format(data['nw']))
        for i in range(0, data['nw'] + 1):
            self.verbs[i] = database.read_string()
            self.nouns[i] = database.read_string()

        if self.option(Saga.FLAG_VERBOSE, Saga.FLAG_DEBUGGING):
            print('Reading {0:d} rooms.'.format(data['nr']))
        for room in self.rooms:
            room.read(database)

        if self.option(Saga.FLAG_VERBOSE, Saga.FLAG_DEBUGGING):
            print('Reading {0:d} messages.'.format(data['mn']))
        for i in range(0, data['mn'] + 1):
            self.messages[i] = database.read_string()

        if self.option(Saga.FLAG_VERBOSE, Saga.FLAG_DEBUGGING):
            print('Reading {0:d} items. '.format(data['ni']))
        for item in self.items:
            item.read(database)

        # Discard Comment Strings
        for i in range(0, data['na'] + 1):
            database.read_string()

        self.version = database.read_number()
        self.adventure = database.read_number()

        if self.option(Saga.FLAG_VERBOSE, Saga.FLAG_DEBUGGING):
            print('Version {0:d}.{1:02d} of Adventure {2:d}\nLoad Complete.\n'
                  .format(self.version / 100, self.version % 100, self.adventure))

        #if self.option(Saga.FLAG_DEBUGGING):
        #   self.dump()

        self.redraw = True
        self.state = Saga.STATE_RUN
        return self

    def look(self):
        if self.bit_flags & Saga.FLAG_DARK \
                and self.items[Saga.ITEM_LIGHT].location != Saga.LOC_CARRIED \
                and self.items[Saga.ITEM_LIGHT].location != self.player_room:
            self.output(self.string('too dark', Saga.FLAG_YOUARE), 0, False)

            if self.options & Saga.FLAG_TRS80_STYLE:
                self.output(self.string('trs80 line'), 0, False)

            return

        r = self.rooms[self.player_room]
        if r.text.startswith('*'):
            self.output(r.text[1:] + '\n', 0, False)
        else:
            self.output(self.string('look', Saga.FLAG_YOUARE).format(r.text), 0, False)

        exits = []
        for (i, exit) in enumerate(r.exits):
            if exit != 0:
                exits.append(self.string('exit names')[i])

        exits = len(exits) and ', '.join(exits) or self.string('none')
        self.output(self.string('exits').format(exits), 0, False)

        items = map(lambda item: item.text, filter(lambda item: item.location == self.player_room, self.items))
        if len(items):
            separator = self.string('list separator', Saga.FLAG_TRS80_STYLE)
            lines = [self.string('also see', Saga.FLAG_YOUARE)]
            for item in items:
                if len(lines[-1]) + len(item) > self.width - 10:
                    lines.append('')
                lines[-1] += item + separator

            lines = '\n'.join(lines)

            if not self.options & Saga.FLAG_TRS80_STYLE:
                lines = lines[:-len(separator)]

            self.output(lines + '\n', 0, False)

        if self.options & Saga.FLAG_TRS80_STYLE:
            self.output(self.string('trs80 line'), 0, False)

        self.display_image(self.player_room)
        return self

    def display_image(self, id):
        if id is None:
            return False
        if self.option(Saga.FLAG_DEBUGGING):
            print('Display Image: %d\n' % id)
        return self

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
        buf = self.input(self.string('input'))
        self.output_reset()

        if not len(buf):
            return None

        words = buf.split(' ')
        verb = words[0]

        noun = len(words) > 1 and words[1] or None

        if verb.startswith(':'):
            actions = {
                'load': lambda filename: self.load_database(filename),
                'restore': lambda filename: self.load_game(filename),
                'save': lambda filename: self.save_game(filename),
                'quit': lambda verb: self.exit(1, '\nUser exit\n')
            }
            if verb[1:].lower() in actions:
                actions[verb[1:].lower()](noun)
                return False

        if(noun is None and len(verb) == 1):
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
            return False

        self.noun_text = noun   # Needed by GET/DROP hack
        return (verb_id, noun_id)

    def save_game(self, filename=None):
        default = os.path.join(DIR_SAVE, self.name + EXT_SAVE)

        if filename is None:
            filename = self.input(self.string('filename').format(default)).strip()

        if not len(filename):
            filename = default

        if self.options & Saga.FLAG_VERBOSE:
            print('Saving to "{0}"'.format(filename))

        try:
            file = open(filename, 'w')

            for i in range(0, 16):
                file.write('{0:d} {1:d}\n'.format(self.counters[i], self.room_saved[i]))

            file.write('{0:d} {1:d} {2:d} {3:d} {4:d} {5:d}\n'.format(self.bit_flags,
                       self.bit_flags & Saga.FLAG_DARK and 1 or 0,
                       self.player_room,
                       self.current_counter,
                       self.saved_room,
                       self.light_time))

            for item in self.items:
                file.write('{0:d}\n'.format(item.location))

            file.close()
            self.output(self.string('save ok'))
        except IOError:
            self.output(self.string('save error'))

        return self

    def load_game(self, filename=None):
        default = os.path.join(DIR_SAVE, self.name + EXT_SAVE)

        if filename is None:
            filename = self.input(self.string('filename').format(default)).strip()

        if not len(filename):
            filename = default

        try:
            with open(filename, 'r') as file:
                database = Database(file)

                if self.options & Saga.FLAG_VERBOSE:
                    print('Loading from "{0}"'.format(filename))

                for i in range(0, 16):
                    self.counters[i] = database.read_number()
                    self.room_saved[i] = database.read_number()

                self.bit_flags = database.read_number()
                dark_flag = database.read_number()
                self.player_room = database.read_number()
                self.current_counter = database.read_number()
                self.saved_room = database.read_number()
                self.light_time = database.read_number()

                # Backward compatibility
                if dark_flag:
                    self.bit_flags |= Saga.FLAG_DARK

                for item in self.items:
                    item.location = database.read_number()

            if self.options & Saga.FLAG_VERBOSE:
                print('Loaded.')
        except IOError:
            self.fatal(self.string('load error'))

        return self

    def done_game(self):
        self.output(self.string('game over'))
        self.exit(0)

    def perform_line(self, action):
        continuation = 0
        params = [None] * 5
        param_id = 0
        for i in action.condition:
            (dv, cv) = divmod(i, 20)

            #if self.options & Saga.FLAG_DEBUGGING:
            #   sys.stderr.write('Perform Line - cv: {0}, dv: {1}\n'.format(cv, dv))

            if cv == 0:
                params[param_id] = dv
                param_id += 1
            elif [
                lambda: self.items[dv].location != Saga.LOC_CARRIED,
                lambda: self.items[dv].location != self.player_room,
                lambda: self.items[dv].location != Saga.LOC_CARRIED and
                self.items[dv].location != self.player_room,
                lambda: self.player_room != dv,
                lambda: self.items[dv].location == self.player_room,
                lambda: self.items[dv].location == Saga.LOC_CARRIED,
                lambda: self.player_room == dv,
                lambda: self.bit_flags & (1 << dv) == 0,
                lambda: self.bit_flags & (1 << dv),
                lambda: self.count_carried() == 0,
                lambda: self.count_carried(),
                lambda: self.items[dv].location == Saga.LOC_CARRIED or
                self.items[dv].location == self.player_room,
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
                #if self.options & Saga.FLAG_DEBUGGING:
                #   sys.stderr.write('Action - {0}\n'.format(act))

                if act >= 1 and act < 52:
                    self.output(self.messages[act] + '\n')
                elif act > 101:
                    self.output(self.messages[act - 50] + '\n')
                elif act == 0:  # NOP
                    pass
                elif act == 52:
                    if self.count_carried() == self.max_carry:
                        self.output(self.string('overloaded', Saga.FLAG_YOUARE))
                    else:
                        if self.items[params[param_id]].location == self.player_room:
                            self.redraw = True
                        self.items[params[param_id]].location = Saga.LOC_CARRIED
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
                    self.bit_flags |= Saga.FLAG_DARK
                elif act == 57:
                    self.bit_flags &= ~Saga.FLAG_DARK
                elif act == 58:
                    self.bit_flags |= (1 << params[param_id])
                    param_id += 1
                elif act == 60:
                    self.bit_flags &= ~(1 << params[param_id])
                    param_id += 1
                elif act == 61:
                    self.output(self.string('dead', Saga.FLAG_YOUARE))
                    self.bit_flags &= ~Saga.FLAG_DARK
                    self.player_room = len(self.rooms) - 1   # It seems to be what the code says!
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
                    treasures = reduce(
                        lambda count, item:
                            count + (item.location == self.treasure_room and
                                     item.text.startswith('*') and 1 or 0),
                        self.items, 0)
                    self.output(self.string('treasures').format(
                            self.string('have', Saga.FLAG_YOUARE),
                            treasures,
                            treasures * 100 / self.treasures
                        ))

                    if treasures == self.treasures:
                        self.output(self.string('well done'))
                        self.done_game()
                elif act == 66:
                    carry = map(lambda item: item.text, filter(
                        lambda item: item.location == Saga.LOC_CARRIED,
                        self.items)
                    )
                    if len(carry):
                        carry = self.string(
                            'list separator',
                            Saga.FLAG_TRS80_STYLE
                        ).join(carry)
                    else:
                        carry = self.string('nothing')

                    self.output(
                        self.string('carry', Saga.FLAG_YOUARE)
                        .format(carry)
                    )
                elif act == 67:
                    self.bit_flags |= 1
                elif act == 68:
                    self.bit_flags &= ~1
                elif act == 69:
                    self.light_time = self.light_refill
                    if self.test_light(self.player_room):
                        self.redraw = True

                    self.items[Saga.ITEM_LIGHT].location = Saga.LOC_CARRIED
                    self.bit_flags &= ~Saga.FLAG_DARK
                elif act == 70:
                    self.clear_screen()  # pdd.
                    self.output_reset()
                elif act == 71:
                    self.save_game()
                elif act == 72:
                    i = params[param_id:param_id + 2]
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
                    self.items[params[param_id]].location = Saga.LOC_CARRIED
                    param_id += 1
                elif act == 75:
                    i = params[param_id:param_id + 2]
                    param_id += 2
                    if self.items[i[0]].location == self.player_room \
                            or self.items[i[1]].location == self.player_room:
                        self.redraw = True
                    self.items[i[0]].location = self.items[i[1]].location
                elif act == 76:     # Looking at adventure ..
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
# JR-Not sure if this is necessary
#                   if self.options & Saga.FLAG_USE_CURSES:
#                       for win in self.win:
#                           win.refresh()

                    time.sleep(2)   # DOC's say 2 seconds. Spectrum times at 1.5
                elif act == 89:
                    # SAGA draw picture n
                    # Spectrum Seas of Blood - start combat ?
                    # Poking this into older spectrum games causes a crash
                    #if self.option(Saga.FLAG_DEBUGGING):
                    print('Display Image\n')
                    self.display_image(len(self.rooms)+params[param_id])
                    param_id += 1
                else:
                    sys.stderr.write(
                        'Unknown action {0:d} [Param begins {1:d} {2:d}]\n'
                        .format(act, params[param_id], params[param_id + 1])
                    )

        return 1 + continuation

    def perform_actions(self, verb_id, noun_id, enable_sysfunc=True):
        dark = bool(self.bit_flags & Saga.FLAG_DARK)

        if verb_id == 1 and noun_id == -1:
            self.output(self.string('need dir'))
            return 0

        if verb_id == 1 and noun_id in range(1, 7):
            if self.test_light(self.player_room, Saga.LOC_CARRIED):
                dark = False

            if dark:
                self.output(self.string('dark warning'))

            room = self.rooms[self.player_room].exits[noun_id - 1]
            if room != 0:
                self.player_room = room
                self.look()
                return 0

            if dark:
                self.output(self.string('broke neck', Saga.FLAG_YOUARE))
                self.exit(0)

            self.output(self.string('blocked', Saga.FLAG_YOUARE))
            return 0

        fl = -1
        do_again = False
        for action in self.actions:
            #if self.options & Saga.FLAG_DEBUGGING:
            #   sys.stderr.write(action.to_string())

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

            #if self.options & Saga.FLAG_DEBUGGING:
            #   sys.stderr.write('Verb: {0}, Noun: {1}, Action(Verb: {2}, Noun: {3})\n'.format(verb_id, noun_id, vv, nv))

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
            if self.test_light(self.player_room, Saga.LOC_CARRIED):
                dark = 0

            if verb_id == 10 or verb_id == 18:
                # Yes they really _are_ hardcoded values
                if verb_id == 10:
                    if self.noun_text is not None and self.noun_text.lower() == 'all':
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
                                    self.output(self.string('overloaded', Saga.FLAG_YOUARE))
                                    return 0

                                item.location = Saga.LOC_CARRIED
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
                        self.output(self.string('overloaded', Saga.FLAG_YOUARE))
                        return 0

                    i = self.match_up_item(self.noun_text, self.player_room)
                    if i == -1:
                        self.output(self.string('unable', Saga.FLAG_YOUARE))
                        return 0

                    self.items[i].location = Saga.LOC_CARRIED
                    self.output('O.K. ')
                    self.redraw = True
                    return 0

                if verb_id == 18:
                    if self.noun_text is not None and self.noun_text.lower() == 'all':
                        f = 0
                        for item in self.items:
                            if item.location == Saga.LOC_CARRIED \
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

                    i = self.match_up_item(self.noun_text, Saga.LOC_CARRIED)
                    if i == -1:
                        self.output(self.string('unable', Saga.FLAG_YOUARE))
                        return 0

                    self.items[i].location = self.player_room
                    self.output(self.string('ok'))
                    self.redraw = True
                    return 0

        return fl

    def game_loop(self, iterations=-1):
        while iterations:
            if self.state is Saga.STATE_RUN:
                if iterations != -1:
                    iterations -= 1

                if self.redraw:
                    self.look()
                    self.redraw = False

                self.perform_actions(0, 0)
                if self.redraw:
                    self.look()
                    self.redraw = False

                self.state = Saga.STATE_WAIT

            if self.state is Saga.STATE_WAIT:
                input = self.get_input()
                if input is None:
                    break
                if not input:
                    continue

                self.state = Saga.STATE_RUN
                (verb, noun) = input
                ret = self.perform_actions(verb, noun)
                if ret < 0:
                    self.output(self.string('perform_actions')[abs(ret) - 1])

                # Brian Howarth games seem to use -1 for forever
                if not self.test_light(Saga.LOC_DESTROYED) and self.light_time != - 1:
                    self.light_time -= 1
                    if self.light_time < 1:
                        self.bit_flags |= Saga.FLAG_LIGHT_OUT
                        if self.test_light(Saga.LOC_CARRIED, self.player_room):
                            self.output(self.string('light out', Saga.FLAG_SCOTTLIGHT))

                        if self.options & Saga.FLAG_PREHISTORIC_LAMP:
                            self.items[Saga.ITEM_LIGHT].location = Saga.LOC_DESTROYED

                    elif self.light_time < 25:
                        if self.test_light(Saga.LOC_CARRIED, self.player_room):
                            if(self.options & Saga.FLAG_SCOTTLIGHT):
                                self.output(
                                    self.string('light out in')
                                    .format(self.light_time)
                                )
                            elif(self.light_time % 5 == 0):
                                self.output(self.string('light dim'))

        return self


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
  -r  Randomizer seed
'''.format(argv[0]))


def get_options(argv):
    options = 0
    seed = None

    try:
        opts, args = getopt.getopt(argv[1:], 'hyivdstpwcr:', ['help'])
    except getopt.GetoptError as err:
        # print help information and exit:
        sys.stderr.write(str(err)) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(argv)
            sys.exit(0)
        elif opt == '-y':
            options |= Saga.FLAG_YOUARE
        elif opt == '-i':
            options &= ~Saga.FLAG_YOUARE
        elif opt == '-v':
            options |= Saga.FLAG_VERBOSE
        elif opt == '-d':
            options |= Saga.FLAG_DEBUGGING
        elif opt == '-s':
            options |= Saga.FLAG_SCOTTLIGHT
        elif opt == '-t':
            options |= Saga.FLAG_TRS80_STYLE
        elif opt == '-p':
            options |= Saga.FLAG_PREHISTORIC_LAMP
        elif opt == '-w':
            options |= Saga.FLAG_WAIT_ON_EXIT
        elif opt == '-r':
            seed = arg
        else:
            usage(argv[0])
            sys.exit(2)

    return (options, seed, args)


def main(argv, obj_type=Saga):
    (options, seed, args) = get_options(argv)

    try:
        filename = args[0]
    except:
        filename = raw_input('Filename: ').strip()

    filepath = os.getenv(ENV_FILE, DIR_APP)
    if filepath is None:
        filepath = ''

    savepath = os.environ.get(ENV_SAVE)
    if savepath is None:
        savepath = os.path.join(os.path.expanduser(DIR_SAVE))
        if not os.path.exists(savepath):
            os.mkdir(savepath)

    if not os.path.exists(filename):
        filename = os.path.join(filepath, filename)

    name = os.path.splitext(os.path.basename(filename))[0]

    # Try to open the file and initialize the interpreter
    with open(filename, 'r') as file:
        saga = obj_type(options, seed, name, file)

    # Generate a savename from the filename by replacing the extension
    savename = os.path.join(
        savepath,
        os.path.splitext(os.path.basename(filename))[0] + '.sav'
    )

    if os.path.exists(savename):
        if saga.input('Found saved game "{0}" Restore [Y/n]? '.format(savename)).lower() != 'n':
            saga.load_game(savename)

    saga.game_loop()

if __name__ == '__main__':
    main(sys.argv)
