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

from netforce.model import Model, fields
import time


class EcomProductReview(Model):
    _name = "ecom.product.review"
    _string = "Product Review"
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "title": fields.Char("Title", required=True, search=True),
        "review": fields.Text("Review", required=True),
        "rating": fields.Selection([("0", "Not Rate"), ("1", "Bad"), ("2", "Poor"), ("3", "Regular"), ("4", "Good"), ("5", "Gorgeous")], "Rating"),
        "date": fields.DateTime("Date"),
        "state": fields.Selection([("draft", "Draft"), ("approved", "Approved"), ("discarded", "Discarded")], "State"),
        "product_id": fields.Many2One("product", "Product", required=True, search=True),
    }
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "draft",
        "rating": "0"
    }
    _order = "date desc"

    def create(self, vals, **kw):
        id = super().create(vals, **kw)
        for obj in self.browse([id]):
            obj.trigger("created")

    def approve_review(self, ids, context={}):
        self.write(ids, {"state": "approved"})

    def reset_draft(self, ids, context={}):
        self.write(ids, {"state": "draft"})

    def discard_review(self, ids, context={}):
        self.write(ids, {"state": "discarded"})

EcomProductReview.register()
