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

class Menu(NFView):
    _name="menu"

    def render(self):
        self.win.clear()
        curses.curs_set(0)
        self.win.addstr(0,0,"Netforce Terminal",curses.A_BOLD|curses.color_pair(1))
        menu_items=[
            (1,"Check Product Stock"),
            (2,"Make Stock Count"),
            (3,"Receive From Supplier"),
            (4,"Return To Supplier"),
            (5,"Issue To Customer"),
            (6,"Return From Customer"),
            (7,"Transfer To Production"),
            (8,"Receive From Production"),
            (9,"Transfer Products"),
            (0,"Exit"),
        ]
        y=2
        for i,item in menu_items:
            self.win.addstr(y,0,"%d."%i,curses.A_BOLD|curses.color_pair(2))
            self.win.addstr(y,3,item)
            y+=1
        self.win.refresh()

    def focus(self):
        while True:
            c=self.win.getch()
            if c==ord("1"):
                opts={
                    "win": self.win,
                }
                v=make_view("check_stock",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("2"):
                opts={
                    "win": self.win,
                }
                v=make_view("stock_count",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("3"):
                opts={
                    "win": self.win,
                }
                v=make_view("receive_sup",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("4"):
                opts={
                    "win": self.win,
                }
                v=make_view("return_sup",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("5"):
                opts={
                    "win": self.win,
                }
                v=make_view("issue_cust",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("6"):
                opts={
                    "win": self.win,
                }
                v=make_view("return_cust",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("7"):
                opts={
                    "win": self.win,
                }
                v=make_view("transfer_mfg",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("8"):
                opts={
                    "win": self.win,
                }
                v=make_view("receive_mfg",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("9"):
                opts={
                    "win": self.win,
                }
                v=make_view("transfer",opts)
                v.render()
                v.focus()
                self.render()
            elif c==ord("0"):
                return

Menu.register()
