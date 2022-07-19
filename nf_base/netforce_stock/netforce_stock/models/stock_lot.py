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
from netforce import access
from netforce import tasks
from netforce import database
from datetime import *
import time


class StockLot(Model):
    _name = "stock.lot"
    _string = "Lot / Serial Number"
    _name_field = "number"
    _key = ["number"]
    _audit_log=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "received_date": fields.DateTime("Received Date", search=True),
        "mfg_date": fields.Date("Manufacturing Date", search=True),
        "expiry_date": fields.Date("Expiry Date", search=True),
        "life_75_date": fields.Date("75% Life Date", search=True, readonly=True, function="get_life_dates", store=True, function_multi=True),
        "life_50_date": fields.Date("50% Life Date", search=True, readonly=True, function="get_life_dates", store=True, function_multi=True),
        "life_remain_percent": fields.Decimal("Shelf Life Remain (%)", function="get_life_remain"),
        "description": fields.Text("Description", search=True),
        "weight": fields.Decimal("Weight"),
        "width": fields.Decimal("Width"),
        "length": fields.Decimal("Length"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "product_id": fields.Many2One("product","Product",search=True),
        "stock_balances": fields.One2Many("stock.balance","lot_id","Stock Quantities"),
        "service_item_id": fields.Many2One("service.item","Service Item"), # XXX: deprecated
        "expiry_moves": fields.One2Many("stock.move","expire_lot_id","Expiry Stock Transactions"),
        "lot_items": fields.One2Many("stock.lot.item","lot_id","Lot Items"),
        "lot_items_summary": fields.Char("Lot Items",function="get_lot_items_summary"), 
        "supp_lot_no": fields.Char("Supplier Lot No."),
        "url": fields.Char("URL",size=1024,search=True),
        "moves": fields.One2Many("stock.move","lot_id","Stock Transactions"),
        "validate_lines": fields.One2Many("pick.validate.line","lot_id","Validate Lines"),
        "last_location_id": fields.Many2One("stock.location","Last Location",function="get_last_location"),
        "state": fields.Selection([["active","Active"],["inactive","Inactive"]],"Status",index=True),
    }
    _order = "number desc"

    def _get_number(self, context={}):
        seq_name=context.get("sequence_name")
        seq_id = get_model("sequence").find_sequence("stock_lot",name=seq_name)
        if not seq_id:
            raise Exception("Sequence not found: %s"%seq_name)
        while 1:
            num = get_model("sequence").get_next_number(seq_id,context=context)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id,context=context)

    _defaults = {
        "number": _get_number,
    }

    def create(self,vals,context={},**kw):
        new_id=super().create(vals,context=context,**kw)
        self.function_store([new_id])
        return new_id

    def write(self,ids,vals,**kw):
        super().write(ids,vals,**kw)
        self.function_store(ids)

    def get_life_dates(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d_75=None
            d_50=None
            if obj.mfg_date and obj.expiry_date:
                d0=datetime.strptime(obj.mfg_date,"%Y-%m-%d")
                d1=datetime.strptime(obj.expiry_date,"%Y-%m-%d")
                life_days=(d1-d0).days
                days_75=int(life_days*25/100)
                days_50=int(life_days*50/100)
                d_75=(d0+timedelta(days=days_75)).strftime("%Y-%m-%d")
                d_50=(d0+timedelta(days=days_50)).strftime("%Y-%m-%d")
            vals[obj.id]={"life_75_date":d_75,"life_50_date":d_50}
        return vals

    def update_expired_lots(self,context={}):
        print("StockLot.update_expired_lots")
        access.set_active_user(1)
        access.set_active_company(1)
        settings=get_model("settings").browse(1)
        if not settings.lot_expiry_journal_id:
            raise Exception("Missing lot expiry journal")
        journal=settings.lot_expiry_journal_id
        if not journal.location_to_id:
            raise Exception("Missing to location in lot expiry journal")
        t0=datetime.today().strftime("%Y-%m-%d")
        done_move_ids=[]
        job_id=context.get("job_id")
        objs=self.search_browse([["expiry_date","<=",t0],["product_id","!=",None]])
        for i,obj in enumerate(objs): # XXX: speed
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(objs),"Updating expired lot %s of %s."%(i+1,len(objs)))
            obj.expiry_moves.delete()
            prod=obj.product_id
            for bal in obj.stock_balances:
                if bal.qty_phys<=0:
                    continue
                vals={
                    "journal_id": journal.id,
                    "date": obj.expiry_date+" 00:00:00",
                    "product_id": prod.id,
                    "location_from_id": bal.location_id.id,
                    "location_to_id": journal.location_to_id.id,
                    "lot_id": obj.id,
                    "qty": bal.qty_phys,
                    "uom_id": prod.uom_id.id,
                    "state": "done",
                    "expire_lot_id": obj.id,
                }
                move_id=get_model("stock.move").create(vals)
                done_move_ids.append(move_id)
        plan_move_ids=[]
        objs=self.search_browse([["expiry_date",">",t0],["product_id","!=",None]])
        for i,obj in enumerate(objs): # XXX: speed
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(objs),"Updating future expiring lot %s of %s."%(i+1,len(objs)))
            obj.expiry_moves.delete()
            prod=obj.product_id
            for bal in obj.stock_balances:
                if bal.qty_virt<=0:
                    continue
                vals={
                    "journal_id": journal.id,
                    "date": obj.expiry_date+" 00:00:00",
                    "product_id": prod.id,
                    "location_from_id": bal.location_id.id,
                    "location_to_id": journal.location_to_id.id,
                    "lot_id": obj.id,
                    "qty": bal.qty_virt,
                    "uom_id": prod.uom_id.id,
                    "state": "pending",
                    "expire_lot_id": obj.id,
                }
                move_id=get_model("stock.move").create(vals)
                plan_move_ids.append(move_id)
        get_model("stock.move").set_done(done_move_ids)
        return {
            "flash": "%d stock transactions completed, %d planned"%(len(done_move_ids),len(plan_move_ids)),
        }

    def get_life_remain(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.mfg_date and obj.expiry_date:
                life_days=(datetime.strptime(obj.expiry_date,"%Y-%m-%d")-datetime.strptime(obj.mfg_date,"%Y-%m-%d")).days
                t=time.strftime("%Y-%m-%d")
                days_remain=(datetime.strptime(obj.expiry_date,"%Y-%m-%d")-datetime.strptime(t,"%Y-%m-%d")).days
                percent=max(days_remain,0)*100/life_days if life_days else None
            else:
                percent=None
            vals[obj.id]=percent
        return vals

    def update_life_dates(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.mfg_date and obj.expiry_date:
                d0=datetime.strptime(obj.mfg_date,"%Y-%m-%d")
                d1=datetime.strptime(obj.expiry_date,"%Y-%m-%d")
                life_days=(d1-d0).days
                days_75=int(life_days*25/100)
                days_50=int(life_days*50/100)
                d_75=(d0+timedelta(days=days_75)).strftime("%Y-%m-%d")
                d_50=(d0+timedelta(days=days_50)).strftime("%Y-%m-%d")
                obj.write({"life_75_date":d_75,"life_50_date":d_50})

    def create_lot(self,context={}):
        vals={} # XXX
        new_id=self.create(vals)
        obj=self.browse(new_id)
        return {
            "id": new_id,
            "name": obj.number,
        }

    def add_item(self,ids,number,context={}):
        obj=self.browse(ids[0])
        if not number:
            raise Exception("Missing number")
        vals={
            "number": number,
            "lot_id": obj.id,
        }
        get_model("stock.lot.item").create(vals)

    def add_item_range(self,ids,number_from,number_to,context={}):
        obj=self.browse(ids[0])
        if not number_from:
            raise Exception("Missing start number")
        if not number_to:
            raise Exception("Missing end number")
        try:
            n0=int(number_from)
        except:
            raise Exception("Invalid start number")
        try:
            n1=int(number_to)
        except:
            raise Exception("Invalid end number")
        if n1-n0>100:
            raise Exception("Range is too big (max 100)")
        for n in range(n0,n1+1):
            vals={
                "number": str(n),
                "lot_id": obj.id,
            }
            get_model("stock.lot.item").create(vals)

    def get_lot_items_summary(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            items=[]
            for item in obj.lot_items:
                items.append(item.number or "N/A")
            vals[obj.id]=", ".join(items)
        return vals

    def check_unique_lots(self,ids,context={}):
        for obj in self.browse(ids):
            pick_ids={}
            for move in obj.moves:
                pick_ids.setdefault(move.picking_id.id,0)
                pick_ids[move.picking_id.id]+=1
            for pick_id,n in pick_ids.items():
                pick=get_model("stock.picking").browse(pick_id)
                if n>1:
                    raise Exception("Duplicate lot usage: lot=%s picking=%s"%(obj.number,pick.number))

    def check_unique_lots_validate(self,ids,context={}):
        for obj in self.browse(ids):
            pick_ids={}
            for line in obj.validate_lines:
                if not line.pick_id:
                    continue
                pick_ids.setdefault(line.pick_id.id,0)
                pick_ids[line.pick_id.id]+=1
            for pick_id,n in pick_ids.items():
                pick=get_model("stock.picking").browse(pick_id)
                if n>1:
                    raise Exception("Duplicate lot usage: lot=%s picking=%s"%(obj.number,pick.number))

    def get_last_location(self,ids,context={}):
        db=database.get_connection()
        vals={}
        for obj in self.browse(ids):
            #res=get_model("stock.move").search_browse([["lot_id","=",obj.id],["state","=","done"]],order="date desc,id desc",limit=1)
            #loc_id=res[0].location_to_id.id if res else None
            res=db.get("SELECT location_to_id FROM stock_move WHERE lot_id=%s AND state='done' ORDER BY date DESC LIMIT 1",obj.id)
            loc_id=res.location_to_id if res else None
            vals[obj.id]=loc_id
        return vals

StockLot.register()
