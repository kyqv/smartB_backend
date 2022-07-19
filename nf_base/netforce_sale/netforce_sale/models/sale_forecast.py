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
from netforce.utils import get_data_path
from netforce.database import get_connection
from netforce import access
from datetime import *
import time


class SaleForecast(Model):
    _name = "sale.forecast"
    _string = "Sales Forecast"
    _name_field = "number"
    _key=["number"]
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "date_from": fields.Date("From Date", required=True, search=True),
        "date_to": fields.Date("To Date", required=True, search=True),
        "location_id": fields.Many2One("stock.location", "From Warehouse",search=True),
        "state": fields.Selection([["open", "Open"], ["closed", "Closed"]], "Status", required=True, search=True),
        "description": fields.Text("Description"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "lines": fields.One2Many("sale.forecast.line","forecast_id","Items"),
        "num_lines": fields.Integer("Number Of Items",function="get_num_lines"),
    }
    _order = "date_from desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="sale_forecast",context=context)
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if not num:
                return None
            user_id = access.get_active_user()
            access.set_active_user(1)
            res = self.search([["number", "=", num]])
            access.set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    _defaults = {
        "number": _get_number,
        "state": "open",
    }

    def update_stock(self, ids, context={}):
        settings = get_model("settings").browse(1)
        res = get_model("stock.location").search([["type", "=", "customer"]])
        if not res:
            raise Exception("Customer location not found")
        loc_to_id = res[0]
        for obj in self.browse(ids):
            if not obj.location_id:
                raise Exception("Missing location in sales forecast %s"%obj.number)
            obj.stock_moves.delete()
            for line in obj.lines:
                diff_qty = line.plan_qty - line.actual_qty
                if diff_qty <= 0:
                    continue
                prod=line.product_id
                vals = {
                    "date": obj.date_from + " 00:00:00",
                    "journal_id": settings.pick_out_journal_id.id,
                    "related_id": "sale.forecast,%s" % obj.id,
                    "location_from_id": obj.location_id.id,
                    "location_to_id": loc_to_id,
                    "product_id": prod.id,
                    "qty": diff_qty,
                    "uom_id": prod.uom_id.id,
                    "state": "pending",
                }
                move_id = get_model("stock.move").create(vals)

    def close(self, ids, context={}):
        for obj in self.browse(ids):
            obj.stock_moves.delete()
            obj.write({"state": "closed"})

    def reopen(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "open"})
            obj.update_stock()

    def copy(self, ids, context={}):
        obj=self.browse(ids[0])
        vals = {
            "date_from": obj.date_from,
            "date_to": obj.date_to,
            "description": obj.description,
            "lines": [],
        }
        for line in obj.lines:
            line_vals={
                "product_id": line.product_id.id,
                "customer_id": line.customer_id.id,
                "min_shelf_life": line.min_shelf_life,
                "plan_qty": line.plan_qty,
            }
            vals["lines"].append(("create",line_vals))
        new_id=self.create(vals)
        return {
            "next": {
                "name": "sale_forecast",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Sales forecast copied",
        }

    def copy_to_production_plan(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            d=datetime.strptime(obj.date_from,"%Y-%m-%d")-timedelta(days=obj.product_id.mfg_lead_time or 0)
            mfg_date=d.strftime("%Y-%m-%d")
            res=get_model("bom").search([["product_id","=",obj.product_id.id]])
            if not res:
                raise Exception("BoM not found for product %s"%obj.product_id.code)
            bom_id=res[0]
            vals={
                "product_id": obj.product_id.id,
                "date_from": mfg_date,
                "date_to": mfg_date,
                "plan_qty": obj.plan_qty,
                "uom_id": obj.uom_id.id,
                "bom_id": bom_id,
            }
            get_model("production.plan").create(vals)
            n+=1
        return {
            "flash": "%d production plans created from sales forecast"%n,
        }

    def copy_to_rm_purchase(self,ids,context={}):
        obj=self.browse(ids[0])
        suppliers = {}
        for line in obj.lines:
            prod = line.product_id
            if prod.type not in ("stock", "consumable"):
                continue
            cur_qty=get_model("stock.balance").get_qty_phys(obj.location_id.id,prod.id)
            if line.plan_qty<cur_qty:
                continue
            order_qty=line.plan_qty-cur_qty
            if not prod.suppliers:
                raise Exception("Missing supplier for product '%s'" % prod.name)
            supplier_id = prod.suppliers[0].supplier_id.id
            suppliers.setdefault(supplier_id, []).append((prod.id, order_qty))
            res=get_model("bom").search([["product_id","=",prod.id]])
            if res:
                bom_id=res[0]
                bom=get_model("bom").browse(bom_id)
                ratio=order_qty/bom.qty
                for comp in bom.lines:
                    rm_prod=comp.product_id
                    qty=comp.qty*ratio
                    if not rm_prod.suppliers:
                        raise Exception("Missing supplier for product '%s'" % rm_prod.name)
                    supplier_id = rm_prod.suppliers[0].supplier_id.id
                    suppliers.setdefault(supplier_id, []).append((rm_prod.id, qty))
        if not suppliers:
            raise Exception("No purchase orders to create")
        po_ids = []
        for supplier_id, lines in suppliers.items():
            contact=get_model("contact").browse(supplier_id)
            purch_vals = {
                "contact_id": supplier_id,
                "ref": obj.number,
                "lines": [],
                "pay_term_id": contact.sale_pay_term_id.id,
            }
            for prod_id, qty in lines:
                prod = get_model("product").browse(prod_id)
                line_vals = {
                    "product_id": prod.id,
                    "description": prod.description or "/",
                    "qty": qty,
                    "uom_id": prod.uom_id.id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "location_id": obj.location_id.id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            po_ids.append(po_id)
        return {
            "next": {
                "name": "purchase",
                "search_condition": [["ref", "=", obj.number]],
            },
            "flash": "%d purchase orders created"%len(po_ids),
        }

    def months_to_qty(self,product_id,months,min_shelf_life=None):
        d_from=datetime.today().strftime("%Y-%m-%d")
        d_to=(datetime.today()+timedelta(days=int(months*30))).strftime("%Y-%m-%d")
        cond=[["product_id","=",product_id],["forecast_id.date_to",">=",d_from],["forecast_id.date_from","<=",d_to]]
        total_qty=0
        total_days=0
        for line in get_model("sale.forecast.line").search_browse(cond,order="forecast_id.date_from"):
            if min_shelf_life and line.min_shelf_life!=min_shelf_life:
                continue
            forecast_days=(datetime.strptime(line.forecast_id.date_to,"%Y-%m-%d")-datetime.strptime(line.forecast_id.date_from,"%Y-%m-%d")).days
            period_from=max(d_from,line.forecast_id.date_from)
            period_to=min(d_to,line.forecast_id.date_to)
            period_days=(datetime.strptime(period_to,"%Y-%m-%d")-datetime.strptime(period_from,"%Y-%m-%d")).days
            period_qty=line.plan_qty*period_days/forecast_days
            total_qty+=period_qty
            total_days+=period_days
        num_days=(datetime.strptime(d_to,"%Y-%m-%d")-datetime.strptime(d_from,"%Y-%m-%d")).days
        if total_days and total_days<num_days:
            missing_days=num_days-total_days
            total_qty+=missing_days*total_qty/total_days
        total_qty=int(total_qty) # XXX
        return total_qty

    def get_num_lines(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.lines)
        return vals

SaleForecast.register()
