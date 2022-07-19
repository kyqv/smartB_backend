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

from statistics import pstdev
from netforce.model import Model, fields, get_model
from netforce import database
from netforce import tasks
import math
from decimal import *
import random
import dateutil.relativedelta as relativedelta
import dateutil.rrule as rrule
import datetime

class CycleStockCount(Model):
    _name = "cycle.stock.count"
    _string = "Cycle Stock Count"
    _key = ["location_id", "product_id"]
    _fields = {
        "date": fields.Date("Latest Stock-Count Date",search=True),
        "product_id": fields.Many2One("product","Product",condition=[["type","=","stock"]],required=True,search=True),
        "abc_categ": fields.Selection([["a_","A"],["b_","B"],["c_","C"]],"ABC Category",search=True),
        "xyz_categ": fields.Selection([["x_","X"],["y_","Y"],["z_","Z"]],"XYZ Category",search=True),
        #"turnover_rate": fields.Decimal("Inventory Turnover"),
        "location_id": fields.Many2One("stock.location", "Stock Location",required=True,search=True),
        "record_id": fields.One2Many("stock.count.line","cyclecount_id","Stock Count Records"),
        "qty": fields.Decimal("Latest Expected Qty", function="get_qty"),
        "status": fields.Selection([["active","Active"],["inactive","active"]],"Status"),
    }
    _order = "date,id"

    def default_get(self,field_names=None, context={}, **kw):
        print("CycleStockCount.default_get")
        return {}

    """ Max: 
        1. Need to clean-up and remove testing functions. Working function is marked with "working"
        -done-
        2. Need to add progress bar for "start_job". Right now it will just process in backend without showing it's in progress
        -done-
        3. Need to create new Stock-Count sequence from  Cycle Stock-Count
        -nani?-
    """

    """ CALCULATIONS:
    logic-flow:
    ==> get_sku_categ : assign abc/xyz category to SKUs
        ||           RETURN product_ids according to category
        ==> _get_categ_ratio : RETURN abc/xyz ratio FROM inventory settings
    ==> recommend_cycle_counts : assign number of counts per SKU per period
    ??> need page builder to key-in stock.count.record?
    """
    
    "working - start"


    def assign_sku_categ_job(self,location_id):
        #self.start_job("assign_sku_categ",[location_id])
        self.assign_sku_categ(location_id)

    def schedule_cycle_count_job(self,location_id):
        #self.start_job("schedule_cycle_count",[location_id])
        self.schedule_cycle_count(location_id)

    def assign_sku_categ(self,location_id,exclude_zeros=True,year=None,context={}):
        print("inside assign_sku_categ")
        if not year: 
            now = datetime.datetime.now()
            year = now.year # !
        settings = get_model("settings").browse(1) 
        by_abc = settings.cycle_stockcount_abc # !
        by_xyz = settings.cycle_stockcount_xyz # !
        print("by_abc %s" % by_abc)
        print("by_xyz %s" % by_xyz)
        past_data_period = None
        if by_xyz and not by_abc:
            past_data_period = int(settings.xyz_period) # last 3,6, or 12 months
        else:
            past_data_period = 12 # to be added for by_abc
        print(f"\n\n\t pass_data_period={past_data_period}\n")
        now = datetime.datetime.now()
        latest_month = now.month
        end_date = datetime.date(year,latest_month,1)-datetime.timedelta(days=1) # end of previous month
        #start_date = datetime.date(year-(past_data_period//12),latest_month-(past_data_period%12),1)
        start_date = end_date-relativedelta.relativedelta(months=past_data_period)
        #start_date = datetime.date(year,1,1) # !
        #end_date = datetime.date(year,12,31)  # !
        db = database.get_connection()
        limit = 'NULL'
        stock_move = db.query("SELECT qty,product_id,m.location_from_id FROM stock_move as m LEFT JOIN stock_picking as p ON m.picking_id=p.id WHERE (p.type='out' AND m.location_from_id='%s' AND m.state='done' AND m.date BETWEEN '%s' AND '%s') LIMIT %s"%(location_id,start_date,end_date,limit))  
        print("start_date => %s \n end_date => %s"% (start_date,end_date))
        print("Total Number of Stock Move: %s between %s and %s" % (len(stock_move),start_date,end_date))
        #print(stock_move)
        
        """
        cond = [["state","=","done"],["picking_type","=","out"],["date",">=",start_date],["date","<=",end_date]]
        if exclude_zeros: 
            cond.append(["qty",">",0])
            #cond.append(["cost_amount",">",0])
        stock_move = get_model("stock.move").search_browse(cond,context={"no_limit":True})"""
        # get unique (product,location) combination
        sku_loc = list(set([(o.product_id,o.location_from_id) for o in stock_move]))
        summary  = dict().fromkeys(sku_loc,None)  # !
        for o in stock_move:
            prod_id = o.product_id
            loc_id = o.location_from_id
            if summary[(prod_id,loc_id)] is None:
                summary[(prod_id,loc_id)] = {"total_qty":0,"total_amt":0}
            # get aggregate
            #print(type(o.qty))
            #print(o.qty)
            #print(type(o.cost_amount))
            summary[(prod_id,loc_id)]["total_qty"] += o.qty
           # summary[(prod_id,loc_id)]["total_amt"] += o.cost_amount
        print("summary => %s" % summary)
        print(len(summary))
        # get settings 
        settings = get_model("settings").browse(1) 
        high = mid = low = None # !
        
        if by_abc and not by_xyz:
            pass

        if not by_abc and by_xyz:
            x_pct = Decimal(settings.x_by_percentage/100)
            y_pct = Decimal(settings.y_by_percentage/100)
            # z_pct = settings.z_by_percentage/100        
            sort_by_qty = sorted(summary.items(),key=lambda x : x[1]['total_qty'])
            print("sorted by qty => %s" % sort_by_qty)
            x_prod = list()
            y_prod = list()
            total_qty = sum(list(map(lambda x: x[1]['total_qty'],sort_by_qty)))
            print('total_qty %s'%total_qty)
            def assign_categ_by_cumulative_params(array,percentage,total):
              cumulative = Decimal("0.0")
              while cumulative < total*percentage and len(sort_by_qty):
                item = sort_by_qty.pop()
                cumulative += item[1]['total_qty']
                print(cumulative)
                #print('item %s'%item)
                array.append(item[0])
                if cumulative >= total*percentage:
                  print('While loop stopping condition : %s > %s' % (cumulative, total*percentage))
                  print('ratio of < %s fulfilled by %s'%(percentage,cumulative/total))
            assign_categ_by_cumulative_params(x_prod,x_pct,total_qty)
            assign_categ_by_cumulative_params(y_prod,y_pct,total_qty)
            z_prod = list(map(lambda x: x[0],sort_by_qty))
            #print(x_prod) 
            #print(y_prod)
            #print(z_prod)
            for (prod_id,loc_id) in x_prod:
                res = self.search_browse([["product_id","=",prod_id],["location_id","=",loc_id]])
                if len(res) == 0:
                    # create new instance
                    self.create({"product_id": prod_id,"location_id": loc_id,"xyz_categ":"x_","abc_categ":None})
                else:
                    # assign to category X
                    res[0].write({"xyz_categ":"x_","abc_categ":None})    
            for (prod_id,loc_id) in y_prod:
                res = self.search_browse([["product_id","=",prod_id],["location_id","=",loc_id]])
                if len(res) == 0:
                    # create new instance
                    self.create({"product_id": prod_id,"location_id": loc_id,"xyz_categ": "y_","abc_categ":None})
                else:
                    # assign to category Y
                    res[0].write({"xyz_categ":"y_","abc_categ":None})
            for (prod_id,loc_id) in z_prod:
                res = self.search_browse([["product_id","=",prod_id],["location_id","=",loc_id]])
                if len(res) == 0:
                    # create new instance
                    self.create({"product_id": prod_id,"location_id": loc_id,"xyz_categ": "z_","abc_categ":None})
                else:
                    # assign to category Z
                    res[0].write({"xyz_categ":"z_","abc_categ":None})    

        if by_abc and by_xyz:
            ## to be developed
            pass
        
    def schedule_cycle_count(self,location_id,context={}):
        settings = get_model("settings").browse(1) 
        by_abc = settings.cycle_stockcount_abc # !
        by_xyz = settings.cycle_stockcount_xyz # l
        total_count = settings.total_stockcount_per_year
        print(f"\n\n\tTotal Stock Count per year: {total_count}\n")
        job_id = context.get("job_id")
        if job_id:
            if tasks.is_aborted(job_id):
                return
            tasks.set_progress(job_id,0,"Initializing...")
        else: 
            raise Exception("No job_id")
        if by_abc and not by_xyz:
            pass

        if not by_abc and by_xyz:
            x_prod = self.search_browse([["xyz_categ","=","x_"],["location_id","=",location_id]])
            y_prod = self.search_browse([["xyz_categ","=","y_"],["location_id","=",location_id]])
            z_prod = self.search_browse([["xyz_categ","=","z_"],["location_id","=",location_id]])
            # randomize the order before scheduling
            if len(x_prod) == 0:
                loc = get_model("stock.location").browse(location_id)
                raise Exception("No Cycle Stock-Count entries for location: %s" % loc.name)
            total_z_count = settings.z_total_stockcount_per_year
            total_y_count = total_z_count*settings.y2z_ratio
            total_x_count = total_z_count*settings.x2z_ratio

            X = list()
            Y = list()
            Z = list()
            for p in x_prod:
                X.append({"cyclecount_id":p.id,"xyz_categ":p.xyz_categ,"product_id":p.product_id.id,"uom_id":p.product_id.uom_id.id}) 
            for p in y_prod:
                Y.append({"cyclecount_id":p.id,"xyz_categ":p.xyz_categ,"product_id":p.product_id.id,"uom_id":p.product_id.uom_id.id}) 
            for p in z_prod:
                Z.append({"cyclecount_id":p.id,"xyz_categ":p.xyz_categ,"product_id":p.product_id.id,"uom_id":p.product_id.uom_id.id}) 
            print(f"Total X SKUs: {len(X)}")
            print(f"Total Y SKUs: {len(Y)}")
            print(f"Total Z SKUs: {len(Z)}")
            X_ = X * total_x_count
            Y_ = Y * total_y_count
            Z_ = Z * total_z_count
            
            print(X,Y,Z)
            stock_count = dict().fromkeys(range(total_count),None)
            print(f"Total Count: {total_count}\n Total Z Count: {total_z_count}\n Total Y Count: {total_y_count}\nTotal X Count: {total_x_count}\n")
            total_z_count_per_session = math.ceil(len(Z)*total_z_count/total_count)
            total_y_count_per_session = math.ceil(len(Y)*total_y_count/total_count)
            total_x_count_per_session = math.ceil(len(X)*total_x_count/total_count)
            print(f"\n\n\t TOTAL Z,Y,X COUNT PER SESSION: \n{total_z_count_per_session}, {total_y_count_per_session}, {total_x_count_per_session} \n")
            for key in stock_count.keys():
                if stock_count[key] is None:
                    stock_count[key] = []
                for _ in range(total_z_count_per_session):
                    if len(Z_) > 0:
                        stock_count[key].append(Z_.pop())
                for _ in range(total_y_count_per_session):
                    if len(Y_) > 0:
                        stock_count[key].append(Y_.pop())
                for _ in range(total_x_count_per_session):
                    if len(X_) > 0:
                        stock_count[key].append(X_.pop())
                       
            print("%s",stock_count)
            def create_stock_count(data):
                sc = get_model("stock.count")
                sc_line = get_model("stock.count.line")
                count_id = sc.create({"location_id":location_id})
                balance = get_model("stock.balance")
       
                for d in data:
                    qty =  balance.get_qty_phys(location_id,d["product_id"],None)
                    vals = {"count_id":count_id, "product_id":d["product_id"], "cyclecount_id":d["cyclecount_id"], "prev_qty":qty, "new_qty":qty, "uom_id":d["uom_id"]}
                    sc_line.create(vals)
                return count_id
            
            record_ids = list()
            i=0
            for key in stock_count.keys():
                if job_id:
                    if tasks.is_aborted(job_id):
                        return
                    tasks.set_progress(job_id,i/len(stock_count.keys())*100,"Creating %s of %s Stock Counts"%(i,len(stock_count.keys())))
                print(key)
                print(len(stock_count[key]))
                print(stock_count[key])
                sc_id = create_stock_count(stock_count[key])  
                record_ids.append(sc_id)
                print("\n\n") 
                i+=1
            
             
            return {
                "flash":"Total of %s Stock Count session created" % len(record_ids)
            }

        if by_abc and by_xyz:
            pass
        
        "working - end"
        
    def schedule_cycle_count_old(self,context={}):
        h_freq = 4 # 4 times per month
        m_freq = 2
        l_freq = 1
        h_period = 1 # once every month
        m_period = 2 # once every 2 mmonths
        l_period = 4
        settings = get_model("settings").browse(1)  
        by_abc = settings.cycle_stockcount_abc # !
        by_xyz = settings.cycle_stockcount_xyz # !

        def _get_saturdays(year=None):
            if not year:
                year = 2021
            start = datetime.datetime(year,1,1)
            end = datetime.datetime(year,12,31)
            rr = rrule.rrule(rrule.WEEKLY,byweekday=relativedelta.SA,dtstart=before) 
            saturdays = rr.between(before,after,inc=True)  
            return saturdays
        
        def _get_saturdays_by_month(year=None):
            saturdays = _get_saturdays(year)
            # vv need to modularize 
            sat_by_month = {"1":list(),"2":list(),"3":list(),"4":list(),"5":list(),"6":list(),"7":list(),"8":list(),"9":list(),"10":list(),"11":list(),"12":list()}
            for sat in saturdays:
                month = str(sat.month)
                sat_by_month[month].append(sat)
            print(sat_by_month)
            return sat_by_month

        def _get_available_stockcount_date(stock_counts,period,saturdays):
            #annual_count = 12/period # count 12(high),6(mid),3(low) times a year
            total_sku_to_count = len(stock_counts)

            def _get_count_cycle(add_month):
                count_cycle = dict()
                month = 1
                while month <= 13:
                    start = datetime.date(year,month,1)
                    end = datetime.date(year,month+add_month,1)-datetime.timedelta(days=1) #need to modify to accomodate add_month > 12
                    count_cycle[(start,end)] = list()
                    month += add_month
                return count_cycle

            count_cycle_and_date = _get_cycle_count(period)
            for (start,end) in cycle_count.keys():
                for sat in saturdays:
                    if start < sat < end:
                        cycle_count[(start,end)].append(sat) 
                print("Total number of saturdays between %s and %s is %s"%(start,end,len(cycle_count[(start,end)])))
            return count_cycle_and_date
            
        def _add_stockcount_draft(stock_counts,date):
            m = get_model("cycle.stock.count.record")
            for obj in stock_counts:
                default = m.default_get()
                vals={"product_id":obj.product_id, "location_id":obj.location_id, "date":date, "xyz_categ":obj.xyz_categ,"abc_categ":obj.abc_categ,"cycle_count_id":obj.id}
                default.update(vals)
                m.create(default)
            return None

        def assign_stockcount(stock_counts):
            sat_by_month = _get_saturdays_by_month()
            cycles = _get_available_stockcount_date(stock_counts,period,sat_by_month)
            total_item = len(stock_counts)
            for t in cycles.keys():
                saturdays = cycles[t] # list
                num_of_sat = len(saturdays)
                sku_per_session = total_item/num_of_sat
                for sat in saturdays:
                    _add_stockcount_draft(stock_counts,sat) #Max continue here
            return None

        if by_abc and not by_xyz:
            res = self.search_browse([["xyz_categ","=","NULL"],["abc_categ","!=","NULL"]])  
            abc_categ = [o.abc_categ for o in res]
            print(len(abc_categ))
             
        if not by_abc and by_xyz:
            x_arr = self.search_browse([["xyz_categ","=","x_"],["abc_categ","=","NULL"]])
            y_arr = self.search_browse([["xyz_categ","=","y_"],["abc_categ","=","NULL"]])
            z_arr = self.search_browse([["xyz_categ","=","z_"],["abc_categ","=","NULL"]])
            # randomize the order before scheduling
            x_rand = random.sample(x_arr,len(x_arr))
            y_rand = random.sample(y_arr,len(y_arr))
            z_rand = random.sample(z_arr,len(z_arr))
            assign_stockcount(x_rand)  
            assign_stockcount(y_rand)  
            assign_stockcount(z_rand) 
 
        if by_abc and by_xyz:
            pass
        return

    """ RETRIEVE DATA FROM STOCK BALANCE

    """
    def get_qty(self,ids,context={}):
        vals = {}
        for obj in self.browse(ids):
            prod_id = obj.product_id.id
            loc_id = obj.location_id.id
            if not (loc_id or prod_id):
                vals[obj.id] = None
                continue
            stock = get_model("stock.balance").search_browse([["product_id","=",prod_id],["location_id","=",loc_id]])
            vals[obj.id] = stock.qty or 0
        return vals

    def update_cycle_count_schedule(self):
        # needed?     
        return

CycleStockCount.register()
