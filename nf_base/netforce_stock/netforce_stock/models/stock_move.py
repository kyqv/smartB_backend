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
from netforce.access import get_active_user, set_active_user
from netforce.access import get_active_company
from datetime import *
import time


class Move(Model):
    _name = "stock.move"
    _string = "Stock Movement"
    _name_field = "number"
    _multi_company = True
    #_key = ["company_id", "number"]
    _fields = {
        "ref": fields.Char("Ref", search=True),  # XXX: deprecated
        "product_id": fields.Many2One("product", "Product", required=True, search=True, condition=[["type","in",["stock","consumable","bundle"]]]),
        "location_from_id": fields.Many2One("stock.location", "From Location", required=True, search=True),
        "location_to_id": fields.Many2One("stock.location", "To Location", required=True, search=True),
        "qty": fields.Decimal("Qty", required=True, scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "picking_id": fields.Many2One("stock.picking", "Picking", on_delete="cascade"),
        "picking_type": fields.Selection([["in", "Goods Receipt"], ["internal", "Goods Transfer"], ["out", "Goods Issue"]], "Type", function="_get_related", function_search="_search_related", function_context={"path":"picking_id.type"}),
        "location_from_type": fields.Selection([["internal", "Internal"], ["customer", "Customers"], ["supplier", "Suppliers"], ["inventory", "Inventory Loss"], ["production", "Production"], ["waste", "Waste"], ["transform", "Transform"], ["view", "View"], ["other", "Other"]], "Location From Type", function="_get_related", function_search="_search_related", function_context={"path":"location_from_id.type"}),
        "picking_number": fields.Char("Picking Number", function="_get_related", function_search="_search_related", function_context={"path":"picking_id.number"}),
        "expand_picking_id": fields.Many2One("stock.picking", "Expanded Picking", on_delete="cascade"),
        "expand_move_id": fields.Many2One("stock.move", "Expanded Stock Move", on_delete="cascade"),
        "date": fields.DateTime("Date", required=True, search=True, index=True),
        "cost_price_cur": fields.Decimal("Cost Price (Cur)",scale=6), # in picking currency
        "cost_price": fields.Decimal("Cost Price", scale=6),  # in company currency
        "cost_amount": fields.Decimal("Cost Amount"), # in company currency
        "cost_fixed": fields.Boolean("Cost Fixed"), # don't calculate cost
        "state": fields.Selection([("draft", "Draft"), ("pending", "Planned"), ("approved", "Approved"), ("forecast","Forecast"), ("done", "Completed"), ("voided", "Voided")], "Status", required=True),
        "stock_count_id": fields.Many2One("stock.count", "Stock Count"),
        "move_id": fields.Many2One("account.move", "Journal Entry"),
        "user_id": fields.Many2One("base.user", "User"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "serial_no": fields.Char("Serial No.", search=True),  # XXX: deprecated
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "container_id": fields.Many2One("stock.container", "Container",search=True),
        "container_from_id": fields.Many2One("stock.container", "From Container"), # XXX: deprecated
        "container_to_id": fields.Many2One("stock.container", "To Container"), # XXX: deprecated
        "packaging_id": fields.Many2One("stock.packaging", "Packaging"),
        "num_packages": fields.Integer("# Packages"),
        "notes": fields.Text("Notes"),
        "qty2": fields.Decimal("Qty2"),
        "uom2_id": fields.Many2One("uom", "UoM2"),
        "company_id": fields.Many2One("company", "Company"),
        "invoice_id": fields.Many2One("account.invoice", "Invoice"),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["job", "Service Order"], ["account.invoice", "Invoice"], ["pawn.loan", "Loan"]], "Related To"),
        "number": fields.Char("Number", search=True),
        "journal_id": fields.Many2One("stock.journal", "Journal", required=True, search=True),
        "alloc_costs": fields.One2Many("landed.cost.alloc","move_id","Allocated Costs"),
        "alloc_cost_amount": fields.Decimal("Allocated Costs",scale=6,function="get_alloc_cost_amount"),
        "track_id": fields.Many2One("account.track.categ","Track"),
        "addons": fields.Many2Many("product.addon","Addons"),
        "expire_lot_id": fields.Many2One("stock.lot","Expiry Lot"),
        "net_weight": fields.Decimal("Net Weight"),
        "gross_weight": fields.Decimal("Gross Weight"),
        "index": fields.Integer("Index",function="get_index"),
        "index_sale": fields.Integer("Index (Sale)",function="get_index_sale"),
        "date_day": fields.Char("Day",function="get_date_agg",function_multi=True),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
        "sale_price": fields.Decimal("Sales Price", scale=6),
        "sale_amount": fields.Decimal("Sales Amount",function="get_sale_amount"),
        "validate_lines": fields.One2Many("pick.validate.line","move_id","Validate Lines"),
        "validate_qty": fields.Decimal("Validated Qty",function="get_validate_qty",function_multi=True),
        "validate_num_lots": fields.Decimal("Validated Lots",function="get_validate_qty",function_multi=True),
        "validate_weight": fields.Decimal("Validated Weight",function="get_validate_qty",function_multi=True),
        "avail_lots": fields.Many2Many("stock.lot","Available Lots",function="get_avail_lots"),
        "purchase_id": fields.Many2One("purchase.order","Purchase Order"),
        "supp_lot_no": fields.Char("Supplier Lot No."),
        "exp_date": fields.Date("Exp Date"),
        "mfg_date": fields.Date("Mfg Date"),
        "supp_inv_no": fields.Char("Supplier Inv No."),
        "sequence": fields.Integer("Sequence"),
        "expand_lines": fields.One2Many("stock.move", "expand_move_id", "Expanded Stock Movements"),
        "sale_id": fields.Many2One("sale.order","Sales Order",function="get_sale_order"),
        "sale_line_id": fields.Many2One("sale.order.line","Sales Order Line",function="get_sale_order_line"),
        "qty_stock": fields.Decimal("In Stock",function="get_qty_stock"),
        "update_balance": fields.Boolean("Update Balance"), # XXX: deprecated
        "year": fields.Char("Year", sql_function=["year", "date"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date"]),
        "month": fields.Char("Month", sql_function=["month", "date"]),
        "week": fields.Char("Week", sql_function=["week", "date"]),
        "master_product_id": fields.Many2One("product", "Master Product", store=False, function_search="search_master_product", search=True),
    }
    _order = "date desc" # XXX

    def _get_loc_from(self, context={}):
        print("_get_loc_from", context)
        data = context.get("data")
        settings = get_model("settings").browse(1)
        if data:
            journal_id = data.get("journal_id")
            if journal_id:
                journal = get_model("stock.journal").browse(journal_id)
                if journal.location_from_id:
                    return journal.location_from_id.id
        if context.get("picking_id"):
            pick_id=context.get("picking_id")
            pick=get_model("stock.picking").browse(pick_id)
            journal=pick.journal_id
        else:
            pick_type = context.get("pick_type")
            if pick_type == "in":
                journal = settings.pick_in_journal_id
            elif pick_type == "out":
                journal = settings.pick_out_journal_id
            elif pick_type == "internal":
                journal = settings.pick_internal_journal_id
            else:
                journal = None
        if journal and journal.location_from_id:
            return journal.location_from_id.id
        pick_type = context.get("pick_type")
        if pick_type != "in":
            return None
        res = get_model("stock.location").search([["type", "=", "supplier"]],order="id")
        if not res:
            return None
        return res[0]

    def _get_loc_to(self, context={}):
        print("_get_loc_to", context)
        data = context.get("data")
        settings = get_model("settings").browse(1)
        if data:
            journal_id = data.get("journal_id")
            if journal_id:
                journal = get_model("stock.journal").browse(journal_id)
                if journal.location_to_id:
                    return journal.location_to_id.id
        if context.get("picking_id"):
            pick_id=context.get("picking_id")
            pick=get_model("stock.picking").browse(pick_id)
            journal=pick.journal_id
        else:
            pick_type = context.get("pick_type")
            if pick_type == "in":
                journal = settings.pick_in_journal_id
            elif pick_type == "out":
                journal = settings.pick_out_journal_id
            elif pick_type == "internal":
                journal = settings.pick_internal_journal_id
            else:
                journal = None
        if journal and journal.location_from_id:
            return journal.location_to_id.id
        pick_type = context.get("pick_type")
        if pick_type != "out":
            return None
        res = get_model("stock.location").search([["type", "=", "customer"]])
        if not res:
            return None
        return res[0]

    def _get_uom(self, context={}):
        prod_id=context.get("product_id")
        if not prod_id:
            return
        prod=get_model("product").browse(prod_id)
        return prod.uom_id.id

    def _get_number(self, context={}):
        return "/" # XXX
        seq_id = get_model("sequence").find_sequence("stock_move")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "location_from_id": _get_loc_from,
        "location_to_id": _get_loc_to,
        "uom_id": _get_uom,
        "cost_price": 0,
        "cost_amount": 0,
        "company_id": lambda *a: get_active_company(),
        "number": _get_number,
    }

    def create(self, vals, context={}):
        pick_id = vals.get("picking_id")
        if pick_id:
            pick = get_model("stock.picking").browse(pick_id)
            vals["date"] = pick.date
            vals["picking_id"] = pick.id
            vals["journal_id"] = pick.journal_id.id
        cont_no=context.get("container_no")
        if cont_no and not vals.get("product_id"):
            res=get_model("stock.container").search([["number","=",cont_no]])
            if res:
                cont_id=res[0]
                cont=get_model("stock.container").browse(cont_id)
                contents=cont.contents
                if contents:
                    prod_id=contents[0]["product_id"]
                    prod=get_model("product").browse(prod_id)
                    vals["product_id"]=prod_id
                    vals["uom_id"]=prod.uom_id.id
        new_id = super().create(vals, context=context)
        self.update_balance([new_id])
        #self.function_store([new_id]) # XXX
        prod_id = vals["product_id"]
        user_id = get_active_user()
        set_active_user(1)
        set_active_user(user_id)
        #if context.get("prevent_dup_lots") and pick_id:
        #    get_model("stock.picking").check_dup_lots([pick_id])
        return new_id

    def write(self, ids, vals, context={}):
        prod_ids = []
        for obj in self.browse(ids):
            prod_ids.append(obj.product_id.id)
        super().write(ids, vals, context=context)
        self.update_balance(ids) # XXX: also update before write?
        prod_id = vals.get("product_id")
        if prod_id:
            prod_ids.append(prod_id)
        #self.function_store(ids) # XXX
        user_id = get_active_user()
        set_active_user(1)
        set_active_user(user_id)

    def delete(self, ids, **kw):
        move_ids=[]
        for obj in self.browse(ids):
            if obj.move_id:
                move_ids.append(obj.move_id.id)
        move_ids=list(set(move_ids))
        for move in get_model("account.move").browse(move_ids):
            move.void()
            move.delete()
        prod_ids = []
        for obj in self.browse(ids):
            prod_ids.append(obj.product_id.id)
        self.update_balance(ids)
        super().delete(ids, **kw)
        user_id = get_active_user()
        set_active_user(1)
        set_active_user(user_id)

    def update_balance(self,ids,context={}):
        if not ids:
            return
        db=database.get_connection()
        res=db.query("SELECT product_id,lot_id FROM stock_move WHERE id IN %s",tuple(ids))
        prod_lots=list(set([(r.product_id,r.lot_id) for r in res]))
        for prod_id,lot_id in prod_lots:
            db.execute("INSERT INTO stock_balance_update (product_id,lot_id) VALUES (%s,%s)",prod_id,lot_id)

    def view_stock_transaction(self, ids, context={}):
        obj = self.browse(ids[0])
        if obj.picking_id:
            pick = obj.picking_id
            if pick.type == "in":
                next = {
                    "name": "pick_in",
                    "mode": "form",
                    "active_id": pick.id,
                }
            elif pick.type == "out":
                next = {
                    "name": "pick_out",
                    "mode": "form",
                    "active_id": pick.id,
                }
            elif pick.type == "internal":
                next = {
                    "name": "pick_internal",
                    "mode": "form",
                    "active_id": pick.id,
                }
        elif obj.expand_picking_id:
            pick = obj.expand_picking_id
            if pick.type == "in":
                next = {
                    "name": "pick_in",
                    "mode": "form",
                    "active_id": pick.id,
                }
            elif pick.type == "out":
                next = {
                    "name": "pick_out",
                    "mode": "form",
                    "active_id": pick.id,
                }
            elif pick.type == "internal":
                next = {
                    "name": "pick_internal",
                    "mode": "form",
                    "active_id": pick.id,
                }
        elif obj.stock_count_id: # XXX: deprecated
            next = {
                "name": "stock_count",
                "mode": "form",
                "active_id": obj.stock_count_id.id,
            }
        elif obj.related_id and obj.related_id._model=="stock.count":
            next = {
                "name": "stock_count",
                "mode": "form",
                "active_id": obj.related_id.id,
            }
        elif obj.related_id and obj.related_id._model=="stock.grade":
            next = {
                "name": "grade",
                "mode": "form",
                "active_id": obj.related_id.id,
            }
        else:
            raise Exception("Invalid stock move")
        return {"next": next}

    def create_lots(self,ids,context={}):
        print("create_lots",ids)
        for obj in self.browse(ids):
            if obj.supp_lot_no and not obj.lot_id:
                vals={
                    "supp_lot_no": obj.supp_lot_no,
                    "expiry_date": obj.exp_date,
                    "mfg_date": obj.mfg_date,
                }
                lot_id=get_model("stock.lot").create(vals)
                obj.write({"lot_id": lot_id})

    def create_invoices(self,ids,context={}):
        print("create_invoices")
        inv_nos={}
        for obj in self.browse(ids):
            pick=obj.picking_id
            if not pick or pick.type!="in" or not pick.contact_id:
                continue
            if obj.supp_inv_no and not obj.invoice_id:
                k=(obj.supp_inv_no,pick.contact_id.id)
                inv_nos.setdefault(k,[]).append(obj)
        for (inv_no,contact_id),moves in inv_nos.items():
            contact=get_model("contact").browse(contact_id)
            vals={
                "contact_id": contact.id,
                "type": "in",
                "inv_type": "invoice",
                "sup_inv_number": inv_no,
                "lines": [],
            }
            for move in moves:
                prod=move.product_id
                price=move.cost_price or 0
                line_vals={
                    "product_id": prod.id,
                    "description": prod.name,
                    "qty": move.qty,
                    "unit_price": price,
                    "amount": move.qty*price,
                }
                vals["lines"].append(("create",line_vals))
            inv_id=get_model("account.invoice").create(vals,context={"type":"in","inv_type":"invoice"})
            for move in moves:
                move.write({"invoice_id":inv_id})

    def set_done(self,ids,context={}):
        print("stock_move.set_done",ids)
        self.create_lots(ids,context=context)
        self.create_invoices(ids,context=context)
        settings=get_model("settings").browse(1)
        prod_ids=[]
        self.write(ids,{"state":"done"},context=context)
        unique_lot_ids=[]
        for obj in self.browse(ids):
            #if obj.qty<0:
            #    raise Exception("Negative stock movement qty")
            prod=obj.product_id
            if prod.type not in ("stock","consumable","bundle"):
                raise Exception("Invalid product type")
            prod_ids.append(prod.id)
            pick=obj.picking_id
            vals={}
            if not obj.qty2 and prod.qty2_factor:
                qty2=get_model("uom").convert(obj.qty,obj.uom_id.id,prod.uom_id.id)*prod.qty2_factor
                vals["qty2"]=qty2
            elif prod.require_qty2 and obj.qty2 is None:
                raise Exception("Missing secondary qty for product %s"%prod.code)
            if pick and pick.related_id and not obj.related_id:
                vals["related_id"]="%s,%d"%(pick.related_id._model,pick.related_id.id)
            if pick and not pick.related_id and not obj.related_id:
                vals["related_id"]="%s,%d"%(pick._model,pick.id)
            if obj.location_from_id.type=="view":
                raise Exception("Source location '%s' is a view location"%obj.location_from_id.name)
            if obj.location_to_id.type=="view":
                raise Exception("Destination location '%s' is a view location"%obj.location_to_id.name)
            if prod.auto_lot and not obj.lot_id:
                lot_id=get_model("stock.lot").create({})
                vals["lot_id"]=lot_id
            elif prod.require_lot and not obj.lot_id:
                raise Exception("Missing lot for product %s"%prod.code)
            if prod.require_unique_lot and obj.lot_id:
                unique_lot_ids.append(obj.lot_id.id)
            if obj.cost_price is not None and not obj.cost_amount: # XXX
                vals["cost_amount"]=obj.cost_price*obj.qty
            elif obj.cost_price is None: # XXX
                vals["cost_amount"]=None
            if vals:
                obj.write(vals=vals,context=context)
            # change state in borrow requests # XXX: remove this
            #if not obj.related_id:
            #    if pick.related_id._model=="product.borrow":
            #        if pick.related_id.is_return_item:
            #            pick.related_id.write({"state": "done"})
            #elif obj.related_id._model=="product.borrow":
            #    if obj.related_id.is_return_item:
            #        obj.related_id.write({"state": "done"})
        prod_ids=list(set(prod_ids))
        if prod_ids and settings.stock_cost_auto_compute:
            get_model("stock.compute.cost").compute_cost([],context={"product_ids": prod_ids})
        self.set_standard_cost(ids,context=context)
        if settings.stock_cost_mode=="perpetual" and not context.get("no_post"):
            self.post(ids,context=context)
        self.update_lots(ids,context=context)
        self.update_cost_prices(ids,context=context)
        self.set_reference(ids,context=context)
        self.check_periods(ids,context=context)
        if unique_lot_ids:
            get_model("stock.lot").check_unique_lots(unique_lot_ids,context=context)
        print("<<<  stock_move.set_done")

    def set_done_fast(self,ids,context={}):
        print("stock_move.set_done_fast",ids)
        db=database.get_connection()
        settings=get_model("settings").browse(1)
        db.execute("UPDATE stock_move SET state='done' WHERE id IN %s",tuple(ids))
        self.update_balance(ids)
        print("<<<  stock_move.set_done_fast")

    def set_standard_cost(self,ids,context={}):
        for obj in self.browse(ids):
            prod=obj.product_id
            if prod.cost_method!="standard":
                continue
            price=prod.cost_price
            if price is None:
                raise Exception("Missing cost price in product %s"%prod.code)
            amt=price*obj.qty
            obj.write({"cost_price":price,"cost_amount":amt})

    def check_periods(self,ids,context={}):
        for obj in self.browse(ids):
            d=obj.date[:10]
            res=get_model("stock.period").search([["date_from","<=",d],["date_to",">=",d],["state","=","posted"]])
            if res:
                raise Exception("Failed to validate stock movement because stock period already posted")

    def set_reference(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.ref or not obj.related_id:
                continue
            ref=obj.related_id.name_get()[0][1]
            obj.write({"ref":ref})

    def reverse(self,ids,context={}):
        move_ids=[]
        for obj in self.browse(ids):
            if obj.state!="done":
                raise Exception("Failed to reverse stock movement: invalid state")
            vals={
                "journal_id": obj.journal_id.id,
                "product_id": obj.product_id.id,
                "qty": obj.qty,
                "uom_id": obj.uom_id.id,
                "location_from_id": obj.location_to_id.id,
                "location_to_id": obj.location_from_id.id,
                "cost_price_cur": obj.cost_price_cur,
                "cost_price": obj.cost_price,
                "cost_amount": obj.cost_amount,
                "qty2": obj.qty2,
                "ref": "Reverse: %s"%obj.ref if obj.ref else None,
                "related_id": "%s,%s"%(obj.related_id._model,obj.related_id.id) if obj.related_id else None,
                "picking_id": obj.picking_id.id,
            }
            move_id=self.create(vals)
            move_ids.append(move_id)
        self.set_done(move_ids)

    def get_alloc_cost_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for alloc in obj.alloc_costs:
                if alloc.landed_id.state!="posted":
                    continue
                amt+=alloc.amount or 0
            vals[obj.id]=amt
        return vals

    def post(self,ids,context={}):
        print("stock.move post",ids)
        accounts={}
        post_date=None
        pick_ids=[]
        refs=[]
        for move in self.browse(ids):
            if move.move_id:
                raise Exception("Journal entry already create for stock movement %s"%move.number)
            date=move.date[:10]
            if post_date is None:
                post_date=date
            else:
                if date!=post_date:
                    raise Exception("Failed to post stock movements because they have different dates")
            prod=move.product_id
            #desc="[%s] %s @ %s %s "%(prod.code,prod.name,round(move.qty,2),move.uom_id.name) # XXX: too many lines in JE
            desc="Inventory costing"
            acc_from_id=move.location_from_id.account_id.id
            if move.location_from_id.type=="customer":
                if prod.cogs_account_id:
                    acc_from_id=prod.cogs_account_id.id
                elif prod.categ_id and prod.categ_id.cogs_account_id:
                    acc_from_id=prod.categ_id.cogs_account_id.id
            elif move.location_from_id.type=="internal":
                if prod.stock_account_id:
                    acc_from_id=prod.stock_account_id.id
                elif prod.categ_id and prod.categ_id.stock_account_id:
                    acc_from_id=prod.categ_id.stock_account_id.id
            if not acc_from_id:
                raise Exception("Missing input account for stock movement %s (date=%s, ref=%s, product=%s)"%(move.id,move.date,move.ref,prod.name))
            acc_to_id=move.location_to_id.account_id.id
            if move.location_to_id.type=="customer":
                if prod.cogs_account_id:
                    acc_to_id=prod.cogs_account_id.id
                elif prod.categ_id and prod.categ_id.cogs_account_id:
                    acc_to_id=prod.categ_id.cogs_account_id.id
            elif move.location_to_id.type=="internal":
                if prod.stock_account_id:
                    acc_to_id=prod.stock_account_id.id
                elif prod.categ_id and prod.categ_id.stock_account_id:
                    acc_to_id=prod.categ_id.stock_account_id.id
            if not acc_to_id:
                raise Exception("Missing output account for stock movement %s (date=%s, ref=%s, product=%s)"%(move.id,move.date,move.ref,prod.name))
            track_from_id=move.location_from_id.track_id.id
            track_to_id=move.track_id.id or move.location_to_id.track_id.id # XXX
            contact_from_id=None
            contact_to_id=move.contact_id.id
            amt=move.cost_amount or 0
            if not move.move_id: # XXX: avoid create double journal entry for LC for ex
                accounts.setdefault((acc_from_id,track_from_id,contact_from_id,desc),0)
                accounts.setdefault((acc_to_id,track_to_id,contact_to_id,desc),0)
                accounts[(acc_from_id,track_from_id,contact_from_id,desc)]-=amt
                accounts[(acc_to_id,track_to_id,contact_to_id,desc)]+=amt
            if move.picking_id:
                pick_ids.append(move.picking_id.id)
            if move.ref:
                refs.append(move.ref)
        lines=[]
        for (acc_id,track_id,contact_id,desc),amt in accounts.items():
            lines.append({
                "description": desc,
                "account_id": acc_id,
                "track_id": track_id,
                "contact_id": contact_id,
                "debit": amt>0 and amt or 0,
                "credit": amt<0 and -amt or 0,
            })
        refs=list(set(refs))
        vals={
            "narration": "Inventory costing %s"%(", ".join(refs)),
            "date": post_date,
            "lines": [("create",vals) for vals in lines],
        }
        pick_ids=list(set(pick_ids))
        if len(pick_ids)==1:
            vals["related_id"]="stock.picking,%s"%pick_ids[0]
        move_id=get_model("account.move").create(vals)
        get_model("account.move").post([move_id])
        get_model("stock.move").write(ids,{"move_id":move_id})
        return move_id

    def to_draft(self,ids,context={}):
        move_ids=[]
        for obj in self.browse(ids):
            if obj.move_id:
                move_ids.append(obj.move_id.id)
        move_ids=list(set(move_ids))
        for move in get_model("account.move").browse(move_ids):
            move.void()
            move.delete()
        self.write(ids,{"state":"draft"})
        # change state in borrow requests
        for obj in self.browse(ids):
            if obj.related_id._model=="product.borrow":
               if not obj.related_id.is_return_item:
                    obj.related_id.write({"state": "approved"})

    def update_lots(self,ids,context={}):
        for obj in self.browse(ids):
            lot=obj.lot_id
            if not lot:
                continue
            if obj.location_from_id.type!="internal" and obj.location_to_id.type=="internal":
                lot.write({"received_date": obj.date})
            if not lot.product_id:
                lot.write({"product_id": obj.product_id.id})

    def update_cost_prices(self,ids,context={}):
        for obj in self.browse(ids):
            prod=obj.product_id
            if prod.cost_method not in ("fifo","average"):
                continue
            if obj.location_from_id.type!="internal" and obj.location_to_id.type=="internal":
                cost_price=get_model("uom").convert(obj.cost_price or 0,prod.uom_id.id,obj.uom_id.id)
                prod.write({"cost_price": cost_price})

    # XXX
    def get_unit_price(self,ids,context={}):
        settings=get_model("settings").browse(1)
        vals={}
        for obj in self.browse(ids):
            pick=obj.picking_id
            if pick:
                if pick.currency_rate:
                    currency_rate = pick.currency_rate
                else:
                    if pick.currency_id.id == settings.currency_id.id:
                        currency_rate = 1
                    else:
                        rate_from = pick.currency_id.get_rate(date=pick.date)
                        if not rate_from:
                            raise Exception("Missing currency rate for %s" % pick.currency_id.code)
                        rate_to = settings.currency_id.get_rate(date=pick.date)
                        if not rate_to:
                            raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                        currency_rate = rate_from / rate_to
                price=obj.unit_price_cur or 0
                price_conv=get_model("currency").convert(price,pick.currency_id.id,settings.currency_id.id,rate=currency_rate)
            else:
                price_conv=None
            vals[obj.id]=price_conv
        return vals

    def get_index(self,ids,context={}):
        pick_ids=[]
        for obj in self.browse(ids):
            pick_ids.append(obj.picking_id.id)
        pick_ids=list(set(pick_ids))
        vals={}
        for pick in get_model("stock.picking").browse(pick_ids):
            i=1
            for line in pick.lines:
                if line.id in ids:
                    vals[line.id]=i
                i+=1
        return vals

    def get_index_sale(self,ids,context={}):
        pick_ids=[]
        for obj in self.browse(ids):
            pick_ids.append(obj.picking_id.id)
        pick_ids=list(set(pick_ids))
        vals={}
        for pick in get_model("stock.picking").browse(pick_ids):
            i=0
            for line in pick.lines:
                prod=line.product_id
                so_line=None
                if obj.related_id and obj.related_id._model == "sale.order":
                    so_line_id = obj.related_id.find_sale_line(prod.id)
                    if so_line_id:
                        so_line = get_model("sale.order.line").browse(so_line_id)
                if so_line:
                    i+=1
                if line.id in ids:
                    vals[line.id]=i if so_line else None
        return vals

    def get_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d=datetime.strptime(obj.date,"%Y-%m-%d %H:%M:%S")
            month=d.strftime("%Y-%m")
            week=d.strftime("%Y-W%W")
            day=d.strftime("%Y-%m-%d")
            vals[obj.id]={
                "date_day": day,
                "date_week": week,
                "date_month": month,
            }
        return vals

    def get_sale_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=obj.qty*(obj.sale_price or 0)
        return vals

    def get_validate_qty(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            qty=0
            num_lots=0
            weight=0
            for line in obj.validate_lines:
                qty+=line.qty
                if line.lot_id:
                    num_lots+=1
                weight+=line.qty2 or 0
            vals[obj.id]={
                "validate_qty": qty,
                "validate_num_lots": num_lots,
                "validate_weight": weight,
            }
        return vals

    def get_avail_lots(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod_id=obj.product_id.id
            lot_ids=[]
            for bal in get_model("stock.balance").search_browse([["product_id","=",prod_id],["lot_id","!=",None]]):
                lot_ids.append(bal.lot_id.id)
            lot_ids=list(set(lot_ids))
            vals[obj.id]=lot_ids
        return vals

    def validate_transaction(self,journal_code=None,product_id=None,qty=None,qty2=None,weight=None,lot_id=None,new_lot=False,context={}):
        res=get_model("stock.journal").search([["code","=",journal_code]])
        if not res:
            raise Exception("Journal not found: %s"%journal_code)
        journal_id=res[0]
        journal=get_model("stock.journal").browse(journal_id)
        loc_from_id=journal.location_from_id.id
        if not loc_from_id:
            raise Exception("Missing from location in journal %s"%journal_code)
        loc_to_id=journal.location_to_id.id
        if not loc_to_id:
            raise Exception("Missing to location in journal %s"%journal_code)
        if not journal.type:
            raise Exception("Missing type in journal %s"%journal_code)
        if journal.type not in ("in","out","internal"):
            raise Exception("Missing type")
        if new_lot:
            lot_vals={
                "product_id": product_id,
                "weight": weight,
            }
            ctx={
                "sequence_name": context.get("lot_sequence_name"),
                "sequence_params": context.get("lot_sequence_params"),
            }
            lot_id=get_model("stock.lot").create(lot_vals,context=ctx)
        elif lot_id:
            if qty2 is None:
                lot=get_model("stock.lot").browse(lot_id)
                qty2=lot.weight
        pick_type=journal.type
        pick_vals={
            "journal_id": journal_id,
            "type": pick_type,
            "lines": [],
        }
        prod=get_model("product").browse(product_id)
        move_vals={
            "journal_id": journal_id,
            "location_from_id": loc_from_id,
            "location_to_id": loc_to_id,
            "product_id": product_id,
            "qty": qty,
            "uom_id": prod.uom_id.id,
            "qty2": weight,
            "lot_id": lot_id,
        }
        pick_vals["lines"].append(("create",move_vals))
        pick_id=get_model("stock.picking").create(pick_vals,context={"pick_type":pick_type,"journal_id":journal_id})
        pick=get_model("stock.picking").browse(pick_id)
        pick.set_done()
        return {
            "picking_id": pick.id,
            "number": pick.number,
            "move_id": pick.lines[0].id,
        }

    def get_sale_order(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.related_id and obj.related_id._model=="sale.order":
                vals[obj.id]=obj.related_id.id
            else:
                vals[obj.id]=None
        return vals

    def get_sale_order_line(self,ids,context={}):
        sale_ids=[]
        for obj in self.browse(ids):
            sale_id=obj.sale_id.id
            if sale_id:
                sale_ids.append(sale_id)
        line_ids={}
        for sale in get_model("sale.order").browse(sale_ids):
            for line in sale.lines:
                line_ids[(sale.id,line.product_id.id)]=line.id
        vals={}
        for obj in self.browse(ids):
            sale_id=obj.sale_id.id
            vals[obj.id]=line_ids.get((sale_id,obj.product_id.id)) if sale_id else None
        return vals

    def get_qty_stock_old(self,ids,context={}):
        print("get_qty_stock",ids)
        get_model("stock.balance").update_balances()
        prod_ids=[]
        lot_ids=[]
        for obj in self.browse(ids):
            prod_ids.append(obj.product_id.id)
            if obj.lot_id:
                lot_ids.append(obj.lot_id.id)
        prod_ids=list(set(prod_ids))
        lot_ids=list(set(lot_ids))
        db=database.get_connection()
        prod_qtys={}
        if prod_ids:
            res=db.query("SELECT product_id,location_id,SUM(qty_phys) AS qty_phys FROM stock_balance WHERE product_id IN %s GROUP BY product_id,location_id",tuple(prod_ids))
            for r in res:
                k=(r.product_id,r.location_id)
                prod_qtys[k]=r.qty_phys
        lot_qtys={}
        if lot_ids:
            res=db.query("SELECT product_id,lot_id,location_id,qty_phys FROM stock_balance WHERE lot_id IN %s",tuple(lot_ids))
            for r in res:
                k=(r.product_id,r.lot_id,r.location_id)
                lot_qtys[k]=r.qty_phys
        vals={}
        for obj in self.browse(ids):
            prod_id=obj.product_id.id
            loc_id=obj.location_from_id.id
            lot_id=obj.lot_id.id
            if obj.lot_id:
                k=(prod_id,lot_id,loc_id)
                qty=lot_qtys.get(k,0)
            else:
                k=(prod_id,loc_id)
                qty=prod_qtys.get(k,0)
            vals[obj.id]=qty
        return vals

    def get_qty_stock(self,ids,context={}):
        print("get_qty_stock",ids)
        keys=[]
        for obj in self.browse(ids):
            key=(obj.product_id.id,obj.lot_id.id or -1,obj.location_from_id.id,None)
            keys.append(key)
        date_to=obj.picking_id.date if obj.picking_id else obj.date
        ctx={"date_to":obj.date}
        all_bals=get_model("stock.balance").compute_key_balances(keys,context=ctx)
        print("all_bals",all_bals)
        vals={}
        for obj in self.browse(ids):
            key=(obj.product_id.id,obj.lot_id.id or -1,obj.location_from_id.id,None)
            bals=all_bals[key]
            qty=bals[0]
            vals[obj.id]=qty
        return vals

    def search_master_product(self,clause,context={}):
        master_id=clause[2]
        return ["product_id.parent_id","=",master_id]

Move.register()
