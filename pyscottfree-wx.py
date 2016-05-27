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
__copyright__ = 'Copyright (C) 2010 Jon Ruttan'
__license__ = 'Distributed under the GNU software license'
__version__ = '0.2.0'


class WxSaga(Saga):
    def __init__(self, frame, options=0, seed=None, name=None, file=None, greet=True):
        self.frame = frame
        Saga.__init__(self, options, seed, name, file, True)

    def exit(self, errno=0, str=None):
        Saga.exit(self, errno, str)

    def clear_screen(self):
        Saga.clear_screen(self)

    def output_reset(self, win=1, scroll=False):
        Saga.output_reset(self, win, scroll)

    def output_write(self, string, win=1, scroll=True):
        self.frame.control.AppendText(string)

    # def input_read(self, string='', win=1):
    #     return Saga.input(self, win)

    def input(self, string='', win=1):
        self.frame.control.AppendText(string)
        return Saga.input(self, string, win)


class MainWindow(wx.Frame):
    def __init__(self, options, seed):
        super(MainWindow, self).__init__(None, size=(640, 480))
        self.dirname = '.'
        self.CreateInteriorWindowComponents()
        self.CreateExteriorWindowComponents()

        self.saga = WxSaga(self, options, seed)

    def OnControlKey(self, event):
        print(chr(event.GetKeyCode()))

    def CreateInteriorWindowComponents(self):
        ''' Create "interior" window components. In this case it is just a
            simple multiline text control. '''
        self.control = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.control.Bind(wx.EVT_CHAR, self.OnControlKey)

    def CreateExteriorWindowComponents(self):
        ''' Create "exterior" window components, such as menu and status
            bar. '''
        self.CreateMenu()
        self.CreateStatusBar()
        self.SetTitle()

    def CreateMenu(self):
        fileMenu = wx.Menu()
        for id, label, helpText, handler in \
            [(wx.ID_ABOUT, '&About', 'Information about this program',
                self.OnAbout),
             (wx.ID_OPEN, '&Open', 'Open a new database', self.OnOpen),
           # (wx.ID_RESTORE, '&Restore', 'Restore the current game', self.OnSave),
             (wx.ID_SAVE, '&Save', 'Save the current game', self.OnSave),
             (None, None, None, None),
             (wx.ID_EXIT, 'E&xit', 'Terminate the program', self.OnExit)]:
            if id is None:
                fileMenu.AppendSeparator()
            else:
                item = fileMenu.Append(id, label, helpText)
                self.Bind(wx.EVT_MENU, handler, item)

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, '&File')  # Add the fileMenu to the MenuBar
        self.SetMenuBar(menuBar)  # Add the menuBar to the Frame

    def SetTitle(self):
        # MainWindow.SetTitle overrides wx.Frame.SetTitle, so we have to
        # call it using super:
        super(MainWindow, self).SetTitle('PyScottFree')

    # Helper methods:

    def defaultFileDialogOptions(self):
        ''' Return a dictionary with file dialog options that can be
            used in both the save file dialog as well as in the open
            file dialog. '''
        return dict(message='Choose a file', defaultDir=self.dirname,
                    wildcard='*.*')

    def askUserForFilename(self, **dialogOptions):
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

    def OnAbout(self, event):
        dialog = wx.MessageDialog(
            self,
            self.saga.greeting(),
            'About PyScottFree',
            wx.OK
        )
        dialog.ShowModal()
        dialog.Destroy()

    def OnExit(self, event):
        self.Close()  # Close the main window.

    def OnSave(self, event):
        textfile = open(os.path.join(self.dirname, self.filename), 'w')
        textfile.write(self.control.GetValue())
        textfile.close()

    def OnOpen(self, event):
        if self.askUserForFilename(style=wx.OPEN, **self.defaultFileDialogOptions()):
            with open(os.path.join(self.dirname, self.filename), 'r') as file:
                self.saga.load_database(file)

            self.saga.game_loop(1)

    def OnSaveAs(self, event):
        if self.askUserForFilename(defaultFile=self.filename, style=wx.SAVE,
                                   **self.defaultFileDialogOptions()):
            self.OnSave(event)

if __name__ == '__main__':
    from pyscottfree import get_options

    (options, seed, args) = get_options(sys.argv)
    app = wx.App()
    frame = MainWindow(options, seed)
    if len(args) > 0:
        with open(args[0], 'r') as file:
            frame.saga.load_database(file)
    frame.Show()
    app.MainLoop()
