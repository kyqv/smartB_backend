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


class PurchaseRequestLine(Model):
    _name = "purchase.request.line"
    _fields = {
        "request_id": fields.Many2One("purchase.request", "Purchase Request", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product"),
        "description": fields.Text("Description", required=True),
        "qty": fields.Decimal("Request Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "Location", condition=[["type", "=", "internal"]]),
        "purchase_order_id": fields.Many2One("purchase.order", "Purchase Order"),
        "supplier_id": fields.Many2One("contact", "Supplier"),
        "qty_order": fields.Decimal("Order Qty", function="get_qty_order"),
        "customer_id": fields.Many2One("contact","Customer"),
        "index": fields.Integer("Index",function="get_index"),
        "notes": fields.Text("Notes"),
        "department_id": fields.Many2One("hr.department", "Department", search=True),
    }

    def get_qty_order(self,ids,context={}):
        purch_ids=[]
        for obj in self.browse(ids):
            if obj.purchase_id:
                purch_ids.append(obj.purchase_id.id)
            if obj.request_id.purchase_id:
                purch_ids.append(obj.request_id.purchase_id.id)
        purch_ids=list(set(purch_ids))
        prod_qtys={}
        for purch in get_model("purchase.order").browse(purch_ids):
            for line in purch.lines:
                prod_qtys.setdefault(line.product_id.id,0)
                prod_qtys[line.product_id.id]+=line.qty
        vals={}
        for line in self.browse(ids):
            vals[obj.id]=prod_qtys.get(line.product_id.id) or 0 if line.product_id else None
        return vals

    def get_index(self,ids,context={}):
        request_ids=[]
        for obj in self.browse(ids):
            request_ids.append(obj.request_id.id)
        request_ids=list(set(request_ids))
        vals={}
        for req in get_model("purchase.request").browse(request_ids):
            i=1
            for line in req.lines:
                if line.id in ids:
                    vals[line.id]=i
                i+=1
        return vals

PurchaseRequestLine.register()
