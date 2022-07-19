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
from netforce import database, access, config, utils
from netforce.access import get_active_user, set_active_user
from netforce.access import get_active_company
from datetime import *
import time
import requests
import hashlib
import hmac
import json

class ProductModel(Model):
    _name = "shopee.product.model"
    _string = "Shopee Product Model"
    _fields = {
        "sync_id": fields.Char("Model ID"), #XXX
        "shopee_product_id": fields.Many2One("shopee.product","Shopee Product",search=True),
        "model_sku": fields.Char("Model SKU",search=True),
        "current_price": fields.Decimal("Current Price"),
        #"stock_type": fields.Selection([["1","Shopee Warehouse Stock"],["2","Seller Stock"]],"Stock Type",search=True),
        "normal_stock": fields.Decimal("Normal Stock"),
        "product_id": fields.Many2One("product","System Product",search=True),
        "tier_index": fields.Text("Tier Index"),
        "tier_info": fields.Text("Tier Info", function="get_tier_info"),
        "show_warning": fields.Boolean("Show Warning", function="get_show_warning", store=True),
    }
    _order = "tier_index"

    def write(self, ids, vals, **kw):
        print("shopee.product.model.write",ids,vals)
        super().write(ids, vals, **kw)
        self.function_store(ids)

    def get_tier_info(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if not obj.tier_index:
                continue
            tiers = json.loads(obj.tier_index)
            infos = []
            for (i, tier) in enumerate(tiers):
                variations = get_model("shopee.product.variation").search_browse([["shopee_product_id","=",obj.shopee_product_id.id],["index","=",i]])
                if not variations:
                    break
                else:
                    variation = variations[0]
                options = get_model("shopee.product.variation.option").search_browse([["variation_id","=",variation.id],["index","=",tier]])
                if not options:
                    break
                else:
                    option = options[0]
                infos.append("%s: %s" %(variation.name, option.value))
            vals[obj.id] = '\n'.join(infos)
        return vals

    def get_show_warning(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.product_id:
                vals[obj.id] = False
            else:
                vals[obj.id] = True
        return vals



ProductModel.register()
