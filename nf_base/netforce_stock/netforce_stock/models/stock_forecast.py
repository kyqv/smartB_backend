from netforce.model import Model, fields, get_model
from netforce import database
from netforce import access
from netforce import tasks
from datetime import *
import time

def get_total_qtys(prod_id=None, lot_id=None, loc_ids=None, date_from=None, date_to=None, states=None, categ_id=None):
    db = database.get_connection()
    q = "SELECT " \
        " t1.product_id,t1.lot_id,t1.location_from_id,t1.location_to_id,t1.uom_id,SUM(t1.qty) AS total_qty " \
        " FROM stock_move t1 " \
        " LEFT JOIN product t2 on t1.product_id=t2.id " \
        " WHERE t1.state IN %s"
    q_args = [tuple(states)]
    if date_from:
        q += " AND t1.date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND t1.date<=%s"
        q_args.append(date_to + " 23:59:59")
    if prod_id:
        q += " AND t1.product_id=%s"
        q_args.append(prod_id)
    if lot_id:
        q += " AND t1.lot_id=%s"
        q_args.append(lot_id)
    if loc_ids:
        q += " AND (t1.location_from_id IN %s OR t1.location_to_id IN %s)"
        q_args += [tuple(loc_ids), tuple(loc_ids)]
    if categ_id:
        q += " AND t2.categ_id=%s"
        q_args.append(categ_id)
    company_id = access.get_active_company()
    if company_id:
        q += " AND t1.company_id=%s"
        q_args.append(company_id)
    q += " GROUP BY t1.product_id,t1.lot_id,t1.location_from_id,t1.location_to_id,t1.uom_id"
    #print("q",q)
    #print("q_args",q_args)
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        prod = get_model("product").browse(r.product_id)
        uom = get_model("uom").browse(r.uom_id)
        qty = r.total_qty * uom.ratio / prod.uom_id.ratio
        k = (r.product_id, r.lot_id, r.location_from_id, r.location_to_id)
        totals.setdefault(k, 0)
        totals[k] += qty
    return totals

def get_forecast_lot_qtys(date,lot_id):
    loc_ids=get_model("stock.location").search([["type","=","internal"]])
    qtys = get_total_qtys(date_to=date,lot_id=lot_id,states=["done","pending","approved","forecast"])
    bals={}
    for (prod_id,lot_id,loc_from_id,loc_to_id),qty in qtys.items():
        bals.setdefault((loc_from_id,prod_id),0)
        bals[(loc_from_id,prod_id)]-=qty
        bals.setdefault((loc_to_id,prod_id),0)
        bals[(loc_to_id,prod_id)]+=qty
    res=[]
    for (loc_id,prod_id),qty in bals.items():
        if qty<=0:
            continue
        if loc_id not in loc_ids:
            continue
        res.append((loc_id,prod_id,qty))
    return res

def get_forecast_prod_loc_qtys(date,prod_id,loc_id):
    loc_ids=get_model("stock.location").search([["id","child_of",loc_id]])
    qtys = get_total_qtys(date_to=date,prod_id=prod_id,loc_ids=loc_ids,states=["done","pending","approved","forecast"])
    bals={}
    for (prod_id,lot_id,loc_from_id,loc_to_id),qty in qtys.items():
        bals.setdefault((loc_from_id,lot_id),0)
        bals[(loc_from_id,lot_id)]-=qty
        bals.setdefault((loc_to_id,lot_id),0)
        bals[(loc_to_id,lot_id)]+=qty
    res=[]
    for (loc_id,lot_id),qty in bals.items():
        if qty<=0:
            continue
        if loc_id not in loc_ids:
            continue
        res.append((loc_id,lot_id,qty))
    return res

