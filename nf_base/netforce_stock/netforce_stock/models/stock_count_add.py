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


class StockCountAdd(Model):
    _name = "stock.count.add"
    _transient = True
    _fields = {
        "stock_count_id": fields.Many2One("stock.count","Stock Count",required=True,on_delete="cascade"),
        "product_id": fields.Many2One("product","Product"),
        "categ_id": fields.Many2One("product.categ","Product Category"),
        "sale_invoice_uom_id": fields.Many2One("uom","Sales Invoice UoM"),
        "lot_type": fields.Selection([["with_lot","With Lot"],["without_lot","Without Lot"]],"Lot Type"),
        "qty_type": fields.Selection([["previous","Copy Previous Qty"],["reset","Set Qty To Zero"]],"New Qty"),
        "price_type": fields.Selection([["previous","Copy Previous Cost Price"],["product","Copy Cost Price From Product"],["reset","Set Cost Price To Zero"]],"New Cost Price"),
    }
    _defaults={
        "stock_count_id": lambda self,ctx: ctx["refer_id"],
    }

    def add_lines(self,ids,context={}):
        obj=self.browse(ids[0])
        ctx={
            "product_id": obj.product_id.id,
            "categ_id": obj.categ_id.id,
            "sale_invoice_uom_id": obj.sale_invoice_uom_id.id,
            "lot_type": obj.lot_type,
            "qty_type": obj.qty_type,
            "price_type": obj.price_type,
        }
        ctx.update(context)
        obj.stock_count_id.add_lines(context=ctx)
        return {
            "next": {
                "name": "stock_count",
                "mode": "form",
                "active_id": obj.stock_count_id.id,
            },
        }

StockCountAdd.register()
