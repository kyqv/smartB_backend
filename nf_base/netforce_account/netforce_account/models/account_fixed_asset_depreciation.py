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
from datetime import *
from dateutil.relativedelta import *


class Depreciation(Model):
    _name = "account.fixed.asset.depreciation"
    _string = "Depreciation"
    _fields = {
        "date_to": fields.Date("To Date", required=True),
    }
    _transient = True

    def get_date_to(self, ids, context={}):
        month = int(datetime.now().strftime("%m"))
        year = int(datetime.now().strftime("%Y"))
        day = calendar.monthrange(year, month)[1]
        last_date = "%s-%s-%s" % (year, month, day)
        return last_date

    _defaults = {
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def update(self, ids, context):
        obj = self.browse(ids)[0]
        asset_ids = get_model("account.fixed.asset").search([["state", "=", "registered"]])
        get_model("account.fixed.asset").depreciate(asset_ids, obj.date_to)
        return {
            "next": {
                "name": "fixed_asset",
                "mode": "list",
            },
            "flash": "All registered assets are depreciated to %s" % obj.date_to,
        }

Depreciation.register()
