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
from netforce import database
from netforce.database import get_active_db
import os.path
from PIL import Image, ImageChops


class Product(Model):
    _inherit = "product"
    _fields = {
        "review": fields.One2Many("ecom.product.review", "product_id", "Product Review"),
        "wishlist": fields.One2Many("ecom.wishlist", "product_id", "Wishlist"),
        "has_sample": fields.Boolean("Has Sample", function="check_sample"),
        "avg_rate": fields.Integer("Average Rating", function="get_rating"),
    }

    def check_sample(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            product = obj
            sample = False
            for img in product.images:
                if img.title:
                    if "SAMPLE_OPTS_" in img.title:
                        sample = True
            vals[obj.id] = sample
        return vals

    def get_rating(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            score = []
            for review in get_model("ecom.product.review").search_browse([["product_id","=",obj.id],["state","=","approved"]]):
                score.append(int(review.rating or 0))
            vals[obj.id] = sum(score)/len(score) if score else 0
        return vals

Product.register()
