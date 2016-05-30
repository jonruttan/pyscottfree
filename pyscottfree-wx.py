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

import wx
import sys
import os.path

from pyscottfree import Saga

__author__ = 'Jon Ruttan'
__copyright__ = 'Copyright (C) 2016 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.2.0'


class WxSaga(Saga):
    def __init__(self, options=0, seed=None, name=None, file=None, greet=True):
        self.wx_up = False
        self.root = wx.App()
        self.frame = MainWindow(self)
        Saga.__init__(self, options, seed, name, file, True)
        self.wx_up = True

    # def exit(self, errno=0, str=None):
    #     Saga.exit(self, errno, str)

    def clear_screen(self):
        Saga.clear_screen(self)
        self.frame.win[1].Clear()

    # def output_reset(self, win=1, scroll=False):
    #     Saga.output_reset(self, win, scroll)

    def output_write(self, string, win=1, scroll=True):
        self.frame.win[win].AppendText(string)

    def output(self, string, win=1, scroll=True):
        return Saga.output(self, string, win, False)

    def input_read(self, string='', win=1):
        string = self.frame.entry.GetValue()
        self.frame.entry.Clear()
        return string

    def input(self, string='', win=1):
        string = Saga.input(self, string, win)
        self.frame.win[win].AppendText(string + '\n')
        return string

    def look(self):
        self.frame.win[0].Clear()
        Saga.look(self)


class MainWindow(wx.Frame):
    def __init__(self, saga):
        super(MainWindow, self).__init__(None, size=(640, 480))
        # self.statusbar.Hide()
        self.dirname = '.'
        self.create_interior_window_components()
        self.create_exterior_window_components()

        self.saga = saga

    def on_control_key(self, event):
        if event.GetKeyCode() == 13:
            self.saga.game_loop(2)
        else:
            event.Skip(True)

    def create_interior_window_components(self):
        ''' Create "interior" window components. Three simple multiline text
        controls. '''

        # Frame
        panel = wx.Panel(self, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Win0 - description - top
        console0 = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        sizer.Add(console0, 1, wx.EXPAND | wx.ALL, 2)

        # Win1 - transcript - middle
        console = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        sizer.Add(console, 1, wx.EXPAND | wx.ALL, 2)

        # Win2 - text entry - bottom
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, label="Tell me what to do?")
        sizer2.Add(label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        entry = wx.TextCtrl(
            panel,
            size=wx.DLG_SZE(panel, wx.Size(80, -1))
        )
        sizer2.Add(entry, 1, wx.EXPAND | wx.ALL, 2)
        sizer.Add(sizer2, 0, wx.EXPAND | wx.ALL, 2)

        panel.SetSizer(sizer)

        console0.SetDefaultStyle(wx.TextAttr('FOREST GREEN', wx.WHITE))
        console.SetDefaultStyle(wx.TextAttr('MEDIUM BLUE', wx.WHITE))
        entry.SetDefaultStyle(wx.TextAttr('MEDIUM RED', wx.WHITE))

        self.win = console0, console, entry
        self.entry = entry
        self.entry.SetFocus()

        entry.Bind(wx.EVT_CHAR, self.on_control_key)

    def create_exterior_window_components(self):
        ''' Create "exterior" window components, such as menu and status
            bar. '''
        self.create_menu()
        self.CreateStatusBar()
        self.SetTitle()

    def create_menu(self):
        file_menu = wx.Menu()
        for id, label, help_text, handler in \
            [(wx.ID_ABOUT, '&About', 'Information about this program',
                self.OnAbout),
             (wx.ID_OPEN, '&Open', 'Open a new database', self.OnOpen),
             # (wx.ID_RESTORE, '&Restore', 'Restore the current game', self.OnSave),
             (wx.ID_SAVE, '&Save', 'Save the current game', self.OnSave),
             (None, None, None, None),
             (wx.ID_EXIT, 'E&xit', 'Terminate the program', self.OnExit)]:
            if id is None:
                file_menu.AppendSeparator()
            else:
                item = file_menu.Append(id, label, help_text)
                self.Bind(wx.EVT_MENU, handler, item)

        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, '&File')  # Add the fileMenu to the MenuBar
        self.SetMenuBar(menuBar)  # Add the menuBar to the Frame

    def SetTitle(self):
        # MainWindow.SetTitle overrides wx.Frame.SetTitle, so we have to
        # call it using super:
        super(MainWindow, self).SetTitle('PyScottFree')

    # Helper methods:

    def file_dialog_options(self, options={}):
        ''' Return a dictionary with file dialog options that can be
            used in both the save file dialog as well as in the open
            file dialog. '''
        return dict(message='Choose a file', defaultDir=self.dirname,
                    wildcard='*.*')

    def ask_for_filename(self, **dialogOptions):
        dialog = wx.FileDialog(self, **dialogOptions)
        if dialog.ShowModal() == wx.ID_OK:
            userProvidedFilename = True
            self.filename = dialog.GetFilename()
            self.dirname = dialog.GetDirectory()
            self.SetTitle()  # Update the window title with the new filename
        else:
            userProvidedFilename = False
        dialog.Destroy()
        return userProvidedFilename

    # Event handlers:

    def on_exit(self, event):
        self.Close()  # Close the main window.

    def on_about(self, event):
        dialog = wx.MessageDialog(
            self,
            self.saga.greeting(),
            'About PyScottFree',
            wx.OK
        )
        dialog.ShowModal()
        dialog.Destroy()

    def on_open(self, event):
        if self.ask_for_filename(style=wx.OPEN, **self.file_dialog_options()):
            with open(os.path.join(self.dirname, self.filename), 'r') as file:
                self.saga.load_database(file)

            self.saga.game_loop(2)

    def on_restore(self, event):
        if self.askUserForFilename(defaultFile=self.filename, style=wx.SAVE,
                                   **self.defaultFileDialogOptions()):

    def on_save(self, event):
        textfile = open(os.path.join(self.dirname, self.filename), 'w')
        textfile.write(self.console.GetValue())
        textfile.close()

if __name__ == '__main__':
    from pyscottfree import get_options

    (options, seed, args) = get_options(sys.argv)
    app = WxSaga(options, seed)
    if len(args) > 0:
        with open(args[0], 'r') as file:
            app.frame.saga.load_database(file)
            app.frame.saga.game_loop(2)
    app.frame.Show()
    app.root.MainLoop()
