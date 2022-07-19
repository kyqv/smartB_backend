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

class ReceiveSup(NFView):
    _name="receive_sup"

    def __init__(self,opts):
        super().__init__(opts)
        self.data={
            "purchase_id": None,
            "invoice_id": None,
            "location_id": None,
            "lines": [],
        }
        self.pos=0
        self.prev_product_id=None

    def render(self):
        self.win.clear()
        curses.curs_set(0)
        self.win.addstr(0,0,"Netforce Terminal",curses.A_BOLD|curses.color_pair(1))
        self.win.addstr(1,0,"Receive From Supplier",curses.A_BOLD)
        opts={
            "win": self.win.subwin(1,80,3,0),
            "key": 1,
            "string": "Purchase Order",
            "name": "purchase_id",
            "relation": "purchase.order",
            "condition": [["state","=","confirmed"]],
            "data": self.data,
        }
        self.subviews["purchase_id"]=make_view("field_m2o",opts)
        opts={
            "win": self.win.subwin(1,80,4,0),
            "key": 2,
            "string": "Invoice",
            "name": "invoice_id",
            "relation": "account.invoice",
            "condition": [["state","in",["waiting_payment","paid"]]],
            "data": self.data,
        }
        self.subviews["invoice_id"]=make_view("field_m2o",opts)
        opts={
            "win": self.win.subwin(1,80,5,0),
            "key": 3,
            "string": "To Location",
            "name": "location_id",
            "relation": "stock.location",
            "condition": [["type","=","internal"]],
            "data": self.data,
        }
        self.subviews["location_id"]=make_view("field_m2o",opts)
        self.win.addstr(6,0,"4.",curses.A_BOLD|curses.color_pair(2))
        self.win.addstr(6,3,"Add Product")
        self.win.addstr(7,0,"5.",curses.A_BOLD|curses.color_pair(2))
        self.win.addstr(7,3,"Validate Goods Receipt")
        self.win.addstr(9,0,"Received Products:")
        self.win.refresh()
        h,w=self.win.getmaxyx()
        self.list_win=self.win.subwin(h-11,w,11,0)
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
                    self.subviews["purchase_id"].focus()
                    self.render()
                elif c==ord("2"):
                    self.subviews["invoice_id"].focus()
                    inv_id=self.data.get("invoice_id")
                    if inv_id:
                        with Transaction():
                            inv=get_model("account.invoice").browse(inv_id)
                            rel=inv.related_id
                            if rel and rel._model=="purchase.order":
                                self.data["purchase_id"]=rel.id
                    self.render()
                elif c==ord("3"):
                    self.subviews["location_id"].focus()
                    self.render()
                elif c==ord("4"):
                    opts={
                        "window": self.win,
                        "prev_product_id": self.prev_product_id,
                    }
                    v=make_view("add_product",opts)
                    v.render()
                    res=v.focus()
                    if res:
                        self.data["lines"].append(res)
                        self.prev_product_id=res["product_id"]
                    self.render()
                elif c==ord("5"):
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
            vals={
                "lines": [],
            }
            if self.data["purchase_id"]:
                vals["related_id"]="purchase.order,%d"%self.data["purchase_id"][0]
            res=get_model("stock.location").search([["type","=","supplier"]],order="id")
            if not res:
                raise Exception("Supplier location not found")
            supp_loc_id=res[0]
            if not self.data["location_id"]:
                raise Exception("Missing location")
            to_loc_id=self.data["location_id"][0]
            for line in self.data["lines"]:
                lot_no=line["lot_no"]
                if lot_no:
                    res=get_model("stock.lot").search([["number","=",lot_no]])
                    if res:
                        lot_id=res[0]
                    else:
                        lot_id=get_model("stock.lot").create({"number":lot_no})
                else:
                    lot_id=None
                prod_id=line["product_id"][0]
                prod=get_model("product").browse(prod_id)
                line_vals={
                    "product_id": prod.id,
                    "lot_id": lot_id,
                    "qty": line["qty"],
                    "uom_id": prod.uom_id.id,
                    "location_from_id": supp_loc_id,
                    "location_to_id": to_loc_id,
                }
                vals["lines"].append(("create",line_vals))
            if not vals["lines"]:
                raise Exception("Empty goods receipt")
            pick_id=get_model("stock.picking").create(vals,context={"pick_type":"in"})
            get_model("stock.picking").set_done([pick_id])
            pick=get_model("stock.picking").browse(pick_id)
            msg="Goods receipt %s created successfully"%pick.number
            make_view("message",{"message":msg}).focus()
            self.render()

ReceiveSup.register()
