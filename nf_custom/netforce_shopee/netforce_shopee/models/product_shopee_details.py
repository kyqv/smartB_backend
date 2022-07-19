from netforce.model import Model, fields, get_model
from netforce import access
from netforce import config
from netforce import utils
import time
import requests
import hashlib
import hmac


class ShopeeCategs(Model):
    _name = "product.shopee.details"
    _fields = {
        "product_id": fields.Many2One("product","Product",required=True),
        "account_id": fields.Many2One("shopee.account","Shopee Account",required=True),
        "name": fields.Char("Name"),
        "description": fields.Char("Description"),
        "categ_id": fields.Many2One("product.categ","Product Category"),
        "brand_id": fields.Many2One("product.brand","Product Brand"),
        "ship_methods": fields.Many2Many("ship.method","Shipping Methods"),
    }


ShopeeCategs.register()
