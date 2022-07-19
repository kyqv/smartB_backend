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
from netforce.model import get_model
import curses
import curses.textpad

class TextBox(NFView):
    _name="textbox"

    def __init__(self,opts):
        self.win=opts["win"]
        self.cols=opts["cols"]
        self.value=""

    def process_key(self,c):
        if curses.ascii.isprint(c):
            if len(self.value)<self.cols:
                self.value+=chr(c)
        elif c==curses.KEY_BACKSPACE or c==curses.KEY_DC:
            self.value=self.value[:-1]
        self.win.addstr(0,0,self.value+" "*(self.cols-len(self.value)))
        self.win.refresh()

    def get_value(self):
        return self.value

TextBox.register()
