from netforce.model import Model, fields, get_model
from netforce import access
from netforce.database import get_connection
from datetime import *
from dateutil.relativedelta import *
import time
import math


class Report(Model):
    _name = "report.purchase.picking"
    _transient = True
    _fields = {
        "date_from": fields.Date("PO Date From", required=True),
        "date_to": fields.Date("PO Date To", required=True),
        "project_id": fields.Many2One("project","Project"),
        "contact_id": fields.Many2One("contact","Supplier"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    notes="return lines: PO, Total GRs, Total Qty, Total Qty Received, Qty Difference"

    def get_report_data(self, ids, context={}):
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        print("\n report params: %s\n"% params)
        date_from=params["date_from"]
        date_to=params["date_to"]
        
        cond=[["date","between",[date_from,date_to]]]
        try:
            project_id=params["project_id"]
        except: 
            project_id=None
        try: 
            contact_id=params["contact_id"]
        except: 
            contact_id=None
        if project_id:
            cond.append(["project_id","=",project_id])
        if contact_id:
            cond.append(["contact_id","=",contact_id])
        print("\n search condition: %s \n"% cond)

        purchase= get_model("purchase.order").search_browse(cond)
        purchase_ids=[p.id for p in purchase]
        if len(purchase_ids)==0:
            raise Exception("No purchase order found")
        print("\n purchase_ids: %s\n"% purchase_ids)
        related_ids=[f"purchase.order,{_id}" for _id in purchase_ids]
        print("\n related_ids: %s\n"% related_ids)
       
        db=get_connection() 
        lines=[]
        for purchase in get_model("purchase.order").search_browse(cond):
            purchase_id=purchase.id
            pick_ids=[p.id for p in purchase.pickings]
            print("\n purchase.pickings: %s \n"% pick_ids)
            if len(pick_ids)==0:
                continue
            move_ids=[]
            for p in purchase.pickings:
                for l in p.lines:
                    move_ids.append(l.id)
            print("\n purchase.pickings.lines: %s \n"% move_ids)
            purchase_qty=db.query("SELECT SUM(qty) FROM purchase_order_line WHERE order_id=%s"%purchase_id)
            pick_in_qty=db.query("SELECT SUM(CASE WHEN state='done' THEN qty END) FROM stock_move WHERE related_id='purchase.order,%s'"%purchase_id)
            #aggregate=get_report_line(purchase.id,date_from,date_to)
            line={
                "purchase_id":purchase_id,
                "purchase_number":purchase.number,
                "pick_in_ids":pick_ids,
                "move_ids":move_ids, 
                "total_pick_in":len(pick_ids),
                "total_qty":purchase_qty[0].sum or 0, #sum([l.qty for l in purchase.lines]),
                "total_qty_received":pick_in_qty[0].sum or 0, #sum([l.qty_received for l in purchase.lines]),

            }
            line["total_qty_pending"]=line["total_qty"]-line["total_qty_received"]
            print("\n line: %s\n"% line)
            lines.append(line)
        data={
            "date_from":date_from,
            "date_to":date_to,
            "project_id":project_id,
            "contact_id":contact_id,
            "lines":lines,
        }
        print("\n data: %s \n" % data)
        return data

Report.register()
