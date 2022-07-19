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
from netforce import access
from netforce.access import get_active_company, get_active_user, set_active_user,set_active_company
from netforce import access
from netforce import utils
from decimal import Decimal
from datetime import *
import time


class PurchaseOrder(Model):
    _name = "purchase.order"
    _string = "Purchase Order"
    _audit_log = True
    _name_field = "number"
    _multi_company = True
    _key = ["company_id", "number"]
    _content_search=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Ref", search=True),
        "contact_id": fields.Many2One("contact", "Supplier", required=True, search=True, condition=[["supplier","=",True]]),
        "contact_person_id": fields.Many2One("contact", "Contact Person", search=True),
        "customer_id": fields.Many2One("contact", "Customer", search=True, condition=[["customer","=",True]]),
        "date": fields.Date("Date", required=True, search=True),
        "date_required": fields.Date("Required Date"),
        "state": fields.Selection([("draft", "Draft"), ("wait_approve","Awaiting Approval"), ("confirmed", "Confirmed"), ("done", "Completed"), ("voided", "Voided")], "Status", required=True),
        "lines": fields.One2Many("purchase.order.line", "order_id", "Lines"),
        "amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True, store=True),
        "amount_tax": fields.Decimal("Tax Amount", function="get_amount", function_multi=True, store=True),
        "amount_total": fields.Decimal("Total", function="get_amount", function_multi=True, store=True),
        "amount_total_cur": fields.Decimal("Total (Converted)", function="get_amount", function_multi=True, store=True),
        "amount_total_words": fields.Char("Total Words", function="get_amount_total_words"),
        "qty_total": fields.Decimal("Total Quantity", function="get_qty_total"),
        "qty_stock_total": fields.Decimal("Total Quantity (Stock UoM)", function="get_qty_stock_total"),
        "currency_id": fields.Many2One("currency", "Currency", required=True),
        "tax_type": fields.Selection([["tax_ex", "Tax Exclusive"], ["tax_in", "Tax Inclusive"], ["no_tax", "No Tax"]], "Tax Type", required=True),
        "invoice_lines": fields.One2Many("account.invoice.line", "related_id", "Invoice Lines"),
        #"stock_moves": fields.One2Many("stock.move","purch_id","Stock Moves"),
        "invoices": fields.Many2Many("account.invoice", "Invoices", function="get_invoices"),
        "pickings": fields.Many2Many("stock.picking", "Stock Pickings", function="get_pickings"),
        "is_delivered": fields.Boolean("Delivered", function="get_delivered"),
        "is_paid": fields.Boolean("Paid", function="get_paid"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "location_id": fields.Many2One("stock.location", "Warehouse"),  # XXX: deprecated
        "delivery_date": fields.Date("Delivery Date"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),  # XXX: deprecated
        "payment_terms": fields.Text("Payment Terms"), # XXX: deprecated
        "pay_term_id": fields.Many2One("payment.term","Payment Terms"),
        "ship_term_id": fields.Many2One("ship.term", "Shipping Terms"),
        "price_list_id": fields.Many2One("price.list", "Price List", condition=[["type", "=", "purchase"]]),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "company_id": fields.Many2One("company", "Company"),
        "purchase_type_id": fields.Many2One("purchase.type", "Purchase Type"),
        "other_info": fields.Text("Other Info"),
        "bill_address_id": fields.Many2One("address", "Billing Address"),
        "ship_address_id": fields.Many2One("address", "Shipping Address"),
        "sequence_id": fields.Many2One("sequence", "Number Sequence"),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "agg_amount_total": fields.Decimal("Total Amount", agg_function=["sum", "amount_total"]),
        "year": fields.Char("Year", sql_function=["year", "date"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date"]),
        "month": fields.Char("Month", sql_function=["month", "date"]),
        "week": fields.Char("Week", sql_function=["week", "date"]),
        "agg_amount_subtotal": fields.Decimal("Total Amount w/o Tax", agg_function=["sum", "amount_subtotal"]),
        "user_id": fields.Many2One("base.user", "Owner", search=True),
        "contact_user_id": fields.Many2One("base.user", "Procurement Person", search=True),
        "procurement_employee_id": fields.Many2One("hr.employee", "Procurement Person", search=True),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "related_id": fields.Reference([["sale.order","Sales Order"],["stock.consign","Consignment Stock"]],"Related To"),
        "sale_orders": fields.One2Many("sale.order","related_id","Sales Orders"),
        "gradings": fields.One2Many("stock.grade","related_id","Gradings"),
        "approvals": fields.One2Many("approval","related_id","Approvals"),
        "purchase_request_id": fields.Many2One("purchase.request","Purchase Request"),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
        "date_approve": fields.DateTime("Approved Date",search=True,readonly=True),
        "project_id": fields.Many2One("project","Project", search=True),
    }
    _order = "date desc,number desc"

    _sql_constraints = [
        ("key_uniq", "unique (company_id, number)", "The number of each company must be unique!")
    ]

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="purchase_order",context=context)
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id,context=context)
            user_id = get_active_user()
            set_active_user(1)
            res = self.search([["number", "=", num]])
            set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id,context=context)

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "number": _get_number,
        "currency_id": _get_currency,
        "tax_type": "tax_ex",
        "company_id": lambda *a: get_active_company(),
        "user_id": lambda *a: get_active_user(),
    }

    def create(self, vals, **kw):
        id = super(PurchaseOrder, self).create(vals, **kw)
        self.function_store([id])
        return id

    def write(self, ids, vals, **kw):
        super(PurchaseOrder, self).write(ids, vals, **kw)
        self.function_store(ids)

    def confirm(self, ids, context={}):
        settings = get_model("settings").browse(1)
        if settings.approve_purchase and not access.check_permission_other("approve_purchase"):
            raise Exception("User does not have permission to approve purchase orders (approve_purchase).")
        for obj in self.browse(ids):
            if obj.state not in ("draft","wait_approve"):
                raise Exception("Invalid state")
            for line in obj.lines:
                prod = line.product_id
                if prod and prod.type in ("stock", "consumable", "bundle") and not line.location_id:
                    raise Exception("Missing location for product %s" % prod.code)
            obj.write({"state": "confirmed"})
            if settings.purchase_copy_picking:
                res=obj.copy_to_picking()
                if res and res.get("picking_id"):
                    picking_id=res["picking_id"]
                    get_model("stock.picking").pending([picking_id])
            if settings.purchase_copy_invoice:
                obj.copy_to_invoice()
            obj.trigger("confirm")

    def done(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state != "confirmed":
                raise Exception("Invalid state")
            obj.write({"state": "done"})

    def reopen(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state != "done":
                raise Exception("Invalid state")
            obj.write({"state": "confirmed"})

    def to_draft(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "draft"})
            obj.approvals.delete()

    def get_amount(self, ids, context={}):
        settings = get_model("settings").browse(1)
        res = {}
        for obj in self.browse(ids):
            vals = {}
            subtotal = 0
            tax = 0
            for line in obj.lines:
                if line.tax_id:
                    line_tax = get_model("account.tax.rate").compute_tax(
                        line.tax_id.id, line.amount, tax_type=obj.tax_type)
                else:
                    line_tax = 0
                tax += line_tax
                if obj.tax_type == "tax_in":
                    subtotal += line.amount - line_tax
                else:
                    subtotal += line.amount
            vals["amount_subtotal"] = subtotal
            vals["amount_tax"] = tax
            vals["amount_total"] = subtotal + tax
            vals["amount_total_cur"] = get_model("currency").convert(
                vals["amount_total"], obj.currency_id.id, settings.currency_id.id)
            res[obj.id] = vals
        return res

    def get_qty_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.qty for line in obj.lines])
            res[obj.id] = qty or 0
        return res

    def get_qty_stock_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.qty_stock_func or 0 for line in obj.lines])
            res[obj.id] = qty or 0
        return res

    def update_amounts(self, context):
        data = context["data"]
        data["amount_subtotal"] = 0
        data["amount_tax"] = 0
        tax_type = data["tax_type"]
        for line in data["lines"]:
            if not line:
                continue
            amt = Decimal(((line.get("qty") or 0) * (line.get("unit_price") or 0)) - (line.get("discount_amount") or 0))
            line["amount"] = amt
            tax_id = line.get("tax_id")
            if tax_id:
                tax = get_model("account.tax.rate").compute_tax(tax_id, amt, tax_type=tax_type)
                data["amount_tax"] += tax
            else:
                tax = 0
            if tax_type == "tax_in":
                data["amount_subtotal"] += amt - tax
            else:
                data["amount_subtotal"] += amt
        data["amount_total"] = data["amount_subtotal"] + data["amount_tax"]
        return data

    def onchange_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        line["description"] = prod.description or prod.name
        line["qty"] = 1
        line["uom_id"] = prod.purchase_uom_id.id or prod.uom_id.id
        pricelist_id = data["price_list_id"]
        price = None
        if pricelist_id:
            price = get_model("price.list").get_price(pricelist_id, prod.id, 1)
            price_list = get_model("price.list").browse(pricelist_id)
            price_currency_id = price_list.currency_id.id
        if price is None:
            price = prod.purchase_price
            settings = get_model("settings").browse(1)
            price_currency_id = prod.purchase_currency_id.id or settings.currency_id.id
        if price is not None:
            currency_id = data["currency_id"]
            price_cur = get_model("currency").convert(price, price_currency_id, currency_id, round=True)
            line["unit_price"] = price_cur
        if prod.categ_id and prod.categ_id.purchase_tax_id:
            tax_id = prod.categ_id.purchase_tax_id.id
            line["tax_id"] = tax_id
        if prod.purchase_tax_id:
            tax_id = prod.purchase_tax_id.id
            line["tax_id"] = tax_id
        contact_id=data.get("contact_id")
        if contact_id:
            contact=get_model("contact").browse(contact_id)
            if contact.purchase_tax_id:
                tax_id=contact.purchase_tax_id.id
                line["tax_id"] = tax_id
        if prod.locations:
            line["location_id"] = prod.locations[0].location_id.id
        data = self.update_amounts(context)
        return data

    def onchange_price_list(self, context):
        data = context["data"]
        for line in data["lines"]:
            prod_id = line.get("product_id")
            if not prod_id:
                continue
            prod = get_model("product").browse(prod_id)
            line["description"] = prod.description or prod.name
            line["qty"] = 1
            line["uom_id"] = prod.purchase_uom_id.id or prod.uom_id.id
            pricelist_id = data["price_list_id"]
            price = None
            if pricelist_id:
                price = get_model("price.list").get_price(pricelist_id, prod.id, 1)
                price_list = get_model("price.list").browse(pricelist_id)
                price_currency_id = price_list.currency_id.id
            if price is None:
                price = prod.purchase_price
                settings = get_model("settings").browse(1)
                price_currency_id = settings.currency_id.id
            if price is not None:
                currency_id = data["currency_id"]
                price_cur = get_model("currency").convert(price, price_currency_id, currency_id, round=True)
                line["unit_price"] = price_cur
        data = self.update_amounts(context)
        return data

    def onchange_qty(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        pricelist_id = data["price_list_id"]
        qty = line["qty"]
        if not line["unit_price"] and prod_id:
            prod = get_model("product").browse(prod_id)
            price = None
            if pricelist_id:
                price = get_model("price.list").get_price(pricelist_id, prod.id, qty)
                price_list = get_model("price.list").browse(pricelist_id)
                price_currency_id = price_list.currency_id.id
            if price is None:
                price = prod.purchase_price
                settings = get_model("settings").browse(1)
                price_currency_id = settings.currency_id.id
            if price is not None:
                currency_id = data["currency_id"]
                price_cur = get_model("currency").convert(price, price_currency_id, currency_id)
                line["unit_price"] = price_cur
        data = self.update_amounts(context)
        return data

    def copy_to_picking(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids[0])
        contact = obj.contact_id
        pick_vals = {
            "type": "in",
            "ref": obj.number,
            "related_id": "purchase.order,%s" % obj.id,
            "contact_id": contact.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
        }
        if obj.delivery_date:
            pick_vals["date"]=obj.delivery_date
        if contact and contact.pick_in_journal_id:
            pick_vals["journal_id"] = contact.pick_in_journal_id.id
        res = get_model("stock.location").search([["type", "=", "supplier"]],order="id")
        if not res:
            raise Exception("Supplier location not found")
        supp_loc_id = res[0]
        res = get_model("stock.location").search([["type", "=", "internal"]])
        if not res:
            raise Exception("Warehouse not found")
        wh_loc_id = res[0]
        if not settings.currency_id:
            raise Exception("Missing currency in financial settings")
        for line in obj.lines:
            prod = line.product_id
            if prod.type not in ("stock", "consumable"):
                continue
            remain_qty = (line.qty_stock or line.qty) - line.qty_received
            if remain_qty <= 0:
                continue
            unit_price=line.amount/line.qty if line.qty else 0
            if obj.tax_type=="tax_in":
                if line.tax_id:
                    tax_amt = get_model("account.tax.rate").compute_tax(
                        line.tax_id.id, unit_price, tax_type=obj.tax_type)
                else:
                    tax_amt = 0
                cost_price_cur=round(unit_price-tax_amt,2)
            else:
                cost_price_cur=unit_price
            if line.qty_stock:
                purch_uom=prod.uom_id
                if not prod.purchase_to_stock_uom_factor:
                    raise Exception("Missing purchase order to stock UoM factor for product %s"%prod.code)
                cost_price_cur/=prod.purchase_to_stock_uom_factor
            else:
                purch_uom=line.uom_id
            cost_price=get_model("currency").convert(cost_price_cur,obj.currency_id.id,settings.currency_id.id)
            cost_amount=cost_price*remain_qty
            line_vals = {
                "product_id": prod.id,
                "qty": remain_qty,
                "uom_id": purch_uom.id,
                "cost_price_cur": cost_price_cur,
                "cost_price": cost_price,
                "cost_amount": cost_amount,
                "location_from_id": supp_loc_id,
                "location_to_id": line.location_id.id or wh_loc_id,
                "related_id": "purchase.order,%s" % obj.id,
            }
            pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            #raise Exception("Nothing left to receive")
            return {
                "alert": "Nothing left to receive",
            }
        pick_id = get_model("stock.picking").create(pick_vals, {"pick_type": "in", "contact_code": obj.contact_id.code})
        pick = get_model("stock.picking").browse(pick_id)
        return {
            "next": {
                "name": "pick_in",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Goods receipt %s created from purchase order %s" % (pick.number, obj.number),
            "picking_id": pick_id,
        }

    def copy_to_invoice(self, ids, context={}):
        id = ids[0]
        obj = self.browse(id)
        contact = obj.contact_id
        inv_vals = {
            "type": "in",
            "inv_type": "invoice",
            "ref": obj.number,
            "related_id": "purchase.order,%s" % obj.id,
            "contact_id": obj.contact_id.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
            "tax_type": obj.tax_type,
            "procurement_employee_id": obj.procurement_employee_id.id,
        }
        if contact.purchase_journal_id:
            inv_vals["journal_id"] = contact.purchase_journal_id.id
            if contact.purchase_journal_id.sequence_id:
                inv_vals["sequence_id"] = contact.purchase_journal_id.sequence_id.id
        for line in obj.lines:
            prod = line.product_id
            remain_qty = line.qty - line.qty_invoiced
            if remain_qty <= 0:
                continue
            purch_acc_id=None
            if prod:
                purch_acc_id=prod.purchase_account_id.id
                if not purch_acc_id and prod.parent_id:
                    purch_acc_id=prod.parent_id.purchase_account_id.id
                if not purch_acc_id and prod.categ_id and prod.categ_id.purchase_account_id:
                    purch_acc_id=prod.categ_id.purchase_account_id.id
            line_vals = {
                "product_id": prod.id,
                "description": line.description,
                "qty": remain_qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "account_id": purch_acc_id,
                "tax_id": line.tax_id.id,
                "amount": line.amount,
                "related_id": "purchase.order,%s"%obj.id,
                "track_id": line.track_id.id, #2020-11-02 Chin
                "track2_id": line.track2_id.id, #2020-11-02 Chin
                "notes": line.notes,
            }
            inv_vals["lines"].append(("create", line_vals))
        if not inv_vals["lines"]:
            raise Exception("Nothing left to invoice")
        inv_id = get_model("account.invoice").create(inv_vals, {"type": "in", "inv_type": "invoice"})
        inv = get_model("account.invoice").browse(inv_id)
        return {
            "next": {
                "name": "supp_invoice",
                "mode": "form",
                "form_layout": "supp_invoice_form",
                "active_id": inv_id,
                "target": "new_window", #2020-11-02 Chin
            },
            "flash": "Invoice %s created from purchase order %s" % (inv.number, obj.number),
        }

    def copy_to_cust_invoice(self, ids, context={}):
        id = ids[0]
        obj = self.browse(id)
        if not obj.customer_id:
            raise Exception("Missing customer in purchase order")
        inv_vals = {
            "type": "out",
            "inv_type": "invoice",
            "ref": obj.number,
            "related_id": "purchase.order,%s" % obj.id,
            "contact_id": obj.customer_id.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
            "tax_type": obj.tax_type,
            "procurement_employee_id": obj.procurement_employee_id.id,
        }
        for line in obj.lines:
            prod = line.product_id
            line_vals = {
                "product_id": prod.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "amount": line.amount,
                "related_id": "purchase.order,%s"%obj.id,
                "notes": line.notes,
            }
            inv_vals["lines"].append(("create", line_vals))
        inv_id = get_model("account.invoice").create(inv_vals, {"type": "out", "inv_type": "invoice"})
        inv = get_model("account.invoice").browse(inv_id)
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv_id,
            },
            "flash": "Customer invoice %s created from purchase order %s" % (inv.number, obj.number),
        }

    def get_delivered(self, ids, context={}):
        vals = {}
        #import pdb; pdb.set_trace()
        for obj in self.browse(ids):
            is_delivered = True
            for line in obj.lines:
                prod = line.product_id
                if prod.type not in ("stock", "consumable"):
                    continue
                remain_qty = line.qty - line.qty_received
                if remain_qty > 0:
                    is_delivered = False
                    break
            vals[obj.id] = is_delivered
        return vals

    def get_paid(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            amt_paid = 0
            for inv_line in obj.invoice_lines:
                inv=inv_line.invoice_id
                if inv.state != "paid":
                    continue
                amt_paid += inv_line.amount
            is_paid = amt_paid >= obj.amount_subtotal
            vals[obj.id] = is_paid
        return vals

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        for pick in obj.pickings:
            if pick.state != "voided":
                raise Exception("There are still goods receipts for this purchase order")
        for inv in obj.invoices:
            if inv.state != "voided":
                raise Exception("There are still invoices for this purchase order")
        obj.write({"state": "voided"})

    def copy(self, ids, context):
        obj = self.browse(ids)[0]
        vals = {
            "contact_id": obj.contact_id.id,
            "date": obj.date,
            "ref": obj.ref,
            "currency_id": obj.currency_id.id,
            "tax_type": obj.tax_type,
            "other_info": obj.other_info,
            "lines": [],
        }
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
            }
            vals["lines"].append(("create", line_vals))
        new_id = self.create(vals)
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "purchase",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Purchase order %s copied to %s" % (obj.number, new_obj.number),
        }

    def get_invoices(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            inv_ids = []
            for inv_line in obj.invoice_lines:
                inv_id = inv_line.invoice_id.id
                if inv_id not in inv_ids:
                    inv_ids.append(inv_id)
            vals[obj.id] = inv_ids
        return vals

    def get_pickings(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            pick_ids = []
            for move in obj.stock_moves:
                pick_id = move.picking_id.id
                if pick_id not in pick_ids:
                    pick_ids.append(pick_id)
            vals[obj.id] = pick_ids
        return vals

    def onchange_contact(self, context):
        data = context["data"]
        contact_id = data.get("contact_id")
        if not contact_id:
            return {}
        contact = get_model("contact").browse(contact_id)
        data["contact_person_id"]=contact.contact_person_id.id
        data["pay_term_id"] = contact.purchase_pay_term_id.id
        data["price_list_id"] = contact.purchase_price_list_id.id
        data["bill_address_id"] = contact.get_address(pref_type="billing")
        data["ship_address_id"] = contact.get_address(pref_type="shipping")
        if contact.currency_id:
            data["currency_id"] = contact.currency_id.id
        else:
            settings = get_model("settings").browse(1)
            data["currency_id"] = settings.currency_id.id
        return data

    def check_received_qtys(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids)[0]
        for line in obj.lines:
            check_percent=settings.purchase_check_received_qty
            if check_percent is not None:
                max_qty=line.qty*(100+check_percent)/Decimal(100)
                if line.qty_received > max_qty:
                    raise Exception("Can not receive excess quantity for purchase order %s and product %s (order qty: %s, received qty: %s)" % (
                        obj.number, line.product_id.code, line.qty_stock or line.qty, line.qty_received))

    def get_purchase_form_template(self, ids, context={}):
        obj = self.browse(ids)[0]
        if obj.state == "draft":
            return "rfq_form"
        else:
            return "purchase_form"

    def get_amount_total_words(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            amt=obj.amount_total or 0
            words=utils.num2words(int(amt)).upper()
            cents=int(amt*100)%100
            if cents:
                word_cents=utils.num2words(cents).upper()
                cents_name=obj.currency_id.cents_name or "CENTS"
                words+=" AND %s %s"%(word_cents,cents_name)
            vals[obj.id]=words
        return vals

    def onchange_sequence(self, context={}):
        data = context["data"]
        seq_id = data["sequence_id"]
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = self.search([["number", "=", num]])
            if not res:
                break
            get_model("sequence").increment_number(seq_id, context=context)
        data["number"] = num
        return data

    def delete(self, ids, **kw):
        for obj in self.browse(ids):
            if obj.state in ("confirmed", "done"):
                raise Exception("Can not delete purchase order in this status")
            for pick in obj.pickings:
                if pick.state!="voided":
                    raise Exception("There are still stock transactions linked to this order")
            for inv in obj.invoices:
                if inv.state!="voided":
                    raise Exception("There are still invoices linked to this order")
        super().delete(ids, **kw)

    def copy_to_rm_picking(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids[0])
        contact = obj.contact_id
        pick_vals = {
            "type": "out",
            "ref": "RM-OUT "+obj.number,
            "related_id": "purchase.order,%s" % obj.id,
            "contact_id": contact.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
        }
        if obj.delivery_date:
            pick_vals["date"]=obj.delivery_date
        if contact and contact.pick_out_journal_id:
            pick_vals["journal_id"] = contact.pick_out_journal_id.id
        for line in obj.lines:
            prod = line.product_id
            if prod.type not in ("stock", "consumable"):
                continue
            res=get_model("bom").search([["product_id","=",prod.id]])
            if res:
                bom_id=res[0]
                bom=get_model("bom").browse(bom_id)
                ratio=line.qty/bom.qty
                for comp in bom.lines:
                    prod=comp.product_id
                    #if prod.supply_method!="customer":
                    #    continue
                    prod_loc_id=bom.production_location_id.id
                    qty=comp.qty*ratio
                    line_vals = {
                        "product_id": prod.id,
                        "qty": qty,
                        "uom_id": comp.uom_id.id,
                        "location_from_id": comp.location_id.id,
                        "location_to_id": prod_loc_id,
                        "related_id": "purchase.order,%s" % obj.id,
                    }
                    pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            raise Exception("No raw materials found to issue")
        pick_id = get_model("stock.picking").create(pick_vals, {"pick_type": "out"})
        pick = get_model("stock.picking").browse(pick_id)
        return {
            "next": {
                "name": "pick_out",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Goods issue %s created from purchase order %s" % (pick.number, obj.number),
            "picking_id": pick_id,
        }

    def copy_to_fg_picking(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids[0])
        contact = obj.contact_id
        pick_vals = {
            "type": "in",
            "ref": "FG-IN "+obj.number,
            "related_id": "purchase.order,%s" % obj.id,
            "contact_id": contact.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
        }
        if obj.delivery_date:
            pick_vals["date"]=obj.delivery_date
        if contact and contact.pick_in_journal_id:
            pick_vals["journal_id"] = contact.pick_in_journal_id.id
        for line in obj.lines:
            prod = line.product_id
            if prod.type not in ("stock", "consumable"):
                continue
            res=get_model("bom").search([["product_id","=",prod.id]])
            if res:
                bom_id=res[0]
                bom=get_model("bom").browse(bom_id)
                ratio=line.qty/bom.qty
                line_vals = {
                    "product_id": prod.id,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "location_from_id": bom.production_location_id.id,
                    "location_to_id": line.location_id.id,
                    "related_id": "purchase.order,%s" % obj.id,
                }
                pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            raise Exception("No finished goods found to receive")
        pick_id = get_model("stock.picking").create(pick_vals, {"pick_type": "in"})
        pick = get_model("stock.picking").browse(pick_id)
        return {
            "next": {
                "name": "pick_in",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Goods receipt %s created from purchase order %s" % (pick.number, obj.number),
            "picking_id": pick_id,
        }

    def copy_to_supplier_sale(self,ids,context={}):
        obj=self.browse(ids[0])
        company_id=obj.company_id.id
        company=get_model("company").browse(company_id)
        contact_id=company.contact_id.id
        if not contact_id:
            raise Exception("Missing contact for company %s"%company.name)
        res=get_model("company").search([["contact_id","=",obj.contact_id.id]])
        if not res:
            raise Exception("Company not found for contact %s"%obj.contact_id.name)
        other_company_id=res[0]
        other_company=get_model("company").browse(other_company_id)
        sale_vals={
            "contact_id": contact_id,
            "ref": obj.ref,
            "related_id": "%s,%s"%(obj.related_id._model,obj.related_id.id) if obj.related_id else None,
            "due_date": obj.delivery_date,
            "lines": [],
        }
        access.set_active_company(other_company_id)
        for line in obj.lines: 
            prod=line.product_id
            loc_id=prod.locations[0].location_id.id if prod.locations else None
            line_vals={
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "amount": line.amount,
                "due_date": obj.delivery_date,
                "location_id": loc_id,
            }
            sale_vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(sale_vals)
        sale=get_model("sale.order").browse(sale_id)
        sale_num=sale.number
        if context.get("confirm_order"):
            sale.confirm()
        access.set_active_company(company_id)
        return {
            "flash": "Sales order %s created in company %s from purchase order %s" % (sale_num, other_company.name, obj.number),
            "sale_id": sale_id,
        }

    def copy_to_sale(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.customer_id:
            raise Exception("Missing customer")
        sale_vals={
            "contact_id": obj.customer_id.id,
            "ref": obj.number,
            "related_id": "purchase.order,%s"%obj.id,
            "lines": [],
        }
        for line in obj.lines: 
            prod=line.product_id
            loc_id=prod.locations[0].location_id.id if prod.locations else None
            line_vals={
                "product_id": line.product_id.id,
                "description": line.description,
                #"qty": line.qty,
                "qty": line.qty_received, # XXX
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "amount": line.amount,
                #"due_date": obj.delivery_date,
                "location_id": loc_id,
            }
            sale_vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(sale_vals)
        sale=get_model("sale.order").browse(sale_id)
        return {
            "flash": "Sales order %s created from purchase order %s" % (sale.number, obj.number),
            "sale_id": sale_id,
        }

    def merge_orders(self, ids, context={}):
        if len(ids)<2:
            raise Exception("Select at least 2 orders")
        first=None
        n=0
        refs=[]
        for obj in self.browse(ids):
            if obj.state!="draft":
                raise Exception("Can only merge draft orders")
            if first==None:
                first=obj
            else:
                if obj.contact_id.id!=first.contact_id.id:
                    raise Exception("Supplier has to be the same")
                if obj.date!=first.date:
                    raise Exception("Date has to be the same")
                if obj.currency_id.id!=first.currency_id.id:
                    raise Exception("Currency has to be the same")
            if obj.ref:
                refs.append(obj.ref)
        new_ref=", ".join(refs)
        new_id=first._copy({"number": first.number+" (merged)","ref": new_ref})[0]
        new_lines={}
        for obj in self.browse(ids):
            for line in obj.lines:
                k=(line.product_id.id,line.description,line.uom_id.id,line.location_id.id)
                if k in new_lines:
                    new_line_id=new_lines[k]
                    new_line=get_model("purchase.order.line").browse(new_line_id)
                    new_line.write({"qty":new_line.qty+line.qty})
                else:
                    new_line_id=line._copy({"order_id": new_id})[0]
                    new_lines[k]=new_line_id
            obj.void()
            n+=1
        return {
            "flash": "%d orders merged"%n,
        }

    def copy_to_grading(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            for line in obj.lines:
                if not line.product_id or not line.location_id:
                    continue
                vals={
                    "product_id": line.product_id.id,
                    "qty": line.qty_received or line.qty,
                    "location_id": line.location_id.id,
                    "related_id": "purchase.order,%s"%obj.id,
                }
                grade_id=get_model("stock.grade").create(vals)
                n+=1
        return {
            "alert": "%d gradings created"%n,
        }

    def submit_for_approval(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"state":"wait_approve"})
        obj.trigger("submit_approve")

    def approve(self,ids,context={}):
        if not access.check_permission_other("approve_purchase"):
            raise Exception("User does not have permission to approve purchase orders.")
        obj=self.browse(ids[0])
        user_id=access.get_active_user()
        wait_user_ids=[]
        for a in obj.approvals:
            if a.state!="pending":
                continue
            wait_user_ids.append(a.user_id.id)
        if wait_user_ids and user_id not in wait_user_ids:
            raise Exception("User is not allowed to approve")
        vals={
            "related_id": "purchase.order,%s"%obj.id,
            "user_id": user_id,
            "state": "approved",
            "date_approve": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        res=get_model("approval").search([["related_id","=",vals["related_id"]],["user_id","=",user_id],["state","=","approved"]])
        if res:
            raise Exception("Already approved by user")
        get_model("approval").create(vals)
        settings=get_model("settings").browse(1)
        min_approvals=settings.purchase_min_approvals or 1
        res=get_model("approval").search([["related_id","=",vals["related_id"]]])
        num_approvals=len(res)
        if num_approvals>=min_approvals:
            obj.confirm(context=context)
            obj.write({"date_approve":time.strftime("%Y-%m-%d %H:%M:%S")})

    def onchange_date(self, context={}):
        data = context["data"]
        ctx = {
            "date": data["date"],
        }
        if not data.get("id"):
            number = self._get_number(context=ctx)
            data["number"] = number
        return data

    def get_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d=datetime.strptime(obj.date,"%Y-%m-%d")
            month=d.strftime("%Y-%m")
            week=d.strftime("%Y-W%W")
            vals[obj.id]={
                "date_week": week,
                "date_month": month,
            }
        return vals

    def onchange_amount_input(self,context={}):
        data=context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        amount=line["amount_input"] or 0
        if line["qty"] and amount:
            line["unit_price"]=amount/line["qty"]
        elif not line["qty"] and line["unit_price"]:
            line["qty"]=amount/line["unit_price"]
        data=self.update_amounts(context=context)
        return data

    def test(self,ids,context={}):
        from random import randint
        get_model("purchase.order").exec_func_custom("test_custom",[ids,randint(1,100),randint(1,100)],{})

PurchaseOrder.register()
