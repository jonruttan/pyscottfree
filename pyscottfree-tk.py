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

import Tkinter
import tkFileDialog
import tkMessageBox
from PIL import Image, ImageTk
# import Image
# import ImageTk
import sys
import os
from zipfile import ZipFile
from StringIO import StringIO

sys.path.append(os.path.dirname(sys.argv[0]))

from pyscottfree import Saga, DIR_SAVE

__author__ = 'Jon Ruttan'
__copyright__ = 'Copyright (C) 2016 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.2.0'


class TkSaga(Saga):
    def __init__(self, options=0, seed=None, name=None, file=None, greet=True):
        self.root = Tkinter.Tk()
        self.root.title("PyScottFree")
        self.dirname = '.'
        self.image_id = None
        self.game_path = '.'
        self.save_path = os.path.join(os.path.expanduser(DIR_SAVE))
        self.resize_filter = Image.NEAREST
        # self.resize_filter = Image.BILINEAR
        # self.resize_filter = Image.BICUBIC
        # self.resize_filter = Image.ANTIALIAS
        self.createWidgets()

        Saga.__init__(self, options, seed, name, file, greet)
        self.width = self.win[0]['width']

    def createWidgets(self):
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

        # Console0
        frame = Tkinter.Frame(self.root)
        frame.pack(fill=Tkinter.BOTH, expand=Tkinter.YES)
        console0 = Tkinter.Text(frame, width=40, height=10)
        console0.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=Tkinter.YES)
        self.canvas = Tkinter.Canvas(frame, width=256, height=96)
        # self.canvas.pack(
        #     side=Tkinter.LEFT,
        #     fill=Tkinter.BOTH,
        #     expand=Tkinter.YES
        # )

        # Console
        frame = Tkinter.Frame(self.root, relief=Tkinter.SUNKEN)
        frame.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=Tkinter.YES)
        console = Tkinter.Text(frame, width=80, height=14)
        console.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=Tkinter.YES)
        scrollbar = Tkinter.Scrollbar(frame)
        scrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        console.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=console.yview)
        console.bind('<Key>', lambda e: 'break')  # ignore all key presses

        console0.tag_configure('WIN0', background='white', foreground='green4')
        console.tag_configure('WIN1', background='white', foreground='blue4')
        console.tag_configure('WIN2', background='white', foreground='red4')

        # Entry
        frame = Tkinter.Frame(self.root)
        frame.pack(fill=Tkinter.X)
        label = Tkinter.Label(frame, text="Tell me what to do?")
        label.pack(side=Tkinter.LEFT)
        entry = Tkinter.Entry(frame)
        entry.pack(fill=Tkinter.X)

        self.win = console0, console, entry
        self.entry = entry
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

    def input_read(self, string='', win=1):
        return self.entry.get()

    def input(self, string='', win=1):
        string = Saga.input(self, string, win)
        self.entry.delete(0, Tkinter.END)
        self.output(string+'\n')
        return string

    def look(self):
        self.win[0].delete('1.0', Tkinter.END)
        Saga.look(self)

    def display_image(self, id):
        if not Saga.display_image(self, id):
            return
        self.image_id = id
        if len(self.images) and id < len(self.images):
            self.root.update_idletasks()
            self.canvas.image = ImageTk.PhotoImage(self.images[id].resize(
                    (
                        self.canvas.winfo_width() - 1,
                        self.canvas.winfo_height() - 1
                    ),
                    self.resize_filter
                ))
            self.canvas.create_image(
                0, 0,
                anchor=Tkinter.NW,
                image=self.canvas.image
            )

    def load_database(self, file=None):
        if not Saga.load_database(self, file):
            return False

        image_path = os.path.split(file.name)[0]
        filename = self.name + '.zip'
        path = os.path.join(image_path, filename)
        self.images = []
        if os.path.exists(path):
            self.canvas.pack(
                side=Tkinter.LEFT,
                fill=Tkinter.BOTH,
                expand=Tkinter.YES
            )
            with ZipFile(path, 'r') as gfx:
                ext = ('.bmp', '.gif', '.png')
                for filename in [
                    f for f in sorted(gfx.namelist())
                        if os.path.splitext(f)[1].lower() in ext
                ]:
                    image = Image.open(StringIO(gfx.read(filename)))
                    self.images.append(image)
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