class StockForecast(Model):
    _name = "stock.forecast"

    def update_forecast(self,ids,context={}):
        print("StockOrder.update_forecast",ids)
        db=database.get_connection()
        db.execute("DELETE FROM stock_move WHERE state='forecast'")
        lot_expiry_dates={}
        for lot in get_model("stock.lot").search_browse([["expiry_date","!=",None]]): # XXX: speed
            lot_expiry_dates[lot.id]=lot.expiry_date
        settings=get_model("settings").browse(1)
        forecast_journal=settings.forecast_journal_id
        if not forecast_journal:
            raise Exception("Missing forecast journal")
        job_id=context.get("job_id")
        d=datetime.today()
        num_days=90
        for i in range(num_days):
            ds=d.strftime("%Y-%m-%d")
            print("-"*80)
            print("making forecast %d/%d (%s)"%(i+1,num_days,ds))
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/num_days,"Updating forecast for %s (%s/%s)"%(ds,i+1,num_days))
            for lot in get_model("stock.lot").search_browse([["expiry_date","=",ds]]):
                print("  - expiring lot: %s"%lot.number)
                expire_journal=settings.lot_expiry_journal_id
                if not expire_journal:
                    raise Exception("Missing expire journal")
                if not expire_journal.location_to_id:
                    raise Exception("Missing to location in expire journal")
                res=get_forecast_lot_qtys(ds,lot.id)
                for loc_id,prod_id,qty in res:
                    print("    - loc_id=%s prod_id=%s qty=%s"%(loc_id,prod_id,qty))
                    prod=get_model("product").browse(prod_id)
                    vals={
                        "journal_id": forecast_journal.id,
                        "date": ds+" 00:00:00",
                        "location_from_id": loc_id,
                        "location_to_id": expire_journal.location_to_id.id,
                        "product_id": prod_id,
                        "lot_id": lot.id,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "state": "forecast",
                    }
                    get_model("stock.move").create(vals)
            for lot in get_model("stock.lot").search_browse([["life_75_date","=",ds]]):
                print("  - 75%% life: %s"%lot.number)
                life_75_journal=settings.life_75_journal_id
                if not life_75_journal:
                    raise Exception("Missing 75% life journal")
                if not life_75_journal.location_from_id:
                    raise Exception("Missing from location in life journal")
                if not life_75_journal.location_to_id:
                    raise Exception("Missing to location in life journal")
                res=get_forecast_lot_qtys(ds,lot.id)
                for loc_id,prod_id,qty in res:
                    if loc_id==life_75_journal.location_to_id.id:
                        continue
                    print("    - loc_id=%s prod_id=%s qty=%s"%(loc_id,prod_id,qty))
                    prod=get_model("product").browse(prod_id)
                    vals={
                        "journal_id": forecast_journal.id,
                        "date": ds+" 00:00:00",
                        "location_from_id": life_75_journal.location_from_id.id,
                        "location_to_id": life_75_journal.location_to_id.id,
                        "product_id": prod_id,
                        "lot_id": lot.id,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "state": "forecast",
                    }
                    get_model("stock.move").create(vals)
            for lot in get_model("stock.lot").search_browse([["life_50_date","=",ds]]):
                print("  - 50%% life: %s"%lot.number)
                life_50_journal=settings.life_50_journal_id
                if not life_50_journal:
                    raise Exception("Missing 50% life journal")
                if not life_50_journal.location_from_id:
                    raise Exception("Missing from location in life journal")
                if not life_50_journal.location_to_id:
                    raise Exception("Missing to location in life journal")
                res=get_forecast_lot_qtys(ds,lot.id)
                for loc_id,prod_id,qty in res:
                    if loc_id==life_50_journal.location_to_id.id:
                        continue
                    print("    - loc_id=%s prod_id=%s qty=%s"%(loc_id,prod_id,qty))
                    prod=get_model("product").browse(prod_id)
                    vals={
                        "journal_id": forecast_journal.id,
                        "date": ds+" 00:00:00",
                        "location_from_id": life_50_journal.location_from_id.id,
                        "location_to_id": life_50_journal.location_to_id.id,
                        "product_id": prod_id,
                        "lot_id": lot.id,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "state": "forecast",
                    }
                    get_model("stock.move").create(vals)
            for line in get_model("sale.forecast.line").search_browse([["forecast_id.date_from","=",ds]]):
                print("  - sale forecast: %s"%line.id)
                res=get_model("stock.location").search([["type","=","customer"]])
                if not res:
                    raise Exception("Customer location not found")
                cust_loc_id=res[0]
                res=get_forecast_prod_loc_qtys(ds,line.product_id.id,line.location_id.id)
                res.sort(key=lambda x: lot_expiry_dates.get(x[1],"9999-99-99"))
                remain_qty=max(0,line.plan_qty-line.actual_qty)
                for loc_id,lot_id,qty in res:
                    if remain_qty<=0:
                        break
                    use_qty=min(remain_qty,qty) # XXX: uom
                    print("    - loc_id=%s lot_id=%s qty=%s use_qty=%s"%(loc_id,lot_id,qty,use_qty))
                    prod=line.product_id
                    vals={
                        "journal_id": forecast_journal.id,
                        "date": ds+" 00:00:00",
                        "location_from_id": loc_id,
                        "location_to_id": cust_loc_id,
                        "product_id": prod.id,
                        "lot_id": lot_id,
                        "qty": use_qty,
                        "uom_id": prod.uom_id.id,
                        "state": "forecast",
                    }
                    get_model("stock.move").create(vals)
                    remain_qty-=use_qty
                if remain_qty>0:
                    prod=line.product_id
                    vals={
                        "journal_id": forecast_journal.id,
                        "date": ds+" 00:00:00",
                        "location_from_id": line.location_id.id,
                        "location_to_id": cust_loc_id,
                        "product_id": prod.id,
                        "qty": remain_qty,
                        "uom_id": prod.uom_id.id,
                        "state": "forecast",
                    }
                    get_model("stock.move").create(vals)
            d+=timedelta(days=1)
        prod_ids=get_model("product").search([])
        get_model("product").write(prod_ids,{"update_balance":True}) # XXX

StockForecast.register()
