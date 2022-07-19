from netforce.model import Model, fields, get_model
from netforce.database import get_connection
from datetime import *
import time


class Report(Model):
    _name = "report.mfg.cost"

    def get_report_data(self,params,context={}):
        prod_id=params["product_id"]
        date_from=params["date_from"]
        date_to=params["date_to"]
        location_id=params["location_id"]
        date_from_m1 = (datetime.strptime(params["date_from"], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        qty_start=get_model("stock.balance").get_product_qty(product_id=prod_id,location_id=location_id,date=date_from_m1+" 23:59:59")
        qty_received=get_model("stock.balance").get_product_qty_in(product_id=prod_id,location_id=location_id,date_from=date_from+" 00:00:00",date_to=date_to+" 23:59:59")
        qty_end=get_model("stock.balance").get_product_qty(product_id=prod_id,location_id=location_id,date=date_to+" 23:59:59")
        cond=[["order_id.state","=","done"],["order_id.due_date",">=",date_from],["order_id.due_date","<=",date_to],["product_id","=",prod_id]]
        qty_use_actual=qty_start+qty_received-qty_end
        qty_use_planned=0
        fg_prod_ids=[]
        packed_qtys={}
        planned_use_qtys={}
        num_orders={}
        for comp in get_model("production.component").search_browse(cond):
            order=comp.order_id
            fg_prod_id=order.product_id.id
            packed_qtys.setdefault(fg_prod_id,0)
            packed_qtys[fg_prod_id]+=order.qty_received
            planned_use_qtys.setdefault(fg_prod_id,0)
            planned_use_qtys[fg_prod_id]+=comp.qty_planned_done
            num_orders.setdefault(fg_prod_id,0)
            num_orders[fg_prod_id]+=1
            qty_use_planned+=comp.qty_planned_done
            fg_prod_ids.append(fg_prod_id)
        fg_prod_ids=list(set(fg_prod_ids))
        qty_use_ratio=qty_use_actual/qty_use_planned if qty_use_planned else 0
        lines=[]
        for fg_prod in get_model("product").browse(fg_prod_ids):
            line={
                "fg_prod_name": fg_prod.name,
                "fg_prod_code": fg_prod.code,
                "fg_packed_qty": packed_qtys.get(fg_prod.id,0),
                "rm_planned_use_qty": planned_use_qtys.get(fg_prod.id,0),
                "num_orders": num_orders.get(fg_prod.id,0),
            }
            line["current_bom_qty"]=line["rm_planned_use_qty"]/line["fg_packed_qty"] if line["fg_packed_qty"] else 0
            line["new_bom_qty"]=line["current_bom_qty"]*qty_use_ratio
            lines.append(line)
        lines.sort(key=lambda l: l["fg_prod_code"])
        data={
            "qty_start": qty_start,
            "qty_received": qty_received,
            "qty_end": qty_end,
            "qty_use_actual": qty_use_actual,
            "qty_use_planned": qty_use_planned,
            "qty_use_ratio": qty_use_ratio,
            "lines": lines,
        }
        return data

Report.register()
