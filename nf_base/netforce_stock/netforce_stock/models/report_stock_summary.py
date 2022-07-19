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
from netforce.database import get_connection
from pprint import pprint
from netforce.access import get_active_company
import time


def get_totals(date_from, date_to, product_id=None, product_ids=None, lot_id=None, location_id=None, container_id=None, prod_categ_id=None, prod_code=None, prod_company_ids=None, query_details=False, brand_id=None):
    print(">>> get_totals query_details=%s"%query_details)
    if query_details:
        q = "SELECT m.product_id,m.lot_id,m.container_id,m.location_from_id,m.location_to_id,m.uom_id,p.uom_id AS product_uom_id,SUM(m.qty) AS total_qty,SUM(m.cost_amount) AS total_amt,SUM(m.qty2) AS total_qty2 FROM stock_move m LEFT JOIN product p ON m.product_id=p.id WHERE m.state='done' AND p.type='stock'"
    else:
        q = "SELECT m.product_id,m.location_from_id,m.location_to_id,m.uom_id,p.uom_id AS product_uom_id,SUM(m.qty) AS total_qty,SUM(m.cost_amount) AS total_amt,SUM(m.qty2) AS total_qty2 FROM stock_move m LEFT JOIN product p ON m.product_id=p.id WHERE m.state='done' AND p.type='stock'"
    q_args = []
    if date_from:
        q += " AND m.date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND m.date<=%s"
        q_args.append(date_to + " 23:59:59")
    if product_id:
        q += " AND m.product_id=%s"
        q_args.append(product_id)
    if product_ids:
        q += " AND m.product_id IN %s"
        q_args.append(tuple(product_ids))
    if lot_id:
        q += " AND m.lot_id=%s"
        q_args.append(lot_id)
    if container_id:
        q += " AND m.container_id=%s"
        q_args.append(container_id)
    if location_id:
        q += " AND (m.location_from_id=%s OR m.location_to_id=%s)"
        q_args += [location_id, location_id]
    if prod_categ_id:
        prod_categ_ids = get_model("product.categ").search([["id","child_of",prod_categ_id]])
        prod_categ_ids.append(prod_categ_id)
        q += " AND p.categ_id in %s"
        q_args.append(tuple(prod_categ_ids))

    if prod_code:
        q += " AND p.code like %s"
        q_args.append("%s%s%s" % ("%", prod_code, "%"))
    if prod_company_ids:
        q += " AND p.company_id in %s"
        q_args.append(prod_company_ids)
    if brand_id:
        q += " AND p.brand_id = %s"
        q_args.append(brand_id)
    if query_details:
        q += " GROUP BY m.product_id,m.lot_id,m.container_id,m.location_from_id,m.location_to_id,m.uom_id,product_uom_id"
    else:
        q += " GROUP BY m.product_id,m.location_from_id,m.location_to_id,m.uom_id,product_uom_id"
    db = get_connection()
    print("q",q)
    print("q_args",q_args)
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        qty = get_model("uom").convert(r.total_qty, r.uom_id, r.product_uom_id)
        amt = r.total_amt or 0
        qty2 = r.total_qty2 or 0
        k = (r.product_id, r.get("lot_id"), r.get("container_id"), r.location_from_id, r.location_to_id)
        tot = totals.setdefault(k, [0, 0, 0])
        tot[0] += qty
        tot[1] += amt
        tot[2] += qty2
    print("<<< get_totals")
    return totals


