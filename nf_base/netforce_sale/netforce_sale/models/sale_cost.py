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
from netforce.utils import get_data_path
import time


class SaleCost(Model):
    _name = "sale.cost"
    _string = "Cost"
    _fields = {
        "sale_id": fields.Many2One("sale.order","Sales Order",required=True,on_delete="cascade"),
        "sequence": fields.Char("Apply To Item No."),
        "product_id": fields.Many2One("product","Cost Product"),
        "description": fields.Text("Description",required=True,search=True),
        "unit_price": fields.Decimal("Unit Price"), # XXX deprecated
        "list_price": fields.Decimal("Supplier List Price"),
        "purchase_price": fields.Decimal("Purchase Price"),
        "purchase_duty_percent": fields.Decimal("Import Duty (%)"),
        "purchase_ship_percent": fields.Decimal("Shipping Charge (%)"),
        "landed_cost": fields.Decimal("Landed Cost"),
        "qty": fields.Decimal("Qty"),
        "uom_id": fields.Many2One("uom","UoM"), # XXX deprecated
        "amount": fields.Decimal("Cost Amount",function="get_amount"),
        "currency_id": fields.Many2One("currency","Currency"),
        "currency_rate": fields.Decimal("Currency Rate"), # XXX: deprecated
        "supplier_id": fields.Many2One("contact","Supplier"),
    }

    def get_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.qty or 0)*(obj.landed_cost or 0)
        return vals

SaleCost.register()
