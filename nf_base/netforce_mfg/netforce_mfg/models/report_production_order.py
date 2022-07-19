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
from dateutil.relativedelta import *
from datetime import *


class ReportProductionOrder(Model):
    _name = "report.production.order"
    _transient = True
    _fields = {
        "date_from": fields.Date("Order Date From"),
        "date_to": fields.Date("Order Date To"),
        "product_id": fields.Many2One("product", "Product"),
        "state": fields.Selection([["draft", "Draft"], ["waiting_confirm", "Waiting Confirmation"], ["waiting_suborder", "Waiting Suborder"], ["waiting_material", "Waiting Material"], ["ready", "Ready To Start"], ["in_progress", "In Progress"], ["done", "Completed"], ["voided", "Voided"], ["split", "Split"]], "Status"),
        "production_order": fields.Many2One("production.order", "Production Order"),
        "production_location_id": fields.Many2One("stock.location", "Production Location"),
        "sale_order": fields.Char("Sales Order"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        elif not date_from and date_to:
            date_from = get_model("settings").get_fiscal_year_start(date=date_to)
        return {
            "date_from": date_from,
            "date_to": date_to,
        }

    def get_report_data(self, ids, context={}):
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        condition = []
        if params.get("date_from"):
            date_from = params.get("date_from") + " 00:00:00"
            condition.append(["order_date", ">=", date_from])
        if params.get("date_to"):
            date_to = params.get("date_to") + " 23:59:59"
            condition.append(["order_date", "<=", date_to])
        if params.get("product_id"):
            condition.append(["product_id", "=", params.get("product_id")])
        if params.get("production_location_id"):
            condition.append(["production_location_id", "=", params.get("production_location_id")])
        if params.get("state"):
            condition.append(["state", "=", params.get("state")])
        prod_order_list = get_model("production.order").search_browse(condition)
        lines = []
        item_no = 0
        status_map = {
            "draft": "Draft",
            "waiting_confirm": "Waiting Confirmation",
            "waiting_suborder": "Waiting Suborder",
            "waiting_material": "Waiting Material",
            "ready": "Ready To Start",
            "in_progress": "In Progress",
            "done": "Complete",
            "voided": "Voided",
        }
        for prod_order in prod_order_list:
            item_no += 1
            line = self.get_line_data(context={"prod_order": prod_order})
            line["state"] = status_map[line["state"]] if line["state"] in status_map else line["state"]
            line["_item_no"] = item_no
            lines.append(line)
        return {"lines": lines}

    def get_line_data(self, context={}):
        prod_order = context["prod_order"]
        return {
            "number": prod_order.number,
            "order_date": prod_order.order_date,
            "sale_order_number": prod_order.sale_id.number,
            "product_code": prod_order.product_id.code,
            "product_name": prod_order.product_id.name,
            "production_location": prod_order.production_location_id.name,
            "qty_planned": prod_order.qty_planned,
            "qty_received": prod_order.qty_received,
            "uom": prod_order.product_id.uom_id.name,
            "time_start": prod_order.time_start,
            "time_stop": prod_order.time_stop,
            #"duration": prod_order.duration,
            "state": prod_order.state,
        }

ReportProductionOrder.register()
