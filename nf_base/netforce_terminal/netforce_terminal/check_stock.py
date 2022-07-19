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
from netforce.database import Transaction
from netforce.model import get_model
import curses
import curses.textpad

class CheckStock(NFView):
    _name="check_stock"

    def __init__(self,opts):
        super().__init__(opts)
        self.data={
            "product_id": None,
            "location_id": None,
            "lines": [],
        }
        self.pos=0

    def render(self):
        self.win.clear()
        curses.curs_set(0)
        self.win.addstr(0,0,"Netforce Terminal",curses.A_BOLD|curses.color_pair(1))
        self.win.addstr(1,0,"Check Product Stock",curses.A_BOLD)
        opts={
            "win": self.win.subwin(1,80,3,0),
            "key": 1,
            "string": "Product",
            "name": "product_id",
            "relation": "product",
            "data": self.data,
        }
        self.subviews["product_id"]=make_view("field_m2o",opts)
        opts={
            "win": self.win.subwin(1,80,4,0),
            "key": 2,
            "string": "Location",
            "name": "location_id",
            "relation": "stock.location",
            "condition": [["type","=","internal"]],
            "data": self.data,
        }
        self.subviews["location_id"]=make_view("field_m2o",opts)
        self.win.addstr(5,0,"3.",curses.A_BOLD|curses.color_pair(2))
        self.win.addstr(5,3,"Check Stock")
        self.win.refresh()
        h,w=self.win.getmaxyx()
        self.list_win=self.win.subwin(h-7,w,7,0)
        self.render_items()
        for n,view in self.subviews.items():
            view.render()

    def render_items(self):
        self.list_win.clear()
        if self.data["lines"]:
            i=0
            for line in self.data["lines"]:
                self.list_win.addstr(i,0,"%s %s %s %s"%(line["location_id"][1],line["lot_id"][1] if line["lot_id"] else "/",line["qty_phys"],line["qty_virt"]),curses.A_BOLD if i==self.pos else 0)
                i+=1
        else:
            self.list_win.addstr(0,0,"There are no items to display.")
        self.list_win.refresh()

    def focus(self):
        while True:
            c=self.win.getch()
            try:
                if c==27:
                    return
                elif c==ord("1"):
                    self.subviews["product_id"].focus()
                    self.data["lines"]=[]
                    self.render()
                elif c==ord("2"):
                    self.subviews["location_id"].focus()
                    self.data["lines"]=[]
                    self.render()
                elif c==ord("3"):
                    self.check_stock()
                elif c==curses.KEY_DOWN:
                    if self.pos<len(self.data["lines"])-1:
                        self.pos+=1
                        self.render_items()
                elif c==curses.KEY_UP:
                    if self.pos>0:
                        self.pos-=1
                        self.render_items()
            except Exception as e:
                make_view("error",{"message": str(e)}).focus()
                self.render()

    def check_stock(self):
        with Transaction():
            if not self.data["product_id"]:
                raise Exception("Missing product")
            cond=[["product_id","=",self.data["product_id"][0]]]
            if self.data["location_id"]:
                cond.append(["location_id","=",self.data["location_id"][0]])
            self.data["lines"]=[]
            for bal in get_model("stock.balance").search_browse(cond):
                self.data["lines"].append({
                    "location_id": [bal.location_id.id,bal.location_id.name],
                    "lot_id": [bal.lot_id.id,bal.lot_id.number] if bal.lot_id else None,
                    "qty_phys": bal.qty_phys,
                    "qty_virt": bal.qty_virt,
                })
            self.render()

CheckStock.register()
