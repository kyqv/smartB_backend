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
from decimal import *


class FulfillmentBillLine(Model):
    _name = "fulfillment.bill.line"
    _string="Fulfillment Billing Line"
    _fields = {
        "fulfillment_id": fields.Many2One("fulfillment.bill", "Fulfillment Billing", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product",condition=[["type","=","service"]],search=True),
        "description": fields.Text("Description"),
        "qty": fields.Decimal("Qty"),
        "qty2": fields.Decimal("Qty2"),
        "uom_id": fields.Many2One("uom", "UoM"),
        "uom2_id": fields.Many2One("uom", "UoM2"),
        "unit_price": fields.Decimal("Unit Price", scale=6),
        "discount": fields.Decimal("Disc %"),
        "discount_amount": fields.Decimal("Disc Amt"),  
        "amount": fields.Decimal("Amount", required=True),
        #"date": fields.Date("Date", function="_get_related", function_search="_search_related", function_context={"path": "invoice_id.date"}, search=True),
        #"invoice_state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Waiting Approval"), ("waiting_payment", "Waiting Payment"), ("paid", "Paid"), ("voided", "Voided"), ("repeat","Repeating")], "Status", function="_get_related", function_search="_search_related", search=True, function_context={"path": "invoice_id.state"}),
    }
    _order="id"

FulfillmentBillLine.register()
