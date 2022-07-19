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


class Packaging(Model):
    _name = "stock.packaging"
    _string = "Packaging"
    _fields = {
        "name": fields.Char("Name", required=True),
        "code": fields.Char("Code"),
        "description": fields.Text("Description"),
        "width": fields.Decimal("Width"),
        "height": fields.Decimal("Height"),
        "length": fields.Decimal("Length"),
        "net_weight": fields.Decimal("Net Weight"),
        "packaging_weight": fields.Decimal("Packaging Weight"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "product_id": fields.Many2One("product","Product"),
        "num_items": fields.Integer("Number Of Items"),
    }
    _order = "name"

    def _get_code(self, context={}):
        seq_id = get_model("sequence").find_sequence(model=self._name,context=context)
        if not seq_id:
            return None
        while 1:
            code = get_model("sequence").get_next_number(seq_id,context=context)
            res = self.search([["code", "=", code]])
            if not res:
                return code
            get_model("sequence").increment_number(seq_id,context=context)

    _defaults = {
        "code": _get_code,
    }
    
Packaging.register()
