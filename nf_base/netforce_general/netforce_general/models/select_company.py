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
from netforce.access import get_active_company


class SelectCompany(Model):
    _name = "select.company"
    _transient = True
    _fields = {
        "company": fields.Selection([], "Company", required=True),
        "company_id": fields.Many2One("company", "Company"),  # XXX: not used any more (popup bug)
    }

    def _get_company(self, context):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        return comp.name

    _defaults = {
        #"company_id": lambda *a: get_active_company(),
        "company": _get_company,
    }

    def get_companies(self, context={}):
        res = get_model("company").search_read([], ["name"],context={"no_translate":True})
        return [(r["name"], r["name"]) for r in res]

    def select(self, ids, context={}):
        obj = self.browse(ids)[0]
        res = get_model("company").search([["name", "=", obj.company]])
        if not res:
            raise Exception("Company not found: %s"%obj.company)
        company_id = res[0]
        comp = get_model("company").browse(company_id)
        return {
            "next": {
                "type": "set_cookies",
                "cookies": {
                    "company_id": company_id,
                },
            },
        }

SelectCompany.register()
