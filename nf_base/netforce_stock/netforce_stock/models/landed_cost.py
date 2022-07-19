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
import time
from netforce.utils import get_data_path

class LandedCost(Model):
    _name = "landed.cost"
    _name_field = "number"
    _string = "Landed Costs"
    _fields = {
        "number": fields.Char("Number",required=True,search=True),
        "date": fields.DateTime("Date",required=True,search=True),
        "ref": fields.Char("Ref", size=1024, search=True),
        "state": fields.Selection([["draft","Draft"],["posted","Posted"],["reversed","Reversed"]],"Status",search=True),
        "cost_allocs": fields.One2Many("landed.cost.alloc","landed_id","Cost Allocations"),
        "cost_alloc_method": fields.Selection([["amount", "By Amount"], ["qty", "By Qty"]], "Cost Allocation Method"),
        "move_id": fields.Many2One("account.move","Journal Entry"),
        "est_ship": fields.Decimal("Estimate Shipping Cost",function="_get_total",function_multi=True),
        "est_duty": fields.Decimal("Estimate Duty Cost",function="_get_total",function_multi=True),
        "act_ship": fields.Decimal("Actual Shipping Cost",function="_get_total",function_multi=True),
        "act_duty": fields.Decimal("Actual Duty Cost",function="_get_total",function_multi=True),
        "alloc_amount": fields.Decimal("Allocate Amount"),
        "alloc_type": fields.Selection([["amount","Amount"],["qty","Qty"]],"Allocation Type"),
        "alloc_cost_type": fields.Selection([["est_ship","Est Shipping"],["est_duty","Estimate Duty"],["act_ship","Actual Shipping"],["act_duty","Actual Duty"]],"Cost Type"),
        "reverse_move_id": fields.Many2One("account.move","Reverse Journal Entry"),
        "stock_moves": fields.One2Many("stock.move","related_id","Stock Movements"),
        "invoice_id": fields.Many2One("account.invoice","Invoice"),
    }

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence("landed_cost")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults={
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "cost_alloc_method": "amount",
        "number": _get_number,
    }

    def post(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj=self.browse(ids[0])
        total_qty=0
        total_amt=0
        for alloc in obj.cost_allocs:
            total_qty+=alloc.qty
            total_amt+=alloc.cost_amount or 0
        accounts={}
        for alloc in obj.cost_allocs:
            total_alloc_amt=0
            if alloc.est_ship:
                acc_id=settings.est_ship_account_id.id
                if not acc_id:
                    raise Exception("Missing estimate shipping account")
                k=(acc_id,alloc.track_id.id)
                accounts.setdefault(k,0)
                accounts[k]-=alloc.est_ship
            if alloc.est_duty:
                acc_id=settings.est_duty_account_id.id
                if not acc_id:
                    raise Exception("Missing estimate duty account")
                k=(acc_id,alloc.track_id.id)
                accounts.setdefault(k,0)
                accounts[k]-=alloc.est_duty
            if alloc.act_ship:
                acc_id=settings.act_ship_account_id.id
                if not acc_id:
                    raise Exception("Missing actual shipping account")
                k=(acc_id,alloc.track_id.id)
                accounts.setdefault(k,0)
                accounts[k]-=alloc.act_ship
            if alloc.act_duty:
                acc_id=settings.act_duty_account_id.id
                if not acc_id:
                    raise Exception("Missing actual duty account")
                k=(acc_id,alloc.track_id.id)
                accounts.setdefault(k,0)
                accounts[k]-=alloc.act_duty
            if alloc.qty_stock_lc>=alloc.qty_stock_gr:
                inv_amt=alloc.amount
                var_amt=0
            else:
                ratio=min(alloc.qty_stock_lc/alloc.qty_stock_gr,1)
                inv_amt=alloc.amount*ratio
                var_amt=alloc.amount*(1-ratio)
            if inv_amt:
                inv_account_id=alloc.location_to_id.account_id.id or alloc.product_id.stock_in_account_id.id
                if not inv_account_id:
                    raise Exception("Missing inventory account")
                k=(inv_account_id,alloc.track_id.id)
                accounts.setdefault(k,0)
                accounts[k]+=inv_amt
            if var_amt:
                var_account_id=settings.landed_cost_variance_account_id.id
                if not var_account_id:
                    raise Exception("Missing landed cost variance account")
                k=(var_account_id,alloc.track_id.id)
                accounts.setdefault(k,0)
                accounts[k]+=var_amt
        desc="Landed costs %s"%obj.number
        vals={
            "narration": desc,
            "date": obj.date,
            "related_id": "landed.cost,%d"%obj.id,
            "lines": [],
        }
        for (acc_id,track_id),amt in accounts.items():
            line_vals={
                "description": desc,
                "account_id": acc_id,
                "track_id": track_id,
                "debit": amt>0 and amt or 0,
                "credit": amt<0 and -amt or 0,
            }
            vals["lines"].append(("create",line_vals))
        account_move_id=get_model("account.move").create(vals)
        get_model("account.move").post([account_move_id])
        obj.write({"move_id":account_move_id, "state": "posted"})
        stock_move_ids=[]
        for line in obj.cost_allocs:
            move=line.move_id
            if not move.qty:
                raise Exception("Missing qty in stock movement %s"%move.number)
            #ratio=min(line.qty_stock_lc/line.qty_stock_gr,1)
            ratio=1
            journal_id=settings.landed_cost_journal_id.id
            if not journal_id:
                raise Exception("Missing landed cost journal")
            vals={
                "journal_id": journal_id,
                "date": obj.date,
                "related_id": "landed.cost,%s"%obj.id,
                #"ref": obj.number,
                "ref": line.picking_id.number,
                "product_id": move.product_id.id,
                "qty": 0,
                "uom_id": move.uom_id.id,
                "location_from_id": move.location_from_id.id,
                "location_to_id": move.location_to_id.id,
                "cost_price": 0,
                "cost_amount": line.amount*ratio,
                "move_id": account_move_id,
            }
            stock_move_id=get_model("stock.move").create(vals)
            stock_move_ids.append(stock_move_id)
        get_model("stock.move").set_done(stock_move_ids,context={"no_post": True})

    def to_draft(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.move_id:
            obj.move_id.to_draft()
            obj.move_id.delete()
        if obj.reverse_move_id:
            obj.reverse_move_id.to_draft()
            obj.reverse_move_id.delete()
        obj.stock_moves.delete()
        obj.write({"state": "draft"})

    def view_journal_entry(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.move_id:
            raise Exception("Journal entry not found")
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.move_id.id,
            }
        }

    def view_reverse_journal_entry(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.reverse_move_id:
            raise Exception("Reverse journal entry not found")
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.reverse_move_id.id,
            }
        }

    def _get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            est_ship=0
            est_duty=0
            act_ship=0
            act_duty=0
            for line in obj.cost_allocs:
                est_ship+=line.est_ship or 0
                est_duty+=line.est_duty or 0
                act_ship+=line.act_ship or 0
                act_duty+=line.act_duty or 0
            vals[obj.id]={
                "est_ship": est_ship, 
                "est_duty": est_duty, 
                "act_ship": act_ship, 
                "act_duty": act_duty, 
            }
        return vals

    def copy_to_actual(self,ids,context={}):
        obj=self.browse(ids[0])
        vals={
            "cost_allocs": [],
        }
        for line in obj.cost_allocs:
            alloc_vals={
                "move_id": line.move_id.id,
                "est_ship": -line.est_ship,
                "est_duty": -line.est_duty,
            }
            vals["cost_allocs"].append(("create",alloc_vals))
        land_id=self.create(vals)
        new_land=self.browse(land_id)
        return {
            "next": {
                "name": "landed_cost",
                "mode": "form",
                "active_id": land_id,
            },
            "flash": "Actual landed costs %s copied from estimate landed costs %s"%(new_land.number,obj.number),
        }

    def alloc_amount(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.alloc_amount is None:
            raise Exception("Missing allocation amount")
        if obj.alloc_type=="amount":
            total_amt=0
            for line in obj.cost_allocs:
                total_amt+=line.cost_amount or 0
            if not total_amt:
                raise Exception("Total amount is zero")
        elif obj.alloc_type=="qty":
            total_qty=0
            for line in obj.cost_allocs:
                total_qty+=line.qty
            if not total_qty:
                raise Exception("Total qty is zero")
        for line in obj.cost_allocs:
            if obj.alloc_type=="amount":
                alloc_amt=obj.alloc_amount*(line.cost_amount or 0)/total_amt
            elif obj.alloc_type=="qty":
                alloc_amt=obj.alloc_amount*line.qty/total_qty
            vals={
                obj.alloc_cost_type: alloc_amt,
            }
            line.write(vals)

    def reverse(self,ids,context={}):
        obj=self.browse(ids)[0]
        if obj.state!="posted":
            raise Exception("Failed to reverse landed cost: invalid state")
        if not obj.move_id:
            raise Exception("Missing journal entry")
        res=obj.move_id.reverse()
        obj.write({"state": "reversed","reverse_move_id": res["reverse_move_id"]})
        for move in obj.stock_moves:
            move.reverse()

    def merge_lc(self,ids,context={}):
        if len(ids)<2:
            raise Exception("Can not merge less than two landed costs")
        vals = {
            "cost_allocs": [],
        }
        seq=0
        for obj in self.browse(ids):
            for line in obj.cost_allocs:
                cost_vals={
                    "move_id": line.move_id.id,
                    "est_ship": line.est_ship,
                    "est_duty": line.est_duty,
                    "act_ship": line.act_ship,
                    "act_duty": line.act_duty,
                }
                vals["cost_allocs"].append(("create",cost_vals))
        new_id = self.create(vals, context=context)
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "landed_cost",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Landed costs merged",
        }

LandedCost.register()
