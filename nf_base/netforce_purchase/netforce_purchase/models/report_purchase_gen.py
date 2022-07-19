from netforce.model import Model, fields, get_model
from datetime import *
import time
from dateutil.relativedelta import *
from netforce import database
from netforce import access
from decimal import *

def get_total_qtys(prod_ids=None, loc_id=None, date_from=None, date_to=None, states=None, categ_ids=None, min_life_50_date=None, min_life_75_date=None):
    db = database.get_connection()
    q = "SELECT " \
        " m.product_id,p.uom_id AS prod_uom_id,m.location_from_id,m.location_to_id,m.uom_id,m.state,SUM(m.qty) AS total_qty " \
        " FROM stock_move m " \
        " JOIN product p on m.product_id=p.id" \
        " LEFT JOIN stock_lot l on m.lot_id=l.id WHERE true"
    q_args = []
    if states:
        q+=" AND m.state IN %s"
        q_args.append(tuple(states))
    if date_from:
        q += " AND m.date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND m.date<=%s"
        q_args.append(date_to + " 23:59:59")
    if prod_ids:
        q += " AND m.product_id IN %s"
        q_args.append(tuple(prod_ids))
    if loc_id:
        q += " AND (m.location_from_id=%s OR m.location_to_id=%s)"
        q_args += [loc_id, loc_id]
    if categ_ids:
        q += " AND p.categ_id IN %s"
        q_args.append(tuple(categ_ids))
    if min_life_50_date:
        q += " AND l.life_50_date>=%s"
        q_args.append(min_life_50_date)
    if min_life_75_date:
        q += " AND l.life_75_date>=%s"
        q_args.append(min_life_75_date)
    company_id = access.get_active_company()
    if company_id:
        q += " AND m.company_id=%s"
        q_args.append(company_id)
    q += " GROUP BY m.product_id,p.uom_id,m.location_from_id,m.location_to_id,m.uom_id,m.state"
    #print("q",q)
    #print("q_args",q_args)
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        qty = get_model("uom").convert(r.total_qty,r.uom_id,r.prod_uom_id)
        k = (r.product_id, r.location_from_id, r.location_to_id, r.state)
        totals.setdefault(k, 0)
        totals[k] += qty
    return totals

def get_in_dates():
    db=database.get_connection()
    q="SELECT m.product_id,MIN(m.date) AS date FROM stock_move m JOIN stock_location l1 ON l1.id=m.location_from_id JOIN stock_location l2 ON l2.id=m.location_to_id WHERE m.state IN ('pending','approved') AND l1.type!='internal' AND l2.type='internal' GROUP BY m.product_id"
    res=db.query(q)
    dates={}
    for r in res:
        dates[r.product_id]=r.date[:10]
    return dates

