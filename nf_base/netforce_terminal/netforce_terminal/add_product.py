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

class AddProduct(NFView):
    _name="add_product"

    def __init__(self,opts):
        super().__init__(opts)
        self.data={
            "product_id": None,
            "lot_no": None,
            "qty": None,
            "uom_id": None,
            "prev_product_id": opts.get("prev_product_id"),
        }

    def render(self):
        with Transaction():
            self.win.clear()
            curses.curs_set(0)
            self.win.addstr(0,0,"Netforce Terminal",curses.A_BOLD|curses.color_pair(1))
            self.win.addstr(1,0,"Add Product",curses.A_BOLD)
            opts={
                "win": self.win.subwin(1,80,3,0),
                "key": 1,
                "string": "Product",
                "name": "product_id",
                "relation": "product",
                "data": self.data,
                "name_field": "code",
            }
            self.subviews["product_id"]=make_view("field_m2o",opts)
            opts={
                "win": self.win.subwin(1,80,4,0),
                "key": "2",
                "string": "Lot Number",
                "name": "lot_no",
                "data": self.data,
            }
            self.subviews["lot_no"]=make_view("field_char",opts)
            opts={
                "win": self.win.subwin(1,80,5,0),
                "key": "3",
                "string": "Qty",
                "name": "qty",
                "data": self.data,
            }
            if self.data["product_id"]:
                prod_id=self.data["product_id"][0]
                prod=get_model("product").browse(prod_id)
                opts["string"]="Qty (%s)"%prod.uom_id.name
            self.subviews["qty"]=make_view("field_decimal",opts)
            self.win.addstr(6,0,"4.",curses.A_BOLD|curses.color_pair(2))
            self.win.addstr(6,3,"Add Product")
            if self.data.get("prev_product_id"):
                self.win.addstr(7,0,"5.",curses.A_BOLD|curses.color_pair(2))
                self.win.addstr(7,3,"Select Previous Product")
            for n,view in self.subviews.items():
                view.render()

    def focus(self):
        while True:
            c=self.win.getch()
            try:
                if c==27:
                    return
                elif c==ord("1"):
                    self.subviews["product_id"].focus()
                    self.render()
                elif c==ord("2"):
                    self.subviews["lot_no"].focus()
                    self.render()
                elif c==ord("3"):
                    self.subviews["qty"].focus()
                    self.render()
                elif c==ord("4"):
                    if not self.data["product_id"]:
                        raise Exception("Missing product")
                    if not self.data["qty"]:
                        raise Exception("Missing qty")
                    return self.data
                elif c==ord("5"):
                    self.data["product_id"]=self.data["prev_product_id"]
                    self.render()
            except Exception as e:
                make_view("error",{"message": str(e)}).focus()
                self.render()

AddProduct.register()
