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
from datetime import *
import time


class Target(Model):
    _name = "mkt.target"
    _string = "Target"
    _name_field = "last_name"
    _fields = {
        "list_id": fields.Many2One("mkt.target.list", "Target List", required=True, on_delete="cascade"),
        "date": fields.Date("Date Created", required=True, search=True),
        "first_name": fields.Char("First Name", search=True),
        "last_name": fields.Char("Last Name", search=True),
        "company": fields.Char("Company", size=256, search=True),
        "email": fields.Char("Email", search=True),
        "street": fields.Char("Street"),
        "city": fields.Char("City"),
        "province_id": fields.Many2One("province", "Province", search=True),
        "zip": fields.Char("Zip"),
        "country_id": fields.Many2One("country", "Country", search=True),
        "phone": fields.Char("Phone"),
        "fax": fields.Char("Fax"),
        "mobile": fields.Char("Mobile"),
        "website": fields.Char("Website"),
        "birthday":  fields.Date("Birthday"),
        "target_life": fields.Integer("Target Life (days)", function="get_life"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "email_status": fields.Selection([["error_syntax", "Syntax Error"], ["error_dns", "DNS Error"], ["error_smtp", "SMTP Error"], ["verified", "Verified"]], "Email Status", search=True, readonly=True),
        "email_error": fields.Text("Email Error Details", readonly=True),
    }
    _order = "date desc"
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.first_name:
                name = obj.first_name + " " + obj.last_name
            else:
                name = obj.last_name
            vals.append((obj.id, name))
        return vals

    def get_life(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = (datetime.today() - datetime.strptime(obj.date, "%Y-%m-%d")).days if obj.date else None
        return vals

Target.register()
