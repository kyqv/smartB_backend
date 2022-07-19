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

class Message(NFView):
    _name="message"

    def __init__(self,opts):
        super().__init__(opts)
        self.win=curses.newwin(40,80,0,0)
        self.win.bkgd(0,curses.color_pair(4))
        self.win.refresh()
        self.message=opts.get("message")

    def focus(self):
        self.fill()
        self.win.addstr(0,0,"Information",curses.A_BOLD)
        self.win.addstr(2,0,self.message[:80])
        while True:
            c=self.win.getch()
            if c in (27,10):
                return
        del self.win

    def fill(self):
        h,w=self.win.getmaxyx() 
        for y in range(h-1): 
            for x in range(w-1): 
                self.win.move(y, x) 
                self.win.addch(' ')

Message.register()
