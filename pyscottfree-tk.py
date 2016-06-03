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

import os
import sys
import Tkinter
import tkFileDialog
import tkMessageBox
from PIL import Image, ImageTk

sys.path.append(os.path.dirname(sys.argv[0]))

from pyscottfree import Saga, DIR_SAVE
from sagagfx import SagaGfx

__author__ = 'Jon Ruttan'
__copyright__ = 'Copyright (C) 2016 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.3.1'


class TkSaga(Saga):
    def __init__(self, options=0, seed=None, name=None, file=None, greet=True):
        self.root = Tkinter.Tk()
        self.root.title("PyScottFree")
        self.dirname = '.'
        self.gfx = None
        self.image_id = None
        self.game_path = '.'
        self.save_path = os.path.join(os.path.expanduser(DIR_SAVE))
        self.resize_filter = Image.NEAREST
        # self.resize_filter = Image.BILINEAR
        # self.resize_filter = Image.BICUBIC
        # self.resize_filter = Image.ANTIALIAS
        self.create_widgets()

        Saga.__init__(self, options, seed, name, file, greet)
        self.width = self.win[0]['width']

    def greeting(self):
        return '''PyScottFreeTK, A Scott Adams game driver in Python.
Release {0}, {1}.
''' \
                .format(__version__, __copyright__, __license__) \
                + Saga.greeting(self)

    def create_widgets(self):
        # Menu
        menubar = Tkinter.Menu(self.root, tearoff=0)
        self.root.config(menu=menubar)
        self.file_menu = file_menu = Tkinter.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", underline=0, menu=file_menu)
        file_menu.add_command(label="Open", command=self.on_open)
        file_menu.add_command(label="Restore Game", command=self.on_open_game)
        file_menu.add_command(label="Save Game", command=self.on_save_game)
        file_menu.add_command(
            label="Save Game As",
            command=self.on_save_game_as
        )
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=sys.exit)

        file_menu.entryconfig(
            file_menu.index('Restore Game'),
            state=Tkinter.DISABLED
        )
        file_menu.entryconfig(
            file_menu.index('Save Game'),
            state=Tkinter.DISABLED
        )
        file_menu.entryconfig(
            file_menu.index('Save Game As'),
            state=Tkinter.DISABLED
        )

        help_menu = Tkinter.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", underline=0, menu=help_menu)
        help_menu.add_command(label="About", command=self.on_about)

        # Frame
        frame = Tkinter.Frame(self.root)
        frame.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)

        # Win0 - description - top,top-left
        win0 = Tkinter.Text(frame, width=40, height=10)
        win0.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=Tkinter.YES)

        # Canvas - images - upper-right
        self.canvas = Tkinter.Canvas(frame, width=256, height=96)
        frame = Tkinter.Frame(self.root, relief=Tkinter.SUNKEN)
        frame.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=Tkinter.YES)

        # Win1 - transcript - middle
        win1 = Tkinter.Text(frame, width=80, height=14)
        win1.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=Tkinter.YES)
        scrollbar = Tkinter.Scrollbar(frame)
        scrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        win1.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=win1.yview)
        win1.bind('<Key>', lambda e: 'break')  # ignore all key presses

        # Win2 - text entry - bottom
        frame = Tkinter.Frame(self.root)
        frame.pack(fill=Tkinter.X)
        label = Tkinter.Label(frame, text="Tell me what to do?")
        label.pack(side=Tkinter.LEFT)
        win2 = Tkinter.Entry(frame)
        win2.pack(fill=Tkinter.X)

        # Set the Window colours
        win0.tag_configure('WIN0', background='white', foreground='green4')
        win1.tag_configure('WIN1', background='white', foreground='blue4')
        # win2.tag_configure('WIN2', background='white', foreground='red4')

        self.win = win0, win1, win2
        self.entry = win2
        self.entry.focus_set()

        self.root.bind('<Return>', self.on_input)
        self.root.bind('<FocusIn>', self.on_focus_in)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

    def on_focus_in(self, event):
        self.entry.focus_set()

    def on_canvas_configure(self, event):
        self.display_image(self.image_id)

    def exit(self, errno=0, str=None):
        Saga.exit(self, errno, str)

    def clear_screen(self):
        Saga.clear_screen(self)
        # self.win[0].delete('1.0', Tkinter.END)
        self.win[1].delete('1.0', Tkinter.END)
        # self.win[2].delete(0, Tkinter.END)
        # self.look()

    def output_reset(self, win=1, scroll=False):
        Saga.output_reset(self, win, scroll)

    def output_write(self, string, win=1, scroll=True):
        self.win[win].insert('end', string, ('WIN0', 'WIN1')[win])
        self.win[win].see('end')

    def output(self, string, win=1, scroll=True):
        return Saga.output(self, string, win, False)

    def input_read(self, string='', win=1):
        return self.entry.get()

    def input(self, string='', win=1):
        string = Saga.input(self, string, win)
        self.entry.delete(0, Tkinter.END)
        self.output(string + '\n')
        return string

    def look(self):
        self.win[0].delete('1.0', Tkinter.END)
        Saga.look(self)

    def display_image(self, id):
        if self.gfx is not None:
            id = self.gfx.get_image_id(self, id)

        if not Saga.display_image(self, id):
            return

        self.image_id = id

        if self.gfx is not None and self.image_id < self.gfx.num_rooms + self.gfx.num_action89 + self.gfx.num_extended:
            self.root.update_idletasks()
            size = (
                self.canvas.winfo_width() - 1 or self.gfx.size[0],
                self.canvas.winfo_height() - 1 or self.gfx.size[1],
            )
            pilImage = self.gfx.images[self.image_id].resize(size)
            self.canvas.image = ImageTk.PhotoImage(pilImage)
            self.canvas.create_image(0, 0, anchor=Tkinter.NW, image=self.canvas.image)

    def load_database(self, file=None):
        if not Saga.load_database(self, file):
            return False

        image_path = os.path.split(file.name)[0]
        self.images = []

        filename = self.name + '.gfx'
        path = os.path.join(image_path, filename)
        if os.path.exists(path):
            self.canvas.pack(
                side=Tkinter.LEFT,
                fill=Tkinter.BOTH,
                expand=Tkinter.YES
            )
            self.gfx = SagaGfx(path).read()
        else:
            self.canvas.pack_forget()

        self.file_menu.entryconfig(
            self.file_menu.index('Restore Game'),
            state=Tkinter.ACTIVE)
        self.file_menu.entryconfig(
            self.file_menu.index('Save Game'),
            state=Tkinter.ACTIVE
        )
        self.file_menu.entryconfig(
            self.file_menu.index('Save Game As'),
            state=Tkinter.ACTIVE
        )

    def on_input(self, event):
        self.game_loop(2)
        self.entry.focus_set()

    def open_database(self, path):
        self.clear_screen()
        with open(path, 'r') as file:
            self.load_database(file)
        self.on_input(None)
        self.save_path = os.path.join(
            self.save_path,
            os.path.splitext(os.path.basename(path))[0] + '.sav'
        )
        return self.game_loop(2)

    def on_open(self):
        formats = [
            ('Adventure Files', '*.dat'),
            ('All files', '*.*'),
        ]
        path = tkFileDialog.askopenfilename(
            parent=self.root,
            filetypes=formats
        )
        if not path:
            return
        self.open_database(path)

    def on_open_game(self):
        save_path = os.path.split(self.save_path)
        formats = [
            ('Saved Games', '*.sav'),
            ('All files', '*.*'),
        ]
        path = tkFileDialog.askopenfilename(
            parent=self.root,
            filetypes=formats,
            initialfile=save_path[1],
            initialdir=save_path[0]
        )
        if not path:
            return
        self.load_game(path)
        self.save_path = path
        self.look()

    def on_save_game(self):
        self.save_game(self.save_path)

    def on_save_game_as(self):
        formats = [
            ('Saved Games', '*.sav'),
            ('All files', '*.*'),
        ]
        save_path = os.path.split(self.save_path)
        path = tkFileDialog.asksaveasfilename(
            parent=self.root,
            filetypes=formats,
            initialfile=save_path[1],
            initialdir=save_path[0]
        )
        if not path:
            return
        if not self.save_game(path):
            return
        self.save_path = path

    def on_about(self):
        tkMessageBox.showinfo('About PyScottFree', self.greeting())

if __name__ == '__main__':
    from pyscottfree import get_options

    (options, seed, args) = get_options(sys.argv)
    app = TkSaga(options, seed)
    if len(args) > 0:
        app.open_database(args[0])
    app.root.mainloop()
