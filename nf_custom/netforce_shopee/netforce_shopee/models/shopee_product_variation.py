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

class Variation(Model):
    _name = "shopee.product.variation"
    _string = "Shopee Product Variations"
    _name_field = "name"
    _fields = {
        "name": fields.Char("Name",required=True,search=True),
        "shopee_product_id": fields.Many2One("shopee.product","Shopee Product",required=True,search=True,on_delete="cascade"),
        "index": fields.Integer("Index",required=True),
        "option_list": fields.One2Many("shopee.product.variation.option","variation_id","Options"),
        "options": fields.Text("Options",function="get_options"),
    }
    _order = "name"

    def get_options(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            #vals[obj.id] = json.dumps([o.value for o in obj.option_list])
            vals[obj.id] = " | ".join([o.value for o in obj.option_list])
        return vals

Variation.register()
