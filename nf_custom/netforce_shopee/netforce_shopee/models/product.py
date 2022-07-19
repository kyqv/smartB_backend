from netforce.model import Model, fields, get_model
from netforce import access
from netforce import config
from netforce import utils
import time
import requests
import hashlib
import hmac
import json

class Product(Model):
    _inherit = "product"
    _fields = {
        "shopee_details": fields.One2Many("product.shopee.details","product_id","Shopee Details"),
        "shopee_sync_stock": fields.Boolean("Shopee Sync Stock On"),
        "sync_records": fields.One2Many("sync.record","related_id","Sync Records"),
    }


    def update_shopee_stock(self,ids,context={}):
        print("Update Shopee Stock",ids)
        pass

    def update_shopee_stock_async(self,ids,context={}):
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "product",
            "method": "update_shopee_stock",
            "args": json.dumps({
                "ids": ids,
            }),
        }
        get_model("bg.task").create(vals)

Product.register()