class Report(Model):
    _name = "report.purchase.gen"
    _transient = True
    _fields = {
        "product_categ_id": fields.Many2One("product.categ","Product Category"),
        "supplier_id": fields.Many2One("contact","Supplier",condition=[["supplier","=",True]]),
        "product_id": fields.Many2One("product","Product"),
        "filter_min_stock": fields.Boolean("Show only below min stock"),
        "num_periods": fields.Integer("Number Of Periods"),
        "period_type": fields.Selection([["month","Month"],["week","Week"]],"Period Type"),
    }
    _defaults={
        "num_periods": 6,
        "period_type": "month",
    }

    def get_report_data(self, ids, context={}):
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        categ_id = params.get("product_categ_id")
        supplier_id = params.get("supplier_id")
        product_id = params.get("product_id")
        filter_min_stock = params.get("filter_min_stock")
        num_periods = params.get("num_periods")
        period_type = params.get("period_type")
        prod_ids=[product_id] if product_id else None
        categ_ids=[categ_id] if categ_id else None
        today=time.strftime("%Y-%m-%d")
        res=get_total_qtys(prod_ids=prod_ids,categ_ids=categ_ids)
        all_prod_ids=[]
        bal_qtys_75={}
        bal_qtys_50={}
        bal_qtys_other={}
        exp_qtys_75={}
        exp_qtys_50={}
        exp_qtys_other={}
        for bal in get_model("stock.balance").search_browse([]):
            prod=bal.product_id
            all_prod_ids.append(prod.id)
            lot=bal.lot_id
            if lot.life_75_date and lot.life_75_date>today:
                bal_qtys_75.setdefault(prod.id,0)
                bal_qtys_75[prod.id]+=bal.qty_phys
                exp_qtys_75.setdefault(prod.id,[])
                exp_qtys_75[prod.id].append((lot.life_75_date,bal.qty_phys))
            elif lot.life_50_date and lot.life_50_date>today:
                bal_qtys_50.setdefault(prod.id,0)
                bal_qtys_50[prod.id]+=bal.qty_phys
                exp_qtys_50.setdefault(prod.id,[])
                exp_qtys_50[prod.id].append((lot.life_50_date,bal.qty_phys))
            else:
                bal_qtys_other.setdefault(prod.id,0)
                bal_qtys_other[prod.id]+=bal.qty_phys
                if lot.expiry_date:
                    exp_qtys_other.setdefault(prod.id,[])
                    exp_qtys_other[prod.id].append((lot.expiry_date,bal.qty_phys))
        locations={}
        for loc in get_model("stock.location").search_browse([]):
            locations[loc.id]=loc
        tomorrow=datetime.today()+timedelta(days=1)
        periods=[]
        for i in range(num_periods):
            if period_type=="month":
                d_from=tomorrow+relativedelta(months=i,day=1)
                if d_from<tomorrow:
                    d_from=tomorrow
                d_to=tomorrow.today()+relativedelta(months=i,day=31)
                vals={
                    "date_from": d_from.strftime("%Y-%m-%d"),
                    "date_to": d_to.strftime("%Y-%m-%d"),
                    "name": d_from.strftime("%d")+" - "+d_to.strftime("%d %b %Y"),
                }
                periods.append(vals)
            elif period_type=="week":
                d_from=tomorrow+timedelta(days=7*i-tomorrow.weekday())
                if d_from<tomorrow:
                    d_from=tomorrow
                d_to=d_from+timedelta(days=7)
                vals={
                    "date_from": d_from.strftime("%Y-%m-%d"),
                    "date_to": d_to.strftime("%Y-%m-%d"),
                    "name": d_from.strftime("%d")+" - "+d_to.strftime("%d %b %Y"),
                }
                periods.append(vals)
        for period in periods:
            forecasts={}
            for line in get_model("sale.forecast.line").search_browse([["forecast_id.date_from","<=",period["date_to"]],["forecast_id.date_to",">=",period["date_to"]]]):
                period_days=(datetime.strptime(period["date_to"],"%Y-%m-%d")-datetime.strptime(period["date_from"],"%Y-%m-%d")).days
                forecast_days=(datetime.strptime(line.forecast_id.date_to,"%Y-%m-%d")-datetime.strptime(line.forecast_id.date_from,"%Y-%m-%d")).days
                qty=round(line.plan_qty*period_days/forecast_days,1)
                qtys=forecasts.setdefault(line.product_id.id,{"qty_other":0,"qty_50":0,"qty_75":0})
                if line.min_shelf_life=="75":
                    qtys["qty_75"]+=qty
                elif line.min_shelf_life=="50":
                    qtys["qty_50"]+=qty
                else:
                    qtys["qty_other"]+=qty
            period["forecasts"]=forecasts
            res=get_total_qtys(prod_ids=prod_ids,categ_ids=categ_ids,date_from=period["date_from"],date_to=period["date_to"])
            prod_qtys={}
            for (prod_id, loc_from_id, loc_to_id, state), qty in res.items():
                prod_qtys.setdefault(prod_id,{})
                k=(loc_from_id,loc_to_id,state)
                prod_qtys[prod_id][k]=qty
            period["prod_qtys"]=prod_qtys
        def get_qty_phys(prod_id,min_life=None):
            if min_life=="50":
                qtys=prod_qtys_life_50.get(prod_id,{})
            elif min_life=="75":
                qtys=prod_qtys_life_75.get(prod_id,{})
            else:
                qtys=prod_qtys.get(prod_id,{})
            total_qty = 0
            for (loc_from_id, loc_to_id, state), qty in qtys.items():
                loc_from=locations[loc_from_id]
                loc_to=locations[loc_to_id]
                if loc_from.type!="internal" and loc_to.type=="internal":
                    if state=="done":
                        total_qty+=qty
                elif loc_from.type=="internal" and loc_to.type!="internal":
                    if state=="done":
                        total_qty-=qty
            return total_qty
        def get_period_qty_in(period,prod_id):
            prod_qtys=period["prod_qtys"]
            qtys=prod_qtys.get(prod_id,{})
            total_qty = 0
            for (loc_from_id, loc_to_id, state), qty in qtys.items():
                loc_from=locations[loc_from_id]
                loc_to=locations[loc_to_id]
                if loc_from.type!="internal" and loc_to.type=="internal":
                    if state in ("pending","approved"):
                        total_qty+=qty
            return total_qty
        def get_exp_50(period,prod_id):
            qtys=exp_qtys_50.get(prod.id,[])
            total=0
            for d,qty in qtys:
                if d>=period["date_from"] and d<=period["date_to"]:
                    total+=qty
            return total
        def get_exp_75(period,prod_id):
            qtys=exp_qtys_75.get(prod.id,[])
            total=0
            for d,qty in qtys:
                if d>=period["date_from"] and d<=period["date_to"]:
                    total+=qty
            return total
        def get_exp_other(period,prod_id):
            qtys=exp_qtys_other.get(prod.id,[])
            total=0
            for d,qty in qtys:
                if d>=period["date_from"] and d<=period["date_to"]:
                    total+=qty
            return total
        cond=[]
        if categ_id:
            cond.append(["categ_id","=",categ_id])
        if supplier_id:
            cond.append(["suppliers.supplier_id","=",supplier_id])
        if product_id:
            cond.append(["id","=",product_id])
        all_prod_ids=list(set(all_prod_ids))
        #print("all_prod_ids",all_prod_ids)
        cond.append(["id","in",all_prod_ids])
        lines=[]
        for prod in get_model("product").search_browse(cond):
            qty_75=bal_qtys_75.get(prod.id,0)
            qty_50=bal_qtys_50.get(prod.id,0)
            qty_other=bal_qtys_other.get(prod.id,0)
            lead_days=prod.purchase_lead_time or "N/A"
            min_months=prod.min_qty_months or 0
            bal_qty_75=qty_75
            bal_qty_50=qty_50
            bal_qty_other=qty_other
            prod_periods=[]
            max_date=None
            last_forecasts=None
            for period in periods:
                qty_in=get_period_qty_in(period,prod.id)
                forecasts=period["forecasts"].get(prod.id,{})
                if forecasts:
                    last_forecasts=forecasts
                else:
                    forecasts=last_forecasts
                vals={
                    "qty_in": qty_in,
                    "qty_out_75": forecasts.get("qty_75",0),
                    "qty_out_50": forecasts.get("qty_50",0),
                    "qty_out_other": forecasts.get("qty_other",0),
                }
                bal_qty_75+=vals["qty_in"]
                if vals["qty_out_75"]:
                    bal_qty_75-=vals["qty_out_75"]
                if vals["qty_out_50"]:
                    remain_qty=vals["qty_out_50"]
                    used_qty=max(0,min(remain_qty,bal_qty_50))
                    bal_qty_50-=used_qty
                    remain_qty-=used_qty
                    used_qty=max(0,min(remain_qty,bal_qty_75))
                    bal_qty_75-=used_qty
                    remain_qty-=used_qty
                    bal_qty_50-=remain_qty
                if vals["qty_out_other"]:
                    remain_qty=vals["qty_out_other"]
                    used_qty=max(0,min(remain_qty,bal_qty_other))
                    bal_qty_other-=used_qty
                    remain_qty-=used_qty
                    used_qty=max(0,min(remain_qty,bal_qty_50))
                    bal_qty_50-=used_qty
                    remain_qty-=used_qty
                    used_qty=max(0,min(remain_qty,bal_qty_75))
                    bal_qty_75-=used_qty
                    remain_qty-=used_qty
                    bal_qty_other-=remain_qty
                exp_75=max(0,min(get_exp_75(period,prod.id),bal_qty_75))
                exp_50=max(0,min(get_exp_50(period,prod.id),bal_qty_50))
                exp_other=max(0,min(get_exp_other(period,prod.id),bal_qty_other))
                vals.update({
                    "exp_75": -exp_75, 
                    "exp_50": -exp_50+exp_75, # XXX
                    "exp_other": -exp_other+exp_50, # XXX
                })
                bal_qty_75+=vals["exp_75"]
                bal_qty_50+=vals["exp_50"]
                bal_qty_other+=vals["exp_other"]
                vals["bal_qty_75"]=bal_qty_75
                vals["bal_qty_50"]=bal_qty_50
                vals["bal_qty_other"]=bal_qty_other
                if vals["bal_qty_75"]>=0 and vals["bal_qty_50"]>=0 and vals["bal_qty_other"]>=0:
                    max_date=period["date_to"]
                prod_periods.append(vals)
            if max_date:
                qty_months=round((datetime.strptime(max_date,"%Y-%m-%d")-datetime.today()).days/Decimal(30),1)
            else:
                qty_months=0
            qty_order=0
            below_min=qty_months<min_months
            line_vals={
                "prod_id": prod.id,
                "prod_code": prod.code,
                "prod_name": prod.name,
                "supplier_name": prod.default_supplier_id.supplier_id.name if prod.default_supplier_id else "N/A",
                "qty_75": qty_75,
                "qty_50": qty_50,
                "qty_other": qty_other,
                "periods": prod_periods,
                "qty_order": qty_order,
                "lead_days": lead_days,
                "below_min": below_min,
                "qty_months": qty_months,
                "min_months": min_months,
            }
            lines.append(line_vals)
        data = {
            "company_name": comp.name,
            "periods": periods,
            "lines": lines,
            "date": time.strftime("%d %b %Y"),
        }
        for period in periods: # XXX
            del period["forecasts"]
            del period["prod_qtys"]
        #print("data",data)
        return data

Report.register()
