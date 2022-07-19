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
from netforce.database import get_connection
from netforce.model import get_model
import curses
import curses.textpad

class StockCount(NFView):
    _name="stock_count"

    def __init__(self,opts):
        super().__init__(opts)
        self.data={
            "location_id": None,
            "lines": [],
        }
        self.pos=0

    def render(self):
        self.win.clear()
        curses.curs_set(0)
        self.win.addstr(0,0,"Netforce Terminal",curses.A_BOLD|curses.color_pair(1))
        self.win.addstr(1,0,"Make Stock Count",curses.A_BOLD)
        opts={
            "win": self.win.subwin(1,80,3,0),
            "key": 1,
            "string": "Location",
            "name": "location_id",
            "relation": "stock.location",
            "condition": [["type","=","internal"]],
            "data": self.data,
        }
        self.subviews["location_id"]=make_view("field_m2o",opts)
        self.win.addstr(4,0,"2.",curses.A_BOLD|curses.color_pair(2))
        self.win.addstr(4,3,"Add Product")
        self.win.addstr(5,0,"3.",curses.A_BOLD|curses.color_pair(2))
        self.win.addstr(5,3,"Validate Stock Count")
        self.win.addstr(7,0,"Count Products:")
        self.win.refresh()
        h,w=self.win.getmaxyx()
        self.list_win=self.win.subwin(h-9,w,9,0)
        self.render_items()
        for n,view in self.subviews.items():
            view.render()

    def render_items(self):
        self.list_win.clear()
        if self.data["lines"]:
            i=0
            for line in self.data["lines"]:
                self.list_win.addstr(i,0,"%s %s %s"%(line["product_id"][1],line["lot_no"] or "/",line["qty"]),curses.A_BOLD if i==self.pos else 0)
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
                    self.subviews["location_id"].focus()
                    self.render()
                elif c==ord("2"):
                    if not self.data["location_id"]:
                        raise Exception("Missing location")
                    opts={
                        "window": self.win,
                        "data": self.data,
                    }
                    v=make_view("add_product",opts)
                    v.render()
                    line_vals=v.focus()
                    if line_vals:
                        line_vals["new_qty"]=line_vals["qty"]
                        with Transaction():
                            line_vals["prev_qty"]=get_model("stock.balance").get_qty_phys(self.data["location_id"][0],line_vals["product_id"][0])
                        self.data["lines"].append(line_vals)
                    self.render()
                elif c==ord("3"):
                    self.validate()
                    return
                elif c==curses.KEY_DOWN:
                    if self.pos<len(self.data["lines"])-1:
                        self.pos+=1
                        self.render_items()
                elif c==curses.KEY_UP:
                    if self.pos>0:
                        self.pos-=1
                        self.render_items()
                elif c==curses.KEY_BACKSPACE or c==curses.KEY_DC:
                    if self.data["lines"]:
                        del self.data["lines"][self.pos]
                    self.render_items()
            except Exception as e:
                make_view("error",{"message": str(e)}).focus()
                self.render()

    def validate(self):
        with Transaction():
            if not self.data["location_id"]:
                raise Exception("Missing location")
            vals={
                "location_id": self.data["location_id"][0],
                "lines": [],
            }
            for line in self.data["lines"]:
                prod_id=line["product_id"][0]
                prod=get_model("product").browse(prod_id)
                line_vals={
                    "product_id": prod.id,
                    "prev_qty": line["prev_qty"],
                    "new_qty": line["new_qty"],
                    "uom_id": prod.uom_id.id,
                }
                vals["lines"].append(("create",line_vals))
            if not vals["lines"]:
                raise Exception("Empty stock count")
            count_id=get_model("stock.count").create(vals)
            get_model("stock.count").validate([count_id])
            count=get_model("stock.count").browse(count_id)
            msg="Stock count %s created successfully"%count.number
            make_view("message",{"message":msg}).focus()
            self.render()

StockCount.register()
