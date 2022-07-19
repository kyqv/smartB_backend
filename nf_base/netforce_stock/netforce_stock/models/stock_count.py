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
import time
from netforce.access import get_active_company
from netforce import access
from netforce import database
from netforce import tasks


class StockCount(Model):
    _name = "stock.count"
    _string = "Stock Count"
    _audit_log = True
    _name_field = "number"
    _multi_company = True
    _key=["number","company_id"]
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "memo": fields.Char("Memo",search=True),
        "location_id": fields.Many2One("stock.location", "Warehouse", condition=[["type", "=", "internal"]], required=True, search=True),
        "date": fields.DateTime("Date", required=True, search=True),
        "description": fields.Char("Description"),
        "state": fields.Selection([("draft", "Draft"), ("done", "Completed"), ("voided", "Voided")], "Status", required=True),
        "lines": fields.One2Many("stock.count.line", "count_id", "Lines"),
        "moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "company_id": fields.Many2One("company", "Company"),
        "journal_id": fields.Many2One("stock.journal", "Journal"),
        "total_cost_amount": fields.Decimal("Total New Cost Amount",function="get_total_cost_amount"),
        "total_prev_qty": fields.Decimal("Total Prev Qty",function="get_total_qty",function_multi=True),
        "total_new_qty": fields.Decimal("Total New Qty",function="get_total_qty",function_multi=True),
        "num_lines": fields.Integer("# Items",function="get_num_lines"),
        "product_id": fields.Many2One("product","Product",store=False,function_search="search_product",search=True),
    }
    _order="date desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="stock_count",context=context)
        if not seq_id:
            raise Exception("Missing number sequence for stock counts")
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
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "number": _get_number,
        "company_id": lambda *a: get_active_company(),
    }

    def delete_lines(self, ids, context={}):
        obj = self.browse(ids)[0]
        line_ids = [l.id for l in obj.lines]
        if line_ids:
            get_model("stock.count.line").delete(line_ids)
        return {
            "flash": "Stock count lines deleted",
        }

    def add_lines(self, ids, context={}):
        print("stock_count.add_lines")
        obj = self.browse(ids)[0]
        product_id=context.get("product_id")
        categ_id=context.get("categ_id")
        sale_invoice_uom_id=context.get("sale_invoice_uom_id")
        lot_type=context.get("lot_type")
        qty_type=context.get("qty_type")
        price_type=context.get("price_type")
        loc_id = obj.location_id.id
        cyclecount_id = context.get("cyclecount_id") # Max
        prod_lines={}
        for line in obj.lines:
            prod_lines[(line.product_id.id,line.lot_id.id)]=line.id
        n=0
        job_id=context.get("job_id")
        cond=[["location_id", "=", loc_id]]
        if product_id:
            cond.append(["product_id","=",product_id])
        bal_ids=get_model("stock.balance").search(cond)
        for i,bal in enumerate(get_model("stock.balance").browse(bal_ids)):
            print("bal %s"%i) 
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                print("percent",i*100/len(bal_ids))
                tasks.set_progress(job_id,i*100/len(bal_ids),"Checking balance %s of %s."%(i+1,len(bal_ids)))
            if bal.qty_phys == 0 and bal.amount==0:
                continue
            prod=bal.product_id
            if product_id and prod.id!=product_id:
                continue
            if categ_id and prod.categ_id.id!=categ_id:
                continue
            if sale_invoice_uom_id and prod.sale_invoice_uom_id.id!=sale_invoice_uom_id:
                continue
            lot=bal.lot_id
            if lot_type=="with_lot" and not lot:
                continue
            if lot_type=="without_lot" and lot:
                continue
            line_id=prod_lines.get((prod.id,lot.id))
            if line_id:
                continue
            vals = {
                "count_id": obj.id,
                "product_id": prod.id,
                "lot_id": bal.lot_id.id,
                "bin_location": prod.bin_location,
                "prev_qty": bal.qty_phys,
                "prev_cost_amount": bal.amount,
                "uom_id": prod.uom_id.id,
                "cyclecount_id": cyclecount_id, # Max
            }
            if qty_type=="previous":
                vals["new_qty"]=max(0,bal.qty_phys)
            else:
                vals["new_qty"]=0
            if price_type=="previous":
                vals["unit_price"]=bal.amount/bal.qty_phys if bal.qty_phys else 0
            elif price_type=="product":
                prod.set_cost_price()
                prod=prod.browse()[0]
                vals["unit_price"]=prod.cost_price
            else:
                vals["unit_price"]=0
            print("="*80)
            print("="*80)
            print("="*80)
            print("vals",vals)
            get_model("stock.count.line").create(vals)
            n+=1
        print("n=%d"%n)
        print("*"*80)
        print("*"*80)
        print("*"*80)
        print("n=%s"%n)
        return {
            "flash": "%d stock count lines added"%n,
        }

    def remove_dup(self,ids,context={}):
        obj = self.browse(ids[0])
        prod_lines={}
        dup_ids=[]
        for line in obj.lines:
            k=(line.product_id.id,line.lot_id.id)
            if k in prod_lines:
                dup_ids.append(line.id)
            else:
                prod_lines[k]=line.id
        get_model("stock.count.line").delete(dup_ids)
        return {
            "flash": "%d duplicate lines removed"%len(dup_ids),
        }

    def onchange_product(self, context):
        data = context["data"]
        loc_id = data["location_id"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        lot_id = line.get("lot_id")
        qty = get_model("stock.balance").get_qty_phys(loc_id, prod_id, lot_id)
        unit_price = get_model("stock.balance").get_unit_price(loc_id, prod_id)
        line["bin_location"] = prod.bin_location
        line["prev_qty"] = qty
        line["prev_cost_price"] = unit_price
        line["new_qty"] = qty
        line["unit_price"] = unit_price
        line["uom_id"] = prod.uom_id.id
        return data

    def update_prev_qtys(self,ids,context={}):
        print("StockCount.update_prev_qtys")
        t0=time.time()
        obj=self.browse(ids[0])
        keys=[]
        for line in obj.lines:
            key=(line.product_id.id,line.lot_id.id or -1,obj.location_id.id,None)
            keys.append(key)
        ctx={"date_to":obj.date}
        all_bals=get_model("stock.balance").compute_key_balances(keys,context=ctx)
        print("all_bals",all_bals)
        for line in obj.lines:
            key=(line.product_id.id,line.lot_id.id or -1,obj.location_id.id,None)
            bals=all_bals[key]
            qty=bals[0]
            amt=bals[1]
            line.write({
                "prev_qty": qty,
                "prev_cost_amount": amt,
            })
        t1=time.time()
        print("<< StockCount.update_prev_qtys finished in %.2f s"%(t1-t0))

    def validate(self, ids, context={}):
        print("Count.validate",ids)
        for obj_id in ids:
            obj=self.browse(obj_id)
            #obj.update_prev_qtys()
            settings = get_model("settings").browse(1)
            res = get_model("stock.location").search([["type", "=", "inventory"]])
            if not res:
                raise Exception("Inventory loss location not found")
            prod_lines={}
            for line in obj.lines:
                k=(line.product_id.id,line.lot_id.id)
                if k in prod_lines:
                    raise Exception("Duplicate item in stock count: product=%s / lot=%s"%(line.product_id.code,line.lot_id.number))
                prod_lines[k]=line.id
            invent_loc_id = res[0]
            move_ids = []
            prod_ids = []
            line_no=0
            db=database.get_connection()
            job_id=context.get("job_id")
            lines=db.query("SELECT * FROM stock_count_line WHERE count_id=%s",obj.id)
            num_lines=len(lines)
            for line in lines:
                line_no+=1
                print("line %s/%s"%(line_no,num_lines))
                if job_id:
                    if tasks.is_aborted(job_id):
                        return
                    tasks.set_progress(job_id,line_no*100/num_lines,"Validating line %s of %s."%(line_no+1,num_lines))
                #prod=line.product_id
                #if prod.type!="stock":
                #    raise Exception("Invalid product type in stock count: %s"%prod.code)
                prod_ids.append(line.product_id)
                new_cost_amount=round((line.new_qty or 0)*(line.unit_price or 0),2)
                if line.new_qty < line.prev_qty:
                    qty_diff = line.prev_qty - line.new_qty
                    amount_diff = (line.prev_cost_amount or 0) - new_cost_amount
                    price_diff = amount_diff / qty_diff if qty_diff else 0
                    loc_from_id = obj.location_id.id
                    loc_to_id = invent_loc_id
                elif line.new_qty >= line.prev_qty:
                    qty_diff = line.new_qty - line.prev_qty
                    amount_diff = new_cost_amount - (line.prev_cost_amount or 0)
                    price_diff = amount_diff / qty_diff if qty_diff else 0
                    loc_from_id = invent_loc_id
                    loc_to_id = obj.location_id.id
                vals = {
                    "journal_id": obj.journal_id.id or settings.stock_count_journal_id.id,
                    "date": obj.date,
                    "ref": obj.number,
                    "product_id": line.product_id,
                    "lot_id": line.lot_id,
                    "location_from_id": loc_from_id,
                    "location_to_id": loc_to_id,
                    "qty": qty_diff,
                    "uom_id": line.uom_id,
                    "cost_price": price_diff,
                    "cost_amount": amount_diff,
                    "related_id": "stock.count,%d" % obj.id,
                }
                #move_id = get_model("stock.move").create(vals)
                number="%s/%s"%(obj.number,line_no)
                res=db.get("INSERT INTO stock_move (journal_id,date,ref,product_id,lot_id,location_from_id,location_to_id,qty,uom_id,cost_price,cost_amount,related_id,state,number,cost_fixed,company_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft',%s,%s,%s) RETURNING id",
                    vals["journal_id"],vals["date"],vals["ref"],vals["product_id"],vals["lot_id"],vals["location_from_id"],vals["location_to_id"],vals["qty"],vals["uom_id"],vals["cost_price"],vals["cost_amount"],vals["related_id"],number,True,obj.company_id.id)
                move_id=res.id
                move_ids.append(move_id)
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,99,"Completing validation...")
            get_model("stock.move").set_done_fast(move_ids)
            obj.write({"state": "done"})
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,99,"Updading stock balances...")
            get_model("stock.balance").do_update_balances()

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.moves.delete()
        obj.write({"state": "voided"})

    def to_draft(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.moves.delete()
        obj.write({"state": "draft"})

    def copy(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "location_id": obj.location_id.id,
            "date": obj.date,
            "lines": [],
        }
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "lot_id": line.lot_id.id,
                "bin_location": line.bin_location,
                "prev_qty": line.prev_qty,
                "new_qty": line.new_qty,
                "unit_price": line.unit_price,
                "uom_id": line.uom_id.id,
            }
            vals["lines"].append(("create", line_vals))
        new_id = self.create(vals)
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "stock_count",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Stock count %s copied from %s" % (new_obj.number, obj.number),
        }

    def delete(self, ids, **kw):
        move_ids = []
        for obj in self.browse(ids):
            for move in obj.moves:
                move_ids.append(move.id)
        get_model("stock.move").delete(move_ids)
        super().delete(ids, **kw)

    def get_total_cost_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total=0
            for line in obj.lines:
                total+=line.new_cost_amount
            vals[obj.id]=total
        return vals

    def get_total_qty(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prev_qty=0
            new_qty=0
            for line in obj.lines:
                prev_qty+=line.prev_qty or 0
                new_qty+=line.new_qty or 0
            vals[obj.id]={
                "total_prev_qty": prev_qty,
                "total_new_qty": new_qty,
            }
        return vals

    def get_num_lines(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.lines)
        return vals

    def on_barcode(self,context={}):
        data = context["data"]
        count_id=data.get("id")
        if not count_id:
            raise Exception("Stock count not yet saved")
        obj=self.browse(count_id)
        loc_id=obj.location_id.id
        barcode=context["barcode"].strip()
        res=get_model("stock.lot").search([["number","=",barcode]])
        if not res:
            raise Exception("Lot not found: '%s'"%barcode)
        lot_id=res[0]
        lot=get_model("stock.lot").browse(lot_id)
        prod=lot.product_id
        if not prod: 
            raise Exception("Missing product in lot: %s"%barcode)
        prev_qty = get_model("stock.balance").get_qty_phys(loc_id, prod.id, lot_id)
        prev_cost_price = get_model("stock.balance").get_unit_price(loc_id, prod.id)
        res=get_model("stock.count.line").search([["count_id","=",count_id],["lot_id","=",lot_id]])
        if res:
            line_id=res[0]
            line=get_model("stock.count.line").browse(line_id)
            line.write({"new_qty":line.new_qty+1})
        else:
            vals={
                "count_id": count_id,
                "product_id": prod.id,
                "lot_id": lot.id,
                "new_qty": 1,
                "uom_id": prod.uom_id.id,
                "prev_qty": prev_qty,
                "prev_cost_price": prev_cost_price,
            }
            prod.set_cost_price()
            prod=prod.browse()[0]
            vals["unit_price"]=prod.cost_price
            line_id=get_model("stock.count.line").create(vals)

    def search_product(self, clause, context={}):
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        count_ids = []
        for line in get_model("stock.count.line").search_browse([["product_id","in",product_ids]]):
            count_ids.append(line.count_id.id)
        cond = [["id","in",count_ids]]
        return cond

    def onchange_date(self, context={}):
        data = context["data"]
        ctx = {
            "date": data["date"][:10],
        }
        number = self._get_number(context=ctx)
        data["number"] = number
        return data

StockCount.register()
