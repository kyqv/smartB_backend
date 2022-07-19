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


class CustomOption(Model):
    _name = "product.custom.option"
    _string = "Custom Option"
    _key = ["code"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True, translate=True),
        "seq": fields.Char("Sequence", required=True),
        "code": fields.Char("Code", search=True),
        "type": fields.Selection([["text", "Text"], ["selection", "Selection"]], "Type", required=True),
        "required": fields.Boolean("Required"),
        "description": fields.Text("Description"),
        "price": fields.Decimal("Price"),
        "values": fields.One2Many("product.custom.option.value", "cust_opt_id", "Values"),
    }
    _defaults = {
        "type": "text",
        "seq": '0',
    }

CustomOption.register()
