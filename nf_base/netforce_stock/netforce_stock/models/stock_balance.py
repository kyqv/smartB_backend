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
from netforce import database
from datetime import *
import time
from netforce import access
import math
from pprint import pprint

class StockBalance(Model):
    _name = "stock.balance"
    _string = "Stock Balance"
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True, search=True, on_delete="cascade"),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number", search=True, on_delete="cascade"),
        "location_id": fields.Many2One("stock.location", "Location", required=True, search=True, on_delete="cascade"),
        "container_id": fields.Many2One("stock.container", "Container", search=True, on_delete="cascade"),
        "qty_phys": fields.Decimal("Physical Qty", scale=6, required=True, search=True),
        "qty_virt": fields.Decimal("Virtual Qty", scale=6, required=True, search=True),
        "qty_out": fields.Decimal("Outgoing Qty", scale=6, required=True),
        "qty_in": fields.Decimal("Incoming Qty", scale=6, required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "min_qty": fields.Decimal("Min Qty"),
        "below_min": fields.Boolean("Below Min", search=True),
        "amount": fields.Decimal("Amount"),
        "last_change": fields.DateTime("Last Change"),
        "supplier_id": fields.Many2One("contact", "Supplier", store=False, search=True, function_search="search_supplier"),
        "qty2": fields.Decimal("Secondary Qty"),
        "lot_type": fields.Selection([["with_lot","With Lot"],["without_lot","Without Lot"]],"Lot Type",function_search="search_lot_type",store=False),
        "expiry_date": fields.Date("Expiry Date", function="_get_related", function_context={"path":"lot_id.expiry_date"}, function_search="_search_related", search=True),
        "agg_qty_phys": fields.Decimal("Physical Qty (Agg)", agg_function=["sum", "qty_phys"]),
        "agg_qty_virt": fields.Decimal("Virtual Qty (Agg)", agg_function=["sum", "qty_virt"]),
        "agg_amount": fields.Decimal("Cost Amount", agg_function=["sum", "amount"]),
        "master_product_id": fields.Many2One("product", "Master Product", store=False, function_search="search_master_product", search=True),
    }
    #_order = "product_id.code,location_id"
    _order = "id"
    _sql_constraints = [
        ("prod_loc_uniq", "unique (product_id, location_id, lot_id, container_id)",
         "Stock balances must have unique products and locations!"),
    ]

    def read(self, *a, **kw):
        self.update_balances()
        res = super().read(*a, **kw)
        return res

    def search(self, *a, **kw):
        self.update_balances()
        res = super().search(*a, **kw)
        return res

    def do_update_balances(self, context={}):
        print("#"*80)
        print("S"*80)
        print("#"*80)
        print("DO_UPDATE_BALANCES")
        db = database.get_connection()
        res=db.query("SELECT product_id,lot_id FROM stock_balance_update")
        if not res and not context.get("update_all"):
            print("nothing to update")
            return
        prod_lots=[]
        prod_ids=[]
        for r in res: 
            prod_lots.append((r.product_id,r.lot_id))
            prod_ids.append(r.product_id)
        prod_lots=list(set(prod_lots))
        prod_ids=list(set(prod_ids))
        pl_conds=[]
        for prod_id,lot_id in prod_lots:
            cond="product_id=%d"%prod_id
            if lot_id:
                cond+=" AND lot_id=%d"%lot_id
            else:
                cond+="AND lot_id IS NULL"
            pl_conds.append(cond)
        pl_where="("+" OR ".join(pl_conds)+")"
        print("pl_where",pl_where)
        if context.get("update_all"):
            pl_where="TRUE"
            prod_ids=get_model("product").search([])
        db.execute("LOCK stock_balance IN EXCLUSIVE MODE")
        db.execute("DELETE FROM stock_balance WHERE "+pl_where), 
        loc_ids = get_model("stock.location").search([["type", "=", "internal"]])
        if not loc_ids:
            return
        prod_uoms = {}
        res = db.query("SELECT id,uom_id FROM product WHERE id IN %s", tuple(prod_ids))
        for r in res:
            prod_uoms[r.id] = r.uom_id
        min_qtys = {}
        res = db.query(
            "SELECT location_id,product_id,min_qty,uom_id FROM stock_orderpoint WHERE product_id IN %s", tuple(prod_ids))
        for r in res:
            min_qtys[(r.location_id, r.product_id)] = (r.min_qty, r.uom_id)
        qtys = {}
        print("-"*80)
        print("calc incoming balances...")
        res = db.query(
            "SELECT location_to_id,container_id,product_id,lot_id,uom_id,state,sum(qty) AS total_qty,sum(cost_amount) AS total_amt,max(date) AS max_date,SUM(qty2) AS total_qty2 FROM stock_move WHERE location_to_id IN %s AND state IN ('pending','approved','done') AND "+pl_where+" GROUP BY location_to_id,container_id,product_id,lot_id,uom_id,state", tuple(loc_ids))
        for r in res:
            qtys.setdefault((r.location_to_id, r.container_id, r.product_id, r.lot_id), []).append(
                ("in", r.total_qty, r.total_amt or 0, r.uom_id, r.state, r.max_date, r.total_qty2 or 0))
        print("-"*80)
        print("calc outgoing balances...")
        res = db.query(
            "SELECT location_from_id,container_id,product_id,lot_id,uom_id,state,sum(qty) AS total_qty,sum(cost_amount) AS total_amt,max(date) AS max_date,SUM(qty2) AS total_qty2 FROM stock_move WHERE location_from_id IN %s AND state IN ('pending','approved','done') AND "+pl_where+" GROUP BY location_from_id,container_id,product_id,lot_id,uom_id,state", tuple(loc_ids))
        for r in res:
            qtys.setdefault((r.location_from_id, r.container_id, r.product_id, r.lot_id), []).append(
                ("out", r.total_qty, r.total_amt or 0, r.uom_id, r.state, r.max_date, r.total_qty2 or 0))
        bals = {}
        prod_loc_qtys = {}
        print("-"*80)
        print("=> qtys len",len(qtys))
        i=0
        for (loc_id, cont_id, prod_id, lot_id), totals in qtys.items():
            if i%1000==0:
                print("progress: %s / %s"%(i,len(qtys)))
            i+=1
            last_change = None
            for type, qty, amt, uom_id, state, max_date, qty2 in totals:
                if not last_change or max_date>last_change:
                    last_change = max_date
            res = min_qtys.get((loc_id, prod_id))
            if res:
                min_qty, min_uom_id = res
            else:
                min_qty = 0
                min_uom_id = None
            if lot_id:
                min_qty=0 # XXX
            bal_uom_id = prod_uoms[prod_id]
            state_qtys = {}
            state_amts = {}
            state_qtys2 = {}
            qty_in = 0
            qty_out = 0
            for type, qty, amt, uom_id, state, max_date, qty2 in totals:
                state_qtys.setdefault(state, 0)
                state_amts.setdefault(state, 0)
                state_qtys2.setdefault(state, 0)
                qty_conv = get_model("uom").convert(qty, uom_id, bal_uom_id)
                if type == "in":
                    state_qtys[state] += qty_conv
                    state_amts[state] += amt
                    state_qtys2[state] += qty2
                    if state in ("pending","approved"):
                        qty_in+=qty_conv
                elif type == "out":
                    state_qtys[state] -= qty_conv
                    state_amts[state] -= amt
                    state_qtys2[state] -= qty2
                    if state in ("pending","approved"):
                        qty_out+=qty_conv
            qty_virt = state_qtys.get("done", 0) + state_qtys.get("pending", 0) + state_qtys.get("approved", 0)
            bals[(loc_id, cont_id, prod_id, lot_id)] = {
                "qty_phys": state_qtys.get("done", 0),
                "qty_virt": qty_virt,
                "qty_in": qty_in,
                "qty_out": qty_out,
                "amt": state_amts.get("done", 0),
                "last_change": last_change,
                "uom_id": bal_uom_id,
                "min_qty": min_qty and get_model("uom").convert(min_qty, min_uom_id, bal_uom_id) or 0,
                "qty2": state_qtys2.get("done", 0),
                #"qty2": 0, # XXX
            }
            prod_loc_qtys.setdefault((loc_id, prod_id), 0)
            prod_loc_qtys[(loc_id, prod_id)] += qty_virt
        for (loc_id, prod_id), (min_qty, uom_id) in min_qtys.items():
            if (loc_id, prod_id) not in prod_loc_qtys:
                bals[(loc_id, None, prod_id, None)] = {
                    "qty_phys": 0,
                    "qty_virt": 0,
                    "qty_in": 0,
                    "qty_out": 0,
                    "amt": 0,
                    "min_qty": min_qty,
                    "uom_id": uom_id,
                    "last_change": None,
                    "qty2": 0,
                }
        print("-"*80)
        print("=> bals len",len(bals))
        total_virt_qtys={}
        for (loc_id, cont_id, prod_id, lot_id), bal_vals in bals.items():
            total_virt_qtys.setdefault(prod_id,0)
            total_virt_qtys[prod_id]+=bal_vals["qty_virt"]
        below_prods=set()
        for prod_id,qty_virt in total_virt_qtys.items():
            if qty_virt<0: # XXX: take into account min stock rules
                below_prods.add(prod_id)
        for (loc_id, cont_id, prod_id, lot_id), bal_vals in bals.items():
            bal_vals["below_min"]=prod_id in below_prods
        print("-"*80)
        print("updating balances in db...")
        i=0
        for (loc_id, cont_id, prod_id, lot_id), bal_vals in bals.items():
            if i%1000==0:
                print("progress: %s / %s"%(i,len(bals)))
            i+=1
            qty_phys = bal_vals["qty_phys"]
            qty_virt = bal_vals["qty_virt"]
            qty_in = bal_vals["qty_in"]
            qty_out = bal_vals["qty_out"]
            qty2 = bal_vals["qty2"]
            amt = bal_vals["amt"]
            min_qty = bal_vals["min_qty"]
            if qty_phys == 0 and qty_virt == 0 and min_qty == 0 and amt == 0:
                continue
            below_min = bal_vals["below_min"]
            uom_id = bal_vals["uom_id"]
            last_change = bal_vals["last_change"]
            if not uom_id:
                continue
            db.execute("INSERT INTO stock_balance (location_id,container_id,product_id,lot_id,qty_phys,qty_virt,qty_in,qty_out,amount,min_qty,uom_id,below_min,last_change,qty2) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       loc_id, cont_id, prod_id, lot_id, qty_phys, qty_virt, qty_in, qty_out, amt, min_qty, uom_id, below_min, last_change, qty2)
        db.execute("DELETE FROM stock_balance_update")

    def update_balances(self, context={}):
        self.do_update_balances()

    def get_qty_phys(self, location_id, product_id, lot_id=None):
        cond=[["location_id", "=", location_id], ["product_id", "=", product_id]]
        if lot_id: 
            cond.append(["lot_id","=",lot_id])
        qty=0
        for bal in self.search_browse(cond):
            qty+=bal.qty_phys
        return qty

    def get_qty_virt(self, location_id, product_id, lot_id=None):
        cond=[["location_id", "=", location_id], ["product_id", "=", product_id]]
        if lot_id: 
            cond.append(["lot_id","=",lot_id])
        qty=0
        for bal in self.search_browse(cond):
            qty+=bal.qty_virt
        return qty

    def get_unit_price(self, location_id, product_id):
        res = self.search([["location_id", "=", location_id], ["product_id", "=", product_id]])
        if not res:
            return 0
        obj = self.browse(res)[0]
        if obj.qty_phys:
            unit_price = obj.amount / obj.qty_phys
        else:
            unit_price = 0
        return unit_price

    def get_prod_qty(self, product_id, loc_type="internal"):
        ids = self.search([["location_id.type", "=", loc_type], ["product_id", "=", product_id]])
        qty = 0
        for obj in self.browse(ids):
            qty += obj.qty_phys
        return qty

    def make_po(self, ids, context={}):
        suppliers = {}
        for obj in self.browse(ids):
            if obj.qty_virt >= obj.min_qty:
                continue
            prod = obj.product_id
            if prod.supply_method!="purchase":
                raise Exception("Supply method for product %s is not set to 'Purchase'"%prod.code)
            res = get_model("stock.orderpoint").search([["product_id", "=", prod.id]])
            if res:
                op = get_model("stock.orderpoint").browse(res)[0]
                max_qty = op.max_qty
            else:
                max_qty = 0
            diff_qty = max_qty - obj.qty_virt
            if prod.purchase_uom_id:
                purch_uom=prod.purchase_uom_id
                if not prod.purchase_to_stock_uom_factor:
                    raise Exception("Missing purchase order -> stock uom factor for product %s"%prod.code)
                purch_qty=diff_qty/prod.purchase_to_stock_uom_factor
            else:
                purch_uom=prod.uom_id
                purch_qty=diff_qty
            if prod.purchase_qty_multiple:
                n=math.ceil(purch_qty/prod.purchase_qty_multiple)
                purch_qty=n*prod.purchase_qty_multiple
            if prod.purchase_uom_id:
                qty_stock=purch_qty*prod.purchase_to_stock_uom_factor
            else:
                qty_stock=None
            line_vals = {
                "product_id": prod.id,
                "description": prod.name_get()[0][1],
                "qty": purch_qty,
                "uom_id": purch_uom.id,
                "unit_price": prod.purchase_price or 0,
                "tax_id": prod.purchase_tax_id.id,
                "qty_stock": qty_stock,
            }
            if not prod.suppliers:
                raise Exception("Missing default supplier for product %s" % prod.name)
            contact_id = prod.suppliers[0].supplier_id.id
            suppliers.setdefault(contact_id, []).append(line_vals)
        if not suppliers:
            raise Exception("Nothing to order")
        count = 0
        for contact_id, lines in suppliers.items():
            vals = {
                "contact_id": contact_id,
                "lines": [("create", x) for x in lines],
            }
            purch_id = get_model("purchase.order").create(vals)
            count += 1
        return {
            "next": {
                "name": "purchase",
                "tab": "Draft",
            },
            "flash": "%d purchase orders created" % count,
        }

    def make_transfer(self, ids, context={}):
        if not ids:
            return
        first = self.browse(ids)[0]
        vals = {
            "location_from_id": first.location_id.id,
        }
        lines = []
        for obj in self.browse(ids):
            lines.append({
                "product_id": obj.product_id.id,
                "lot_id": obj.lot_id.id,
                "qty": obj.qty_phys,
                "uom_id": obj.uom_id.id,
                "container_id": obj.container_id.id,
            })
        vals["lines"] = [("create", v) for v in lines]
        new_id = get_model("barcode.transfer").create(vals)
        return {
            "next": {
                "name": "barcode_transfer",
                "active_id": new_id,
            },
        }

    def make_issue(self, ids, context={}):
        if not ids:
            return
        first = self.browse(ids)[0]
        vals = {
            "location_from_id": first.location_id.id,
        }
        lines = []
        for obj in self.browse(ids):
            lines.append({
                "product_id": obj.product_id.id,
                "lot_id": obj.lot_id.id,
                "qty": obj.qty_phys,
                "uom_id": obj.uom_id.id,
                "container_id": obj.container_id.id,
            })
        vals["lines"] = [("create", v) for v in lines]
        new_id = get_model("barcode.issue").create(vals)
        return {
            "next": {
                "name": "barcode_issue",
                "active_id": new_id,
            },
        }

    def search_supplier(self, clause, context={}):
        supplier_id = clause[2]
        contact = get_model("contact").browse(supplier_id)
        prod_ids = [p.product_id.id for p in contact.supplied_products]
        return [["product_id", "in", prod_ids]]

    def get_totals(self, product_ids=None, location_ids=None, lot_ids=None, container_ids=None, date_from=None, date_to=None, virt_stock=False):
        print("stock_balance.get_totals product_ids=%s location_ids=%s lot_ids=%s container_ids=%s date_from=%s date_to=%s" % (
            product_ids, location_ids, lot_ids, container_ids, date_from, date_to))
        t0 = time.time()
        q = "SELECT product_id,lot_id,location_from_id,container_from_id,location_to_id,container_to_id,uom_id,SUM(qty) AS total_qty,SUM(cost_amount) AS total_amt,SUM(qty2) AS total_qty2 FROM stock_move WHERE"
        if virt_stock:
            q+=" state in ('pending','approved','done')"
        else:
            q+=" state='done'"
        q_args = []
        if product_ids is not None:
            if product_ids:
                q += " AND product_id IN %s"
                q_args.append(tuple(product_ids))
            else:
                q += " AND false"
        if location_ids is not None:
            if location_ids:
                q += " AND (location_from_id IN %s OR location_to_id IN %s)"
                q_args += [tuple(location_ids), tuple(location_ids)]
            else:
                q += " AND false"
        if lot_ids is not None:
            if lot_ids:
                q += " AND lot_id IN %s"
                q_args.append(tuple(lot_ids))
            else:
                q += " AND false"
        if container_ids is not None:
            if container_ids:
                q += " AND (container_from_id IN %s OR container_to_id IN %s)"
                q_args += [tuple(container_ids), tuple(container_ids)]
            else:
                q += " AND false"
        if date_from:
            q += " AND date>=%s"
            q_args.append(date_from)
        if date_to:
            q += " AND date<=%s"
            q_args.append(date_to)
        q += " GROUP BY product_id,lot_id,location_from_id,container_from_id,location_to_id,container_to_id,uom_id"
        db = database.get_connection()
        res = db.query(q, *q_args)
        totals = {}
        prod_ids = set()
        for r in res:
            prod_ids.add(r.product_id)
        prod_ids = list(prod_ids)
        prod_uoms = {}
        for prod in get_model("product").browse(prod_ids):
            prod_uoms[prod.id] = prod.uom_id.id
        for r in res:
            qty = get_model("uom").convert(r.total_qty, r.uom_id, prod_uoms[r.product_id])
            amt = r.total_amt or 0
            qty2 = r.total_qty2 or 0
            k = (r.product_id, r.lot_id, r.location_from_id, r.container_from_id, r.location_to_id, r.container_to_id)
            tot = totals.setdefault(k, [0, 0, 0])
            tot[0] += qty
            tot[1] += amt
            tot[2] += qty2
        t1 = time.time()
        print("totals size: %d" % len(totals))
        print("get_totals finished in %s ms" % ((t1 - t0) * 1000))
        return totals

    def compute_key_balances(self, keys, context={}):
        print("stock_balance.compute_key_balances", keys)
        t0 = time.time()
        all_prod_ids=None
        all_loc_ids=None
        if keys:
            all_prod_ids = set()
            all_loc_ids = set()
            for prod_id, lot_id, loc_id, cont_id in keys:
                all_prod_ids.add(prod_id)
                all_loc_ids.add(loc_id)
            all_prod_ids = list(all_prod_ids)
            all_loc_ids = list(all_loc_ids)
        date_to=context.get("date_to")
        virt_stock=context.get("virt_stock")
        tots = self.get_totals(product_ids=all_prod_ids, location_ids=all_loc_ids, date_to=date_to, virt_stock=virt_stock)
        prod_tots = {}

        def get_sum(prod, lot=None, loc_from=None, loc_to=None, cont_from=None, cont_to=None):
            tot_qty = 0
            tot_amt = 0
            tot_qty2 = 0
            if prod in prod_tots:
                # XXX: can still improve speed
                for (lot_id, loc_from_id, cont_from_id, loc_to_id, cont_to_id), (qty, amt, qty2) in prod_tots[prod].items():
                    if lot==-1:
                        if lot_id:
                            continue
                    else:
                        if lot and lot_id != lot:
                            continue
                    if loc_from and loc_from_id != loc_from:
                        continue
                    if loc_to and loc_to_id != loc_to:
                        continue
                    if cont_from and cont_from_id != cont_from:
                        continue
                    if cont_to and cont_to_id != cont_to:
                        continue
                    tot_qty += qty
                    tot_amt += amt
                    tot_qty2 += qty2
            return tot_qty, tot_amt, tot_qty2
        for (prod_id, lot_id, loc_from_id, cont_from_id, loc_to_id, cont_to_id), (qty, amt, qty2) in tots.items():
            prod_tots.setdefault(
                prod_id, {})[(lot_id, loc_from_id, cont_from_id, loc_to_id, cont_to_id)] = (qty, amt, qty2)
        #pprint([(k,v) for (k,v) in prod_tots[15659].items() if k[0] is None])
        bals = {}
        for key in keys:
            prod_id, lot_id, loc_id, cont_id = key
            qty_in, amt_in, qty2_in = get_sum(prod=prod_id, lot=lot_id, loc_to=loc_id, cont_to=cont_id)
            qty_out, amt_out, qty2_out = get_sum(prod=prod_id, lot=lot_id, loc_from=loc_id, cont_from=cont_id)
            qty = qty_in - qty_out
            amt = amt_in - amt_out
            qty2 = qty2_in - qty2_out
            bals[key] = [qty, amt, qty2]
        t1 = time.time()
        print("compute_key_balances finished in %d ms" % ((t1 - t0) * 1000))
        return bals

    def search_lot_type(self, clause, context={}):
        val = clause[2]
        if val=="with_lot":
            return ["lot_id","!=",None]
        elif val=="without_lot":
            return ["lot_id","=",None]
        else:
            return []

    def check_barcode(self,barcode,no_contents=False,context={}):
        print("check_barcode '%s'"%barcode)
        barcode=barcode.strip()
        res=get_model("product").search_browse(["or",["code","=",barcode],["barcode","=",barcode]])
        if res:
            prod=res[0]
            return {
                "product": {
                    "id": prod.id,
                    "name": prod.name,
                    "code": prod.code,
                    "uom": {
                        "id": prod.uom_id.id,
                        "name": prod.uom_id.name,
                    }
                }
            }
        res=get_model("stock.lot").search_browse(["or",["number","=",barcode],["url","=",barcode]])
        if res:
            lot=res[0]
            prod=lot.product_id
            if prod:
                prod_vals={
                    "id": prod.id,
                    "name": prod.name,
                    "code": prod.code,
                    "uom": {
                        "id": prod.uom_id.id,
                        "name": prod.uom_id.name,
                    }
                }
            else:
                prod_vals=None
            return {
                "lot": {
                    "id": lot.id,
                    "number": lot.number,
                    "product": prod_vals,
                }
            }
        res=get_model("stock.container").search_browse([["number","=",barcode]])
        if res:
            cont=res[0]
            contents=[]
            for bal in self.search_browse([["container_id","=",cont.id]]):
                if bal.qty_phys<=0:
                    continue
                prod=bal.product_id
                vals={
                    "product": {
                        "id": prod.id,
                        "name": prod.name,
                        "code": prod.code,
                        "uom": {
                            "name": prod.uom_id.name,
                            "id": prod.uom_id.id,
                        }
                    }
                }
                lot=bal.lot_id
                if lot:
                    vals["lot"]={
                        "id": lot.id,
                        "number": lot.number,
                    }
                contents.append(vals)
            return {
                "container": {
                    "id": cont.id,
                    "number": cont.number,
                    "contents": contents,
                }
            }

    def search_master_product(self,clause,context={}):
        master_id=clause[2]
        return ["product_id.parent_id","=",master_id]

    def send_min_stock_notifs(self,from_addr=None,to_addrs=None,context={}):
        if not from_addr:
            raise Exception("Missing from_addr")
        if not to_addrs:
            raise Exception("Missing to_addrs")
        #objs=self.search_browse([["below_min","=",True]])
        objs=[]
        for obj in self.search_browse([]):
            if obj.qty_virt<obj.min_qty:
                objs.append(obj)
        if len(objs)==0:
            return
        body="<p>The following products are below minimum stock:</p>\n"
        subject="STCKBAL UPDATE: %d products below minimum stock"%len(objs)
        for obj in objs:
            body+="<p>Product: %s , Stock Qty: %s, Min Qty: %s</p>\n"%(obj.product_id.name,obj.qty_virt,obj.min_qty)
        vals={
            "from_addr": from_addr,
            "to_addrs": to_addrs,
            "subject": subject,
            "body": body,
            "state": "to_send",
        }
        get_model("email.message").create(vals)
        get_model("email.message").send_emails_async()

    def update_all_balances(self,context={}):
        self.do_update_balances(context={"update_all":True})

    def copy_to_transform(self,ids,context={}):
        vals={
            "lines": [],
        }
        for obj in self.browse(ids):
            line_vals={
                "type": "in",
                "product_id": obj.product_id.id,
                "lot_id": obj.lot_id.id,
                "qty": obj.qty_phys,
                "uom_id": obj.uom_id.id,
                "location_id": obj.location_id.id,
            }
            vals["lines"].append(("create",line_vals))
        trans_id=get_model("stock.transform").create(vals)
        return {
            "next": {
                "name": "transform",
                "mode": "form",
                "active_id": trans_id,
            }
        }

StockBalance.register()
