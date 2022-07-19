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


class BankAccount(Model):
    _name = "bank.account"
    _name_field="number"
    _fields = {
        "bank_id": fields.Many2One("bank", "Bank", required=True),
        "branch": fields.Char("Branch"),
        "number": fields.Char("Account Number", required=True),
        "name": fields.Char("Account Name"),
        "signatory": fields.Char("Signatory"),
        "online": fields.Boolean("Online"),
        "contact_id": fields.Many2One("contact", "Contact", on_delete="cascade"),
        "related_id": fields.Reference([],"Related To"),
    }

    def name_get(self,ids,**kw):
        vals=[]
        for obj in self.browse(ids):
            s="%s %s %s"%(obj.bank_id.name,obj.number,obj.name)
            vals.append((obj.id,s))
        return vals

BankAccount.register()
