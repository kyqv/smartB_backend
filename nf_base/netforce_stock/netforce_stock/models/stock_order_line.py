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


class StockOrderLine(Model):
    _name = "stock.order.line"
    _fields = {
        "order_id": fields.Many2One("stock.order","Order",required=True,on_delete="cascade"),
        "product_id": fields.Many2One("product","Product",required=True,on_delete="cascade"),
        "qty": fields.Decimal("Order Qty",required=True),
        "uom_id": fields.Many2One("uom","Order UoM",required=True),
        "date": fields.Date("Order Date",required=True),
        "supply_method": fields.Selection([["purchase", "Purchase"], ["production", "Production"]], "Supply Method", function="_get_related", function_context={"path":"product_id.supply_method"}),
        "supplier_id": fields.Many2One("contact","Supplier",function="get_supplier"),
    }

    def get_supplier(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=obj.product_id.suppliers[0].supplier_id.id if obj.product_id.suppliers else None
        return vals

StockOrderLine.register()
