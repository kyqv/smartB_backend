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
from datetime import *
import time


class ShipRate(Model):
    _name = "ship.rate"
    _string = "Shipping Rate"
    _fields = {
        "sequence": fields.Char("Sequence", required=True, search=True),
        "method_id": fields.Many2One("ship.method", "Shipping Method", required=True, on_delete="cascade", search=True),
        "country_id": fields.Many2One("country", "Country", search=True),
        "province_id": fields.Many2One("province", "Province", search=True),
        "district_id": fields.Many2One("district", "District", search=True),
        "postal_code": fields.Char("Postal Code", search=True),
        "min_amount": fields.Decimal("Min Total Amount"),
        "min_weight": fields.Decimal("Min Total Weight (Kg)"),
        "address_name": fields.Char("Address Name",search=True),
        "ship_price": fields.Decimal("Shipping Price", required=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }

    def _get_number(self, context={}):
        while 1:
            seq = get_model("sequence").get_number("shipping_rates")
            if not seq:
                return None
            res = self.search([["sequence", "=", seq]])
            if not res:
                return seq
            get_model("sequence").increment("shipping_rates")

    _order = "sequence,method_id.name,country_id.name,province_id.name,postal_code,min_amount,min_weight,ship_price"

    _defaults = {
        "sequence": _get_number,
    }

ShipRate.register()
