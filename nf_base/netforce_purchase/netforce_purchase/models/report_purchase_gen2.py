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
    print("q",q)
    print("q_args",q_args)
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
    _name = "report.purchase.gen2"
    _transient = True
    _fields = {
        "product_categ_id": fields.Many2One("product.categ","Product Category"),
        "supplier_id": fields.Many2One("contact","Supplier",condition=[["supplier","=",True]]),
        "product_id": fields.Many2One("product","Product"),
        "filter_min_stock": fields.Boolean("Show only below min stock"),
        "num_months": fields.Integer("Number Of Months"),
    }
    _defaults={
        "num_months": 4,
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
        prod_ids=[product_id] if product_id else None
        categ_ids=[categ_id] if categ_id else None
        today=time.strftime("%Y-%m-%d")
        res=get_total_qtys(prod_ids=prod_ids,categ_ids=categ_ids)
        all_prod_ids=[]
        prod_qtys={}
        for (prod_id, loc_from_id, loc_to_id, state), qty in res.items():
            prod_qtys.setdefault(prod_id,{})
            k=(loc_from_id,loc_to_id,state)
            prod_qtys[prod_id][k]=qty
            all_prod_ids.append(prod_id)
        res=get_total_qtys(prod_ids=prod_ids,categ_ids=categ_ids,min_life_50_date=today)
        prod_qtys_life_50={}
        for (prod_id, loc_from_id, loc_to_id, state), qty in res.items():
            prod_qtys_life_50.setdefault(prod_id,{})
            k=(loc_from_id,loc_to_id,state)
            prod_qtys_life_50[prod_id][k]=qty
        res=get_total_qtys(prod_ids=prod_ids,categ_ids=categ_ids,min_life_75_date=today)
        prod_qtys_life_75={}
        for (prod_id, loc_from_id, loc_to_id, state), qty in res.items():
            prod_qtys_life_75.setdefault(prod_id,{})
            k=(loc_from_id,loc_to_id,state)
            prod_qtys_life_75[prod_id][k]=qty
        locations={}
        for loc in get_model("stock.location").search_browse([]):
            locations[loc.id]=loc
        prod_sales={}
        for line in get_model("sale.forecast.line").search_browse([["forecast_id.date_to",">=",today]],order="forecast_id.date_to"):
            prod=line.product_id
            qtys=prod_sales.setdefault(prod.id,{})
            date_to=line.forecast_id.date_to
            qtys.setdefault(date_to,{
                "qty": 0,
                "qty_50": 0,
                "qty_75": 0,
            })
            if line.min_shelf_life=="50":
                qtys[date_to]["qty_50"]+=line.plan_qty or 0
            elif line.min_shelf_life=="75":
                qtys[date_to]["qty_75"]+=line.plan_qty or 0
            else:
                qtys[date_to]["qty"]+=line.plan_qty or 0
            all_prod_ids.append(prod.id)
        print("prod_sales",prod_sales)
        in_dates=get_in_dates()
        print("in_dates",in_dates)
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
        def get_qty_out(prod_id):
            qtys=prod_qtys.get(prod_id,{})
            total_qty = 0
            for (loc_from_id, loc_to_id, state), qty in qtys.items():
                loc_from=locations[loc_from_id]
                loc_to=locations[loc_to_id]
                if loc_from.type=="internal" and loc_to.type!="internal":
                    if state in ("pending","approved"):
                        total_qty+=qty
            return total_qty
        def get_qty_in(prod_id):
            qtys=prod_qtys.get(prod_id,{})
            total_qty = 0
            for (loc_from_id, loc_to_id, state), qty in qtys.items():
                loc_from=locations[loc_from_id]
                loc_to=locations[loc_to_id]
                if loc_from.type!="internal" and loc_to.type=="internal":
                    if state in ("pending","approved"):
                        total_qty+=qty
            return total_qty
        def get_prod_sales(prod_id):
            if not prod_sales.get(prod_id):
                return None
            d=(datetime.today()+relativedelta(day=31)).strftime("%Y-%m-%d")
            qtys=prod_sales[prod_id].get(d)
            if not qtys:
                return None
            return qtys["qty"]+qtys["qty_50"]+qtys["qty_75"]
        def get_prod_sales_next(prod_id):
            if not prod_sales.get(prod_id):
                return None
            d=(datetime.today()+relativedelta(months=1,day=31)).strftime("%Y-%m-%d")
            qtys=prod_sales[prod_id].get(d)
            if not qtys:
                return None
            return qtys["qty"]+qtys["qty_50"]+qtys["qty_75"]
        def get_months(prod_id,qty_avail,qty_avail_50,qty_avail_75):
            sale_qtys=prod_sales.get(prod_id,{})
            n=0
            total_qty=0
            total_qty_50=0
            total_qty_75=0
            d=datetime.today()+relativedelta(day=31)
            last_qtys={"qty":0,"qty_50":0,"qty_75":0}
            has_sales=False
            while n<12:
                print("-"*80)
                print("n=%s total_qty=%s"%(n,total_qty))
                qtys=sale_qtys.get(d.strftime("%Y-%m-%d"))
                if not qtys:
                    qtys=last_qtys
                else:
                    has_sales=True
                last_qtys=qtys
                d+=relativedelta(months=1,day=31)
                sale_qty=qtys["qty"]
                sale_qty_50=qtys["qty_50"]
                sale_qty_75=qtys["qty_75"]
                last_n=[]
                if sale_qty and total_qty+sale_qty>qty_avail:
                    print("total_qty=%s sale_qty=%s qty_avail=%s"%(total_qty,sale_qty,qty_avail))
                    diff_qty=qty_avail-total_qty
                    print("diff_qty",diff_qty)
                    last_n.append(n+round(Decimal(diff_qty)/sale_qty,1))
                if sale_qty_50 and total_qty_50+sale_qty_50>qty_avail_50:
                    diff_qty=qty_avail_50-total_qty_50
                    last_n.append(n+round(Decimal(diff_qty)/sale_qty_50,1))
                if sale_qty_75 and total_qty_75+sale_qty_75>qty_avail_75:
                    diff_qty=qty_avail_75-total_qty_75
                    last_n.append(n+round(Decimal(diff_qty)/sale_qty_75,1))
                if last_n:
                    print("last_n",last_n)
                    n=min(last_n)
                    break
                total_qty+=sale_qty
                total_qty_50+=sale_qty_50
                total_qty_75+=sale_qty_75
                n+=1
            print("="*80)
            print("n=%s total_qty=%s"%(n,total_qty))
            if not has_sales:
                return None
            return n
        def get_min_qty(prod_id,min_months):
            sale_qtys=prod_sales.get(prod_id,{})
            n=0
            d=datetime.today()+relativedelta(day=31)
            total_qty=0
            last_qtys={"qty":0,"qty_50":0,"qty_75":0}
            while n<min_months:
                qtys=sale_qtys.get(d.strftime("%Y-%m-%d"))
                if not qtys:
                    qtys=last_qtys
                last_qtys=qtys
                d+=relativedelta(months=1,day=31)
                total_qty+=qtys["qty"]
                total_qty+=qtys["qty_50"]
                total_qty+=qtys["qty_75"]
                n+=1
            return total_qty
        cond=[]
        if categ_id:
            cond.append(["categ_id","=",categ_id])
        if supplier_id:
            cond.append(["suppliers.supplier_id","=",supplier_id])
        if product_id:
            cond.append(["id","=",product_id])
        all_prod_ids=list(set(all_prod_ids))
        print("all_prod_ids",all_prod_ids)
        cond.append(["id","in",all_prod_ids])
        lines=[]
        for prod in get_model("product").search_browse(cond):
            qty_phys=get_qty_phys(prod.id)
            qty_out=get_qty_out(prod.id)
            qty_avail=qty_phys-qty_out
            qty_phys_life_50=get_qty_phys(prod.id,min_life="50")
            qty_phys_life_75=get_qty_phys(prod.id,min_life="75")
            qty_avail_life_50=max(0,qty_phys_life_50-qty_out)
            qty_avail_life_75=max(0,qty_phys_life_75-qty_out)
            qty_forecast=get_prod_sales(prod.id) or "N/A"
            qty_forecast_next=get_prod_sales_next(prod.id) or "N/A"
            months_remain=get_months(prod.id,qty_avail,qty_avail_life_50,qty_avail_life_75)
            qty_in=get_qty_in(prod.id)
            in_date=in_dates.get(prod.id) or "N/A"
            lead_days=prod.purchase_lead_time or "N/A"
            min_months=prod.min_qty_months or 0
            if min_months:
                min_qty=get_min_qty(prod.id,min_months)
                if qty_phys+qty_in<min_qty:
                    qty_order=min_qty-qty_phys-qty_in
                    below_min=True
                else:
                    qty_order=0
                    below_min=False
            else:
                min_qty=0 # XXX
                if qty_avail+qty_in<min_qty:
                    qty_order=min_qty-qty_avail-qty_in
                    below_min=True
                else:
                    qty_order=0
                    below_min=False
            if filter_min_stock and not below_min:
                continue
            line_vals={
                "prod_id": prod.id,
                "prod_code": prod.code,
                "prod_name": prod.name,
                "supplier_name": prod.default_supplier_id.supplier_id.name if prod.default_supplier_id else "N/A",
                "qty_phys": qty_phys,
                "qty_phys_life_50": qty_phys_life_50,
                "qty_phys_life_75": qty_phys_life_75,
                "qty_avail": qty_avail,
                "qty_avail_life_50": qty_avail_life_50,
                "qty_avail_life_75": qty_avail_life_75,
                "qty_out": qty_out,
                "qty_forecast": qty_forecast,
                "qty_forecast_next": qty_forecast_next,
                "months_remain": months_remain or "N/A",
                "qty_in": qty_in,
                "in_date": in_date,
                "qty_order": qty_order,
                "lead_days": lead_days,
                "below_min": below_min,
            }
            lines.append(line_vals)
        data = {
            "company_name": comp.name,
            "lines": lines,
        }
        return data

Report.register()
