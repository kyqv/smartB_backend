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
from netforce_terminal.utils import filter_chars
from netforce.database import Transaction
from netforce.model import get_model
import curses
import curses.textpad

class SelectItem(NFView):
    _name="select_item"

    def __init__(self,opts):
        super().__init__(opts)
        self.model=opts["model"]
        self.condition=opts["condition"]

    def render(self):
        with Transaction():
            self.win.clear()
            curses.curs_set(1)
            self.win.addstr(0,0,"Netforce Terminal",curses.A_BOLD|curses.color_pair(1))
            s=get_model(self.model)._string
            self.win.addstr(1,0,"Select %s"%s,curses.A_BOLD)
            self.win.addstr(3,0,"Search:")
            opts={
                "win": self.win.subwin(1,21,3,8),
                "cols": 20,
            }
            self.tb=make_view("textbox",opts)
            h,w=self.win.getmaxyx()
            self.list_win=self.win.subwin(h-5,w,5,0)
            self.load_items()
            self.render_items()

    def render_items(self):
        self.list_win.clear()
        if self.items:
            i=0
            for obj_id,name in self.items[:10]:
                self.list_win.addstr(i,0,filter_chars(name[:40]),curses.A_BOLD if i==self.pos else 0)
                i+=1
        else:
            self.list_win.addstr(0,0,"There are no items to display.")
        self.list_win.refresh()
        self.win.move(3,8+len(self.tb.get_value()))

    def focus(self,params={}):
        while True:
            c=self.win.getch()
            if c==27:
                return
            if c==10:
                if self.items:
                    obj_id=self.items[self.pos][0]
                    return {
                        "select_id": obj_id,
                    }
                else:
                    return {
                        "select_id": None
                    }
            elif c==curses.KEY_DOWN:
                if self.pos<len(self.items)-1:
                    self.pos+=1
                    self.render_items()
            elif c==curses.KEY_UP:
                if self.pos>0:
                    self.pos-=1
                    self.render_items()
            else:
                self.tb.process_key(c)
                self.load_items()
                self.render_items()

    def load_items(self):
        with Transaction():
            q=self.tb.get_value()
            self.items=get_model(self.model).name_search(q,condition=self.condition)
            self.pos=0

SelectItem.register()
