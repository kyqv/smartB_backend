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
from netforce.database import get_connection
from datetime import *


class ReportSafeIn(Model):
    _name = "report.safe.in"
    _transient = True
    _fields = {
        "date_from": fields.DateTime("From"),
        "date_to": fields.DateTime("To"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-%d  00:00:00")
            date_to = date.today().strftime("%Y-%m-%d  23:59:59")
        return {
            "date_from": date_from,
            "date_to": date_to,
        }

    def get_report_data(self, ids, context={}):
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        picks = get_model("stock.picking").search_browse(
            [["date", "<", date_to], ["date", ">", date_from], ["state", "=", "done"], ["ref", "=", "DC To Safe"]])
        data = {
            "lines": [],
        }
        order = 1
        for pick in picks:
            for line in pick.lines:
                vals = {}
                product_code = line.product_id.code
                description = line.product_id.description
                lot_num = line.lot_id.number
                res = get_model("production.order").search_browse([["number", "=", lot_num]])
                production_number = ""
                location_from = ""
                state = ""
                if res:
                    production_order = res[0]
                    production_number = production_order.number
                    location_from = production_order.production_location_id.name
                    state = production_order.state
                vals = {
                    "order": order,
                    "container_number": line.container_from_id.number,
                    "barcode": "IIIIIIIIII",
                    "sales_number": line.container_from_id.number,
                    "production_number": production_number,
                    "product_code": product_code,
                    "description": description,
                    "qty": line.qty,
                    "uom": line.uom_id.name,
                    "location_from": location_from,
                    "location_to": line.location_from_id.name,
                    "location_store": line.location_to_id.name,
                    "state": state,
                }
                data["lines"].append(vals)
                order += 1
        print(data)
        return data

ReportSafeIn.register()