class ReportStockSummary(Model):
    _name = "report.stock.summary"
    _transient = True
    _fields = {
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
        "location_id": fields.Many2One("stock.location", "Location", on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", on_delete="cascade"),
        "master_product_id": fields.Many2One("product", "Master Product", on_delete="cascade"),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "container_id": fields.Many2One("stock.container", "Container"),
        "prod_code": fields.Char("Product Code"),  # for enterprise package
        "prod_categ_id": fields.Many2One("product.categ", "Product Category"),
        "brand_id": fields.Many2One("product.brand", "Product Brand"),
        "show_lot": fields.Boolean("Show Lot / Serial Number"),
        "show_container": fields.Boolean("Show Container"),
        "show_qty2": fields.Boolean("Show Secondary Qty"),
        "only_closing": fields.Boolean("Only Show Closing"),
        "prod_company_id": fields.Many2One("company","Product Company"),
        "show_image": fields.Boolean("Show Images"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_report_data(self, ids=None, context={}):
        print("stock_summary.get_report_data")
        if not ids:
            return
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        date_from_m1 = (datetime.strptime(params["date_from"], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        prod_company_id = params.get("prod_company_id")
        prod_company_ids = get_model("company").search([["id","child_of",prod_company_id]])
        if prod_company_ids:
            prod_company_ids = tuple(prod_company_ids)
        else:
            prod_company_ids = None
        t0 = time.time()
        print("-"*80)
        print("getting totals...")
        query_details=params.get("show_lot") or params.get("show_container")
        prod_ids=None
        if params.get("master_product_id"):
            prod_ids=get_model("product").search([["parent_id","=",params["master_product_id"]]])
        totals = {
            "open": get_totals(None, date_from_m1, product_id=params.get("product_id"), product_ids=prod_ids,lot_id=params.get("lot_id"), location_id=params.get("location_id"), container_id=params.get("container_id"), prod_categ_id=params.get("prod_categ_id"), prod_code=params.get("prod_code"), prod_company_ids=prod_company_ids, query_details=query_details, brand_id=params.get("brand_id")),
            "period": get_totals(params["date_from"], params["date_to"], product_id=params.get("product_id"), product_ids=prod_ids, lot_id=params.get("lot_id"), location_id=params.get("location_id"), container_id=params.get("container_id"), prod_categ_id=params.get("prod_categ_id"), prod_code=params.get("prod_code"), prod_company_ids=prod_company_ids, query_details=query_details, brand_id=params.get("brand_id")),
            "close": get_totals(None, params["date_to"], product_id=params.get("product_id"), product_ids=prod_ids, lot_id=params.get("lot_id"), location_id=params.get("location_id"), container_id=params.get("container_id"), prod_categ_id=params.get("prod_categ_id"), prod_code=params.get("prod_code"), prod_company_ids=prod_company_ids, query_details=query_details, brand_id=params.get("brand_id")),
        }
        t1 = time.time()
        print("get totals in %.3f s" % (t1-t0))
        prod_locs = set([])
        for prod_id, lot_id, cont_id, loc_from_id, loc_to_id in list(totals["open"].keys()) + list(totals["period"].keys()) + list(totals["close"].keys()):
            if not params.get("show_lot"):
                lot_id = -1
            if not params.get("show_container"):
                cont_id = -1
            prod_locs.add((prod_id, lot_id, loc_from_id, cont_id))
            prod_locs.add((prod_id, lot_id, loc_to_id, cont_id))

        prod_totals={}
        for when in ("open","period","close"):
            tots={}
            for (prod_id, lot_id, cont_id, loc_from_id, loc_to_id), tot in totals[when].items():
                tots.setdefault(prod_id,{})
                tots[prod_id][(lot_id,cont_id,loc_from_id,loc_to_id)]=tot
            prod_totals[when]=tots
        def get_sum(when, prod=None, lot=-1, cont=-1, loc_to=-1, loc_from=-1):
            qty = 0
            amt = 0
            qty2 = 0
            tots=prod_totals[when].get(prod,{})
            for (lot_id, cont_id, loc_from_id, loc_to_id), tot in tots.items():
                if lot != -1 and lot_id != lot:
                    continue
                if cont != -1 and cont_id != cont:
                    continue
                if loc_from != -1 and loc_from_id != loc_from:
                    continue
                if loc_to != -1 and loc_to_id != loc_to:
                    continue
                qty += tot[0]
                amt += tot[1]
                qty2 += tot[2]
            return (qty, amt, qty2)
        prod_ids = []
        lot_ids = []
        loc_ids = []
        cont_ids = []
        for prod_id, lot_id, loc_id, cont_id in prod_locs:
            prod_ids.append(prod_id)
            loc_ids.append(loc_id)
            if lot_id and lot_id!=-1:
                lot_ids.append(lot_id)
            if cont_id and cont_id!=-1:
                cont_ids.append(cont_id)
        prod_ids = list(set(prod_ids))
        loc_ids = list(set(loc_ids))
        perm_loc_ids=get_model("stock.location").search([["id","in",loc_ids]])
        lot_ids = list(set(lot_ids))
        cont_ids = list(set(cont_ids))
        prods = {}
        for prod in get_model("product").browse(prod_ids):
            img=prod.image
            if not img and prod.parent_id:
                img=prod.parent_id.image
            prods[prod.id]={
                "name": prod.name,
                "code": prod.code,
                "uom_id": prod.uom_id.id,
                "uom_name": prod.uom_id.name,
                "image": img,
                "active": prod.active,
            }
        locs = {}
        for loc in get_model("stock.location").browse(loc_ids):
            locs[loc.id]={
                "name": loc.name,
                "code": loc.code,
                "type": loc.type,
            }
        lots = {}
        for lot in get_model("stock.lot").browse(lot_ids):
            lots[lot.id]={
                "number": lot.number,
            }
        conts = {}
        for cont in get_model("stock.container").browse(cont_ids):
            conts[cont.id]={
                "number": cont.number,
            }
        t2 = time.time()
        print("get prod/loc/lot/cont info in %.3f s" % (t2-t1))

        lines = []
        print("num prod_locs", len(prod_locs))
        print("-"*80)
        print("creating report lines...")
        i=0
        for prod_id, lot_id, loc_id, cont_id in prod_locs:
            if i%100==0:
                print("  line %d/%d"%(i,len(prod_locs)))
            i+=1
            if loc_id not in perm_loc_ids:
                continue
            if params.get("product_id") and prod_id != params["product_id"]:
                continue
            if params.get("lot_id") and lot_id != params["lot_id"]:
                continue
            if params.get("location_id") and loc_id != params["location_id"]:
                continue
            if params.get("container_id") and cont_id != params["container_id"]:
                continue
            loc = locs[loc_id]
            if loc["type"] != "internal":
                continue
            if cont_id and cont_id != -1:
                cont = conts[cont_id]
            else:
                cont = None
            prod = prods[prod_id]
            if not prod["active"]:
                continue
            lot = lots[lot_id] if lot_id and lot_id != -1 else None
            tot_open_in = get_sum("open", prod=prod_id, lot=lot_id, loc_to=loc_id, cont=cont_id)
            tot_open_out = get_sum("open", prod=prod_id, lot=lot_id, loc_from=loc_id, cont=cont_id)
            tot_period_in = get_sum("period", prod=prod_id, lot=lot_id, loc_to=loc_id, cont=cont_id)
            tot_period_out = get_sum("period", prod=prod_id, lot=lot_id, loc_from=loc_id, cont=cont_id)
            tot_close_in = get_sum("close", prod=prod_id, lot=lot_id, loc_to=loc_id, cont=cont_id)
            tot_close_out = get_sum("close", prod=prod_id, lot=lot_id, loc_from=loc_id, cont=cont_id)
            line_vals = {
                "prod_id": prod_id,
                "prod_name": prod["name"],
                "prod_code": prod["code"],
                "prod_img": prod["image"],
                "lot_id": lot_id if lot_id != -1 else None,
                "lot_num": lot["number"] if lot else None,
                "uom_name": prod["uom_name"],
                "loc_id": loc_id,
                "loc_code": loc["code"],
                "loc_name": loc["name"],
                "cont_id": cont_id,
                "cont_name": cont["number"] if cont else "",
                "open_qty": tot_open_in[0] - tot_open_out[0],
                "open_amt": tot_open_in[1] - tot_open_out[1],
                "open_qty2": tot_open_in[2] - tot_open_out[2],
                "period_in_qty": tot_period_in[0],
                "period_in_amt": tot_period_in[1],
                "period_in_qty2": tot_period_in[2],
                "period_out_qty": tot_period_out[0],
                "period_out_amt": tot_period_out[1],
                "period_out_qty2": tot_period_out[2],
                "close_qty": tot_close_in[0] - tot_close_out[0],
                "close_amt": tot_close_in[1] - tot_close_out[1],
                "close_qty2": tot_close_in[2] - tot_close_out[2],
            }
            if params.get("only_closing") and line_vals["close_qty"] == 0:
                continue
            if not line_vals["open_qty"] and not line_vals["open_qty2"] \
                    and not line_vals["period_in_qty"] and not line_vals["period_in_qty2"] \
                    and not line_vals["period_out_qty"] and not line_vals["period_out_qty2"] \
                    and not line_vals["close_qty"] and not line_vals["close_qty2"]:
                continue
            lines.append(line_vals)
        t3 = time.time()
        print("make lines in %.3f s" % (t3-t2))
        lines.sort(
            key=lambda l: (l["loc_name"], l["prod_code"] or "", l["prod_name"], l["lot_num"] or "", l["cont_name"] or ""))
        data = {
            "company_name": comp.name,
            "date_from": params.get("date_from"),
            "date_to": params.get("date_to"),
            "show_lot": params.get("show_lot"),
            "show_container": params.get("show_container"),
            "show_qty2": params.get("show_qty2"),
            "only_closing": params.get("only_closing"),
            "show_image": params.get("show_image"),
            "lines": lines,
            "total_open_amt": sum([l["open_amt"] for l in lines]),
            "total_open_qty2": sum([l["open_qty2"] for l in lines]),
            "total_period_in_amt": sum([l["period_in_amt"] for l in lines]),
            "total_period_in_qty2": sum([l["period_in_qty2"] for l in lines]),
            "total_period_out_amt": sum([l["period_out_amt"] for l in lines]),
            "total_period_out_qty2": sum([l["period_out_qty2"] for l in lines]),
            "total_close_qty": sum([l["close_qty"] for l in lines]),
            "total_close_amt": sum([l["close_amt"] for l in lines]),
            "total_close_qty2": sum([l["close_qty2"] for l in lines]),
        }
        if params.get("location_id"):
            loc = get_model("stock.location").browse(params["location_id"])
            data["location_id"] = [loc.id, loc.name]
        if params.get("lot_id"):
            lot = get_model("stock.lot").browse(params["lot_id"])
            data["lot_id"] = params["lot_id"]
            data["lot_num"] = lot.number
        if params.get("product_id"):
            prod = get_model("product").browse(params["product_id"])
            data["product_id"] = [prod.id, prod.name_get()[0][1]]
        if params.get("container_id"):
            cont = get_model("stock.container").browse(params["container_id"])
            data["container_id"] = [cont.id, cont.name_get()[0][1]]
        return data

ReportStockSummary.register()
