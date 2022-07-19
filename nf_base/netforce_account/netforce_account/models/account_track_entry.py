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

from netforce.model import Model, fields, get_model
import time
from netforce import database


class TrackEntry(Model):
    _name = "account.track.entry"
    _string = "Tracking Entries"
    _fields = {
        "track_id": fields.Many2One("account.track.categ", "Tracking Category",required=True,on_delete="cascade"),
        "date": fields.Date("Date",required=True),
        "amount": fields.Decimal("Amount",required=True),
        "product_id": fields.Many2One("product","Product"),
        "contact_id": fields.Many2One("contact","Contact"),
        "description": fields.Text("Description"),
        "qty": fields.Decimal("Qty"),
        "uom_id": fields.Many2One("uom","UoM"),
        "unit_price": fields.Decimal("Unit Price"),
        "related_id": fields.Reference([["account.invoice","Invoice"],["stock.picking","Stock Picking"],["work.time","Work Time"],["expense.claim","Expense Claim"],["nd.order","Delivery Order"]],"Related To"),
        "move_id": fields.Many2One("account.move","Journal Entry"),
        "invoice_id": fields.Many2One("account.invoice","Invoice"),
    }
    _order = "date desc,id desc"
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def onchange_product(self,context={}):
        data=context.get("data",{})
        print("#"*80)
        print("ID",data.get("id"))
        prod_id=data["product_id"]
        if not prod_id:
            return
        prod=get_model("product").browse(prod_id)
        price=prod.cost_price
        track_id=data["track_id"]
        track=get_model("account.track.categ").browse(track_id)
        if track.currency_id:
            settings=get_model("settings").browse(1)
            price=get_model("currency").convert(price,settings.currency_id.id,track.currency_id.id)
        data["unit_price"]=-price
        data["qty"]=1
        data["uom_id"]=prod.uom_id.id
        data["amount"]=data["unit_price"]
        return data

    def update_amount(self,context={}):
        data=context.get("data",{})
        unit_price=data.get("unit_price",0)
        qty=data.get("qty",0)
        data["amount"]=unit_price*qty
        return data

    def copy_to_invoice(self,ids,context={}):
        contact_lines={}
        for obj in self.browse(ids):
            if obj.invoice_id:
                raise Exception("Entry is already invoiced")
            contact=obj.track_id.contact_id
            if not contact:
                raise Exception("Missing contact")
            contact_lines.setdefault(contact.id,[]).append(obj)
        for contact_id,lines in contact_lines.items():
            contact=get_model("contact").browse(contact_id)
            inv_vals={
                "contact_id": contact_id,
                "inv_type": "invoice",
                "lines": [],
            }
            if contact.customer:
                inv_vals["type"]="out"
            elif contact.supplier:
                inv_vals["type"]="in"
            else:
                raise Exception("Contact is not a supplier or customer")
            for line in lines:
                prod=line.product_id
                line_vals={
                    "product_id": prod.id,
                    "description": line.description,
                }
                if inv_vals["type"]=="out":
                    line_vals["account_id"]=prod.sale_account_id.id if prod else None
                    line_vals["amount"]=line.amount
                elif inv_vals["type"]=="in":
                    line_vals["account_id"]=prod.purchase_account_id.id if prod else None
                    line_vals["amount"]=-line.amount
                inv_vals["lines"].append(("create",line_vals))
            inv_id=get_model("account.invoice").create(inv_vals,context={"type":inv_vals["type"],"inv_type":"invoice"})
            for line in lines:
                line.write({"invoice_id":inv_id})

TrackEntry.register()
