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

class ShopeeProduct(Model):
    _name = "shopee.product"
    _string = "Shopee Product"
    _name_field = "item_name"
    #_multi_company = True
    #_key = ["company_id", "number"]
    _fields = {
        "account_id": fields.Many2One("shopee.account","Shopee Account",search=True),
        "sync_id": fields.Char("Sync ID",search=True), #XXX
        "category_id": fields.Many2One("shopee.product.categ","Product Category",search=True), #XXX
        "item_name": fields.Char("Product Name",search=True),
        "description": fields.Text("Product Description", search=True),
        "item_sku": fields.Char("Parent SKU",search=True),
        "shopee_create_time": fields.DateTime("Shopee Create Time"), #XXX
        "shopee_update_time": fields.DateTime("Shopee Update Time"), #XXX
        "current_price": fields.Decimal("Current Price"),
        "normal_stock": fields.Decimal("Normal Stock"),
        "condition": fields.Selection("Condition",[["NEW","NEW"],["USED","USED"]]),
        "item_status": fields.Selection([["NORMAL","NORMAL"],["DELETED","DELETED"],["BANNED","BANNED"],["UNLIST","UNLIST"]],"Item Status",search=True),
        "has_model": fields.Boolean("Has Variants",search=True),
        "tier_variation": fields.One2Many("shopee.product.variation", "shopee_product_id", "Tier Variations"),
        "models": fields.One2Many("shopee.product.model", "shopee_product_id", "Variations"),
        "product_id": fields.Many2One("product","System Product",search=True),
        "show_warning": fields.Boolean("Show Warning", function="get_show_warning", store=True),
    }
    _order = "account_id, sync_id"

    def write(self, ids, vals, **kw):
        print("shopee.product.write",ids,vals)
        super().write(ids, vals, **kw)
        self.function_store(ids)

    def get_model_list(self, ids, context={}):
        print("shopee.product.get_model_list",ids)
        path = "/api/v2/product/get_model_list"
        for obj in self.browse(ids):
            url = get_model("shopee.account").generate_url(account_id=obj.account_id.id,path=path)
            print("url",url)
            url += "&item_id=%s" % obj.sync_id
            req = requests.get(url)
            res=req.json()
            if res.get("error"):
                raise Exception("Sync error: %s"%res)
            resp=res["response"]
            #print("resp",resp)
            vals = {}
            if resp.get("tier_variation"):
                var_ids = [var.id for var in obj.tier_variation]
                if var_ids:
                    get_model("shopee.product.variation").delete(var_ids)
                vals["tier_variation"] = []
                for i, v in enumerate(resp["tier_variation"]):
                    tier_var = {
                        "index": i,
                        "name": v["name"],
                        "option_list": [["create",{"index":oi,"value":ov.get("option")}] for oi, ov in enumerate(v["option_list"])],
                    }
                    vals["tier_variation"].append(["create",tier_var])
            if resp.get("model"):
                model_ids = [model.id for model in obj.models]
                if model_ids:
                    get_model("shopee.product.model").delete(model_ids)
                vals["models"] = []
                for m in resp["model"]:
                    print("add model",m)
                    model_vals = {
                        "sync_id": m["model_id"],
                        "model_sku": m.get("model_sku"),
                        "tier_index": json.dumps(m["tier_index"]),
                    }
                    if m.get("price_info"):
                        model_vals["current_price"] = m["price_info"][0]["current_price"]
                    if m.get("stock_info"):
                        for si in m["stock_info"]:
                            if si["stock_type"] == 2:
                                model_vals["normal_stock"] = si["normal_stock"]
                    vals["models"].append(["create",model_vals])
            print("vals",vals)
            obj.write(vals)
    
    def map_product(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.has_model:
                for model in obj.models:
                    if not model.model_sku:
                        continue
                    prod_ids = get_model("product").search([["code","=",model.model_sku.strip()]])
                    if prod_ids:
                        model.write({"product_id":prod_ids[0]})
            else:
                prod_ids = get_model("product").search([["code","=",obj.item_sku]])
                if prod_ids:
                    obj.write({"product_id":prod_ids[0]})
    
    def update_stock(self, ids, context={}):
        print("shopee.product.update_stock",ids)
        path = "/api/v2/product/update_stock"
        for obj in self.browse(ids):
            url = get_model("shopee.account").generate_url(account_id=obj.account_id.id,path=path)
            body={"item_id":obj.sync_id, "stock_list":[]}
            if not obj.has_model:
                stock_list.append({"model_id":0,"normal_stock": obj.normal_stock})
            else:
                for m in obj.models:
                    stock_list.append({"model_id":m.sync_id, "normal_stock": m.normal_stock})
            headers={"Content-Type":"application/json"}
            req=requests.post(url,json=body,headers=headers)
            res=req.json()
            print("res",res)

    def get_show_warning(self, ids, context={}):
        print("shopee.product.get_show_warning",ids)
        vals = {}
        for obj in self.browse(ids):
            if not obj.has_model:
                if obj.product_id:
                    vals[obj.id] = False
                else:
                    vals[obj.id] = True
            else:
                model_ids = [m.id for m in obj.models]
                get_model("shopee.product.model").function_store(model_ids)
                vals[obj.id] = False
                for m in obj.models:
                    if m.show_warning:
                        vals[obj.id] = True
        return vals

ShopeeProduct.register()
