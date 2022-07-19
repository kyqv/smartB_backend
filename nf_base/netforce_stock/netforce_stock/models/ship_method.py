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


class ShipMethod(Model):
    _name = "ship.method"
    _string = "Shipping Method"
    #_key = ["code"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True, translate=True),
        "code": fields.Char("Code", search=True),
        "description": fields.Text("Description", search=True, translate=True),
        "rates": fields.One2Many("ship.rate", "method_id", "Shipping Rates"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "sequence": fields.Integer("Sequence"),
        "type": fields.Selection([],"Type"),
        "ship_product_id": fields.Many2One("product","Shipping Product"),
        "exclude_ship_methods": fields.Many2Many("ship.method", "Exclude Shipping Methods", reltable="m2m_ship_method_exclude", relfield="method1_id", relfield_other="method2_id"),
        "active": fields.Boolean("Active"),
        "ship_amount": fields.Decimal("Shipping Amount",function="get_ship_amount"),
    }
    _order = "sequence"
    _defaults = {
        "active": True,
    }

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.code:
                name = "[%s] %s" % (obj.code, obj.name)
            else:
                name = obj.name
            vals.append((obj.id, name, obj.image))
        return vals

    def create_delivery_order(self,ids,context={}):
        pass

    def get_ship_amount(self,ids,context={}):
        vals={}
        contact_id=context.get("contact_id")
        contact=get_model("contact").browse(contact_id) if contact_id else None
        addr_id=context.get("ship_address_id")
        if addr_id:
            addr=get_model("address").browse(addr_id)
        else:
            addr=None
        order_amount=context.get("order_amount")
        order_weight=context.get("order_weight")
        for obj in self.browse(ids):
            if contact and contact.ship_free:
                vals[obj.id]=0
                continue
            amt = None
            for rate in obj.rates:
                #print("try rate",rate.id)
                if rate.country_id and (not addr or addr.country_id.id!=rate.country_id.id):
                    #print("  skip country")
                    continue
                if rate.province_id and (not addr or addr.province_id.id!=rate.province_id.id):
                    #print("  skip province (%s / %s %s)"%(rate.province_id.id,addr.id,addr.province_id.id if addr else None))
                    continue
                if rate.district_id and (not addr or addr.district_id.id!=rate.district_id.id):
                    #print("  skip district")
                    continue
                if rate.postal_code and (not addr or addr.postal_code!=rate.postal_code):
                    #print("  skip postal code")
                    continue
                if rate.address_name and (not addr or addr.name!=rate.address_name):
                    #print("  skip address name")
                    continue
                if rate.min_amount and (order_amount is None or order_amount<rate.min_amount):
                    #print("  skip min amount")
                    continue
                if rate.min_weight and (order_weight is None or order_weight<rate.min_weight):
                    #print("  skip min weight")
                    continue
                #print("  OK ship_price=%s"%rate.ship_price)
                if amt is None or rate.ship_price < amt:
                    amt = rate.ship_price
            #if amt is not None:
                #print("=> shipping price found: %s"%amt)
            #else:
                #print("=> no shipping price found")
            vals[obj.id]=amt
        return vals

ShipMethod.register()
