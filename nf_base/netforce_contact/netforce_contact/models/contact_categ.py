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


class ContactCateg(Model):
    _name = "contact.categ"
    _string = "Contact Category"
    _key = ["code"]
    _name_field = "name"
    _fields = {
        "name": fields.Char("Category Name", required=True, search=True, translate=True),
        "code": fields.Char("Category Code", search=True),
        "parent_id": fields.Many2One("contact.categ", "Parent", search=True),
        "description": fields.Text("Description",translate=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "full_name": fields.Char("Full Name", function="get_full_name"),
        "account_receivable_id": fields.Many2One("account.account", "Account Receivable", multi_company=True),
        "account_payable_id": fields.Many2One("account.account", "Account Payable", multi_company=True),
        "sale_tax_id": fields.Many2One("account.tax.rate", "Sales Tax"),
        "purchase_tax_id": fields.Many2One("account.tax.rate", "Purchase Tax"),
        "sequence_id": fields.Many2One("sequence","Contact Sequence"),
        "sale_discount_percent": fields.Decimal("Sales Discount (%)"),
    }
    _order = "code"

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.code:
                name = "[%s] %s" % (obj.code, obj.name)
            else:
                name = obj.name
            vals.append((obj.id, name, obj.image))
        return vals

    def get_full_name(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            n = obj.name
            p = obj.parent_id
            i=0
            while p:
                n = p.name + " / " + n
                p = p.parent_id
                i+=1
                if i>=10:
                    break
            vals[obj.id] = n
        return vals

ContactCateg.register()
