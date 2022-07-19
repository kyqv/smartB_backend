# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce_terminal.view import NFView,make_view
import curses
import curses.textpad

class FieldChar(NFView):
    _name="field_char"

    def __init__(self,opts):
        super().__init__(opts)
        self.key=opts["key"]
        self.string=opts["string"]
        self.data=opts["data"]
        self.name=opts["name"]

    def render(self):
        self.win.clear()
        self.win.addstr(0,0,"%s."%self.key,curses.A_BOLD|curses.color_pair(2))
        val=self.data.get(self.name)
        if val:
            self.win.addstr(0,3,"%s: %s"%(self.string,val))
        else:
            self.win.addstr(0,3,"Enter %s"%self.string)

    def focus(self):
        val=self.data.get(self.name) or ""
        self.win.clear()
        self.win.addstr(0,0,"%s."%self.key,curses.A_BOLD|curses.color_pair(2))
        self.win.addstr(0,3,"Enter %s: %s"%(self.string,val))
        curses.curs_set(1)
        val=""
        while True:
            c=self.win.getch()
            if c==27:
                return
            elif c==10:
                self.data[self.name]=val
                return
            elif curses.ascii.isprint(c):
                if len(val)<40:
                    val+=chr(c)
            elif c==curses.KEY_BACKSPACE or c==curses.KEY_DC or c==127: # XXX
                val=val[:-1]
            self.win.clear()
            self.win.addstr(0,0,"%s."%self.key,curses.A_BOLD|curses.color_pair(2))
            self.win.addstr(0,3,"Enter %s: %s"%(self.string,val))

FieldChar.register()
