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
from netforce import access
import time


class ProductWaste(Model):
    _name = "product.waste"
    _string = "Product Waste"
    _name_field="number"
    _fields = {
        "number": fields.Char("Number",required=True,search=True),
        "date": fields.Date("Date",required=True,search=True),
        "location_id": fields.Many2One("stock.location","Location",required=True,search=True,condition=[["type","=","internal"]]),
        "product_id": fields.Many2One("product","Product",required=True,search=True,condition=[["type","=","stock"]]),
        "lot_id": fields.Many2One("stock.lot","Lot / Serial No.",search=True),
        "qty": fields.Decimal("Waste Qty",required=True),
        "uom_id": fields.Many2One("uom","UoM",required=True),
        "user_id": fields.Many2One("base.user","User"),
        "state": fields.Selection([["draft","Draft"],["done","Completed"],["voided","Voided"]],"Status",required=True,search=True),
        "notes": fields.Text("Notes",search=True),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
    }
    _order = "date desc,id desc"

    def _get_number(self, context={}):
        journal_id = context.get("journal_id")
        seq_id = None
        if journal_id:
            journal = get_model("stock.journal").browse(journal_id)
            seq_id = journal.sequence_id.id
        if not seq_id:
            seq_id = get_model("sequence").find_sequence(type="waste",context=context)
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            user_id = access.get_active_user()
            access.set_active_user(1)
            res = self.search([["number", "=", num]])
            access.set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults={
        "number": _get_number,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "state": "draft",
    }

    def onchange_product(self,context={}):
        data=context["data"]
        prod_id=data["product_id"]
        prod=get_model("product").browse(prod_id)
        data["uom_id"]=prod.uom_id.id
        return data

    def validate(self,ids,context={}):
        obj=self.browse(ids[0])
        settings=get_model("settings").browse(1)
        loc_from_id=obj.location_id.id
        res=get_model("stock.location").search([["type","=","waste"]])
        if not res:
            raise Exception("Waste location not found")
        loc_to_id=res[0]
        journal_id=settings.waste_journal_id.id
        if not journal_id:
            raise Exception("Waste journal not found")
        vals={
            "journal_id": journal_id,
            "product_id": obj.product_id.id,
            "lot_id": obj.lot_id.id,
            "qty": obj.qty,
            "uom_id": obj.uom_id.id,
            "location_from_id": loc_from_id,
            "location_to_id": loc_to_id,
            "related_id": "product.waste,%s"%obj.id,
        }
        move_id=get_model("stock.move").create(vals)
        get_model("stock.move").set_done([move_id])
        obj.write({"state":"done"})

    def to_draft(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.stock_moves.delete()
        obj.write({"state":"draft"})

    def void(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.stock_moves.delete()
        obj.write({"state":"voided"})

    def delete(self,ids,context={}):
        for obj in self.browse(ids):
                raise Exception("Can not delete waste products in this status")
        super().delete(ids,context=context)

ProductWaste.register()
