from netforce.model import Model, fields, get_model
from netforce import access
from netforce.database import get_connection
from datetime import *
from dateutil.relativedelta import *
import time
import math


class Report(Model):
    _name = "report.stock.invoice"
    _transient = True
    _fields = {
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
        "product_id": fields.Many2One("product","Product"),
        "categ_id": fields.Many2One("product.categ","Product Category"),
        "pick_id": fields.Many2One("stock.picking","Goods Receipt"),
        "products": fields.Many2Many("product","Products"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_report_data(self, ids, context={}):
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
            obj=self.browse(ids[0])
            filt_prod_ids=[p.id for p in obj.products]
        else:
            params = self.default_get(load_m2o=False, context=context)
            filt_prod_ids=None
        date_from=params["date_from"]
        date_to=params["date_to"]
        prods_in={}
        for move in get_model("stock.move").search_browse([["date",">=",date_from],["date","<=",date_to],["state","=","done"],["picking_id.journal_id.type","=","in"]]):
            if params.get("pick_id") and move.picking_id.id!=params["pick_id"]:
                continue
            prod_id=move.product_id.id
            prods_in.setdefault(prod_id,0)
            prods_in[prod_id]+=move.qty
        prods_return={}
        for move in get_model("stock.move").search_browse([["date",">=",date_from],["date","<=",date_to],["state","=","done"],["picking_id.journal_id.type","=","out_return"]]):
            if params.get("pick_id") and move.picking_id.id!=params["pick_id"]:
                continue
            prod_id=move.product_id.id
            prods_return.setdefault(prod_id,0)
            prods_return[prod_id]+=move.qty
        prods_inv={}
        for line in get_model("account.invoice.line").search_browse([["invoice_id.date",">=",date_from],["invoice_id.date","<=",date_to],["invoice_id.type","=","in"],["invoice_id.state","in",["waiting_payment","paid"]]]):
            prod_id=line.product_id.id
            if not prod_id:
                continue
            prods_inv.setdefault(prod_id,0)
            prods_inv[prod_id]+=line.qty or 0
        prod_ids=[]
        prod_ids+=list(prods_in.keys())
        prod_ids+=list(prods_return.keys())
        prod_ids+=list(prods_inv.keys())
        prod_ids=list(set(prod_ids))
        lines=[]
        for prod in get_model("product").browse(prod_ids):
            if params.get("product_id") and prod.id!=params["product_id"]:
                continue
            if params.get("categ_id") and prod.categ_id.id!=params["categ_id"]:
                continue
            if filt_prod_ids and prod.id not in filt_prod_ids:
                continue
            line={
                "prod_id": prod.id,
                "prod_code": prod.code,
                "prod_name": prod.name,
                "qty_received": prods_in.get(prod.id) or 0,
                "qty_returned": prods_return.get(prod.id) or 0,
                "qty_invoiced": prods_inv.get(prod.id) or 0,
            }
            line["qty_remain"]=line["qty_received"]-line["qty_returned"]-line["qty_invoiced"]
            lines.append(line)
        lines.sort(key=lambda l: l["prod_code"])
        data = {
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
        }
        return data

Report.register()
