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
from netforce.database import get_active_db
import time
import uuid
from netforce import access
from netforce.access import get_active_company, set_active_user, get_active_user
from netforce import utils
from decimal import *


class SaleQuot(Model):
    _name = "sale.quot"
    _string = "Quotation"
    _audit_log = True
    _name_field = "number"
    _key = ["number"]
    _multi_company = True
    _content_search=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Ref", search=True),
        "contact_id": fields.Many2One("contact", "Customer", required=True, search=True),
        "contact_person_id": fields.Many2One("contact", "Contact Person", condition=[["type", "=", "person"]], search=True),
        "date": fields.Date("Date", required=True, search=True),
        "exp_date": fields.Date("Valid Until"),
        "state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Awaiting Approval"), ("approved", "Approved"), ("won", "Won"), ("lost", "Lost"), ("revised", "Revised"), ("voided","Voided")], "Status", function="get_state", store=True),
        "lines": fields.One2Many("sale.quot.line", "quot_id", "Lines"),
        "amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True, store=True),
        "amount_tax": fields.Decimal("Tax Amount", function="get_amount", function_multi=True, store=True),
        "amount_total": fields.Decimal("Total", function="get_amount", function_multi=True, store=True),
        "amount_discount": fields.Decimal("Discount Amount", function="get_amount", function_multi=True),
        "amount_before_discount": fields.Decimal("Before Discount", function="get_amount", function_multi=True),
        "amount_after_discount2": fields.Decimal("After Discount", function="get_amount", function_multi=True), # XXX
        "amount_total_words": fields.Char("Total Words", function="get_amount_total_words"),
        "qty_total": fields.Decimal("Total", function="get_qty_total"),
        "currency_id": fields.Many2One("currency", "Currency", required=True),
        "opport_id": fields.Many2One("sale.opportunity", "Opportunity", search=True),
        "user_id": fields.Many2One("base.user", "Owner", search=True),
        "tax_type": fields.Selection([["tax_ex", "Tax Exclusive"], ["tax_in", "Tax Inclusive"], ["no_tax", "No Tax"]], "Tax Type", required=True),
        "sales": fields.One2Many("sale.order", "quot_id", "Sales Orders"),
        "payment_terms": fields.Text("Payment Terms"), # XXX: deprecated
        "pay_term_id": fields.Many2One("payment.term","Payment Terms"),
        "other_info": fields.Text("Other Information"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "activities": fields.One2Many("sale.activ", "related_id", "Activities"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "uuid": fields.Char("UUID"),
        "price_list_id": fields.Many2One("price.list", "Price List"),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "company_id": fields.Many2One("company", "Company"),
        "related_id": fields.Reference([["issue", "Issue"]], "Related To"),
        "ship_term_id": fields.Many2One("ship.term", "Shipping Terms"),
        "sequence_id": fields.Many2One("sequence", "Number Sequence"),
        "job_template_id": fields.Many2One("job.template", "Service Order Template"),
        "lost_sale_code_id": fields.Many2One("reason.code", "Lost Sale Reason Code", condition=[["type", "=", "lost_sale"]]),
        "agg_amount_total": fields.Decimal("Total Amount", agg_function=["sum", "amount_total"]),
        "agg_amount_subtotal": fields.Decimal("Total Amount w/o Tax", agg_function=["sum", "amount_subtotal"]),
        "year": fields.Char("Year", sql_function=["year", "date"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date"]),
        "month": fields.Char("Month", sql_function=["month", "date"]),
        "week": fields.Char("Week", sql_function=["week", "date"]),
        "est_costs": fields.One2Many("quot.cost","quot_id","Costs"), # XXX: deprecated
        "cost_amount": fields.Decimal("Cost Amount", function="get_profit", function_multi=True),
        "profit_amount": fields.Decimal("Profit Amount", function="get_profit", function_multi=True),
        "margin_percent": fields.Decimal("Margin %", function="get_profit", function_multi=True),
        "currency_rates": fields.One2Many("custom.currency.rate","related_id","Currency Rates"),
        "is_template": fields.Boolean("Use As Template"),
        "opport_email_id": fields.Many2One("email.message","Opportunity Email",function="get_opport_email"),
        "track_id": fields.Many2One("account.track.categ","Tracking Code"),
        "discount": fields.Decimal("Discount %"),
        "amount_after_discount": fields.Decimal("Amount After Discount"),
        "groups": fields.Json("Groups",function="get_groups"),
        "sale_categ_id": fields.Many2One("sale.categ","Sales Category",search=True),
        "tax_details": fields.Json("Tax Details",function="get_tax_details"),
        "extra_amount": fields.Decimal("Extra Amount"),
        "extra_discount": fields.Decimal("Extra Discount"),
        "extra_product_id": fields.Many2One("product","Extra Product"),
        "extra_discount_product_id": fields.Many2One("product","Extra Discount Product"),
        "project_id": fields.Many2One("project","Project",search=True),
        "bill_address_id": fields.Many2One("address", "Billing Address"),
        "ship_address_id": fields.Many2One("address", "Shipping Address"),
        "seller_id": fields.Many2One("seller","Seller"),
        "seller_contact_id": fields.Many2One("contact","Seller Contact"),
        "inquiry_date": fields.Date("Inquiry Date"),
    }

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="sale_quot")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if not num:
                return None
            user_id = get_active_user()
            set_active_user(1)
            res = self.search([["number", "=", num]])
            set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "number": _get_number,
        "currency_id": _get_currency,
        "tax_type": "tax_ex",
        "user_id": lambda self, context: get_active_user(),
        "uuid": lambda *a: str(uuid.uuid4()),
        "company_id": lambda *a: get_active_company(),
    }
    _constraints = ["check_fields"]
    _order = "date desc,number desc"

    def check_fields(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state in ("waiting_approval", "approved"):
                if not obj.lines:
                    raise Exception("No lines in quotation")

    def create(self, vals, **kw):
        id = super().create(vals, **kw)
        self.function_store([id])
        return id

    def write(self, ids, vals, **kw):
        opport_ids = []
        for obj in self.browse(ids):
            if obj.opport_id:
                opport_ids.append(obj.opport_id.id)
        super().write(ids, vals, **kw)
        if opport_ids:
            get_model("sale.opportunity").function_store(opport_ids)
        self.function_store(ids)

    def function_store(self, ids, field_names=None, context={}):
        super().function_store(ids, field_names, context)
        opport_ids = []
        for obj in self.browse(ids):
            if obj.opport_id:
                opport_ids.append(obj.opport_id.id)
        if opport_ids:
            get_model("sale.opportunity").function_store(opport_ids)

    def get_amount(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            vals = {}
            subtotal = 0
            tax = 0
            disc_total=0
            for line in obj.lines:
                if line.is_hidden:
                    continue
                if line.tax_id:
                    line_tax = get_model("account.tax.rate").compute_tax(
                        line.tax_id.id, line.amount, tax_type=obj.tax_type)
                else:
                    line_tax = 0
                tax += line_tax
                if obj.tax_type == "tax_in":
                    subtotal += (line.amount or 0) - line_tax
                else:
                    subtotal += line.amount or 0
                disc_total+=line.amount_discount or 0
            subtotal+=(obj.extra_amount or 0)-(obj.extra_discount or 0)
            tax+=(obj.extra_amount or 0)*Decimal("0.07") # XXX
            vals["amount_subtotal"] = subtotal
            vals["amount_tax"] = tax
            vals["amount_total"] = subtotal + tax
            vals["amount_discount"]=disc_total
            vals["amount_before_discount"]=subtotal+disc_total-(obj.extra_amount or 0)+(obj.extra_discount or 0) # XXX
            vals["amount_after_discount2"]=subtotal-(obj.extra_amount or 0) # XXX
            res[obj.id] = vals
        return res

    def get_qty_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.qty or 0 for line in obj.lines])
            res[obj.id] = qty or 0
        return res

    def submit_for_approval(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state != "draft":
                raise Exception("Invalid state")
            obj.write({"state": "waiting_approval"})
        self.trigger(ids, "submit_for_approval")

    def approve(self, ids, context={}):
        settings = get_model("settings").browse(1)
        if settings.approve_quot and not access.check_permission_other("approve_quotation"):
            raise Exception("User does not have permission to approve quotations (approve_quotation).")
        for obj in self.browse(ids):
            if obj.state not in ("draft", "waiting_approval"):
                raise Exception("Invalid state")
            obj.check_min_prices()
            obj.write({"state": "approved"})

    def check_min_prices(self,ids,context={}):
        for obj in self.browse(ids):
            for line in obj.lines:
                prod=line.product_id
                if not prod:
                    continue
                if prod.sale_min_price and line.unit_price<prod.sale_min_price:
                    raise Exception("Product %s is below the minimum sales price"%prod.name)

    def update_amounts(self, context={}):
        print("update_amounts")
        data = context["data"]
        data["amount_subtotal"] = 0
        data["amount_tax"] = 0
        tax_type = data["tax_type"]
        for line in data["lines"]:
            if not line:
                continue
            amt = (line.get("qty") or 0) * (line.get("unit_price") or 0)
            if line.get("discount"):
                disc = amt * line["discount"] / Decimal(100)
                amt -= disc
            else:
                disc = 0
            line["amount"] = amt
        hide_parents=[]
        for line in data["lines"]:
            if not line:
                continue
            if line.get("sequence") and line.get("hide_sub"):
                hide_parents.append(line["sequence"])
        is_hidden={}
        hide_totals={}
        for line in data["lines"]:
            if not line:
                continue
            if not line.get("sequence"):
                continue
            parent_seq=None
            for seq in hide_parents:
                if line["sequence"].startswith(seq+"."):
                    parent_seq=seq
                    break
            if parent_seq:
                is_hidden[line["sequence"]]=True
                hide_totals.setdefault(parent_seq,0)
                hide_totals[parent_seq]+=line["amount"]
        for line in data["lines"]:
            if not line:
                continue
            if line.get("sequence") and line.get("hide_sub"):
                line["amount"]=hide_totals.get(line["sequence"],0)
                if line["qty"]:
                    line["unit_price"]=line["amount"]/line["qty"]
        for line in data["lines"]:
            if is_hidden.get(line.get("sequence")):
                continue
            tax_id = line.get("tax_id")
            if tax_id:
                tax = get_model("account.tax.rate").compute_tax(tax_id, line["amount"], tax_type=tax_type)
                data["amount_tax"] += tax
            else:
                tax = 0
            if tax_type == "tax_in":
                data["amount_subtotal"] += line["amount"] - tax
            else:
                data["amount_subtotal"] += line["amount"]
        data["amount_total"] = data["amount_subtotal"] + data["amount_tax"]
        return data

    def update_amounts_line(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        amt = (line.get("qty") or 0) * (line.get("unit_price") or 0)
        if line.get("discount"):
            disc = amt * line["discount"] / Decimal(100)
            amt -= disc
        else:
            disc = 0
        line["amount"] = amt
        return data

    def onchange_product(self, context={}):
        data = context["data"]
        contact_id = data.get("contact_id")
        if contact_id:
            contact = get_model("contact").browse(contact_id)
        else:
            contact = None
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        line["description"] = prod.description or prod.name
        line["qty"] = 1
        if prod.uom_id is not None:
            line["uom_id"] = prod.uom_id.id
        pricelist_id = data["price_list_id"]
        price = None
        if pricelist_id:
            price = get_model("price.list").get_price(pricelist_id, prod.id, 1)
            price_list = get_model("price.list").browse(pricelist_id)
            price_currency_id = price_list.currency_id.id
        if price is None:
            price = prod.sale_price
            settings = get_model("settings").browse(1)
            price_currency_id = settings.currency_id.id
        if price is not None:
            currency_id = data["currency_id"]
            price_cur = get_model("currency").convert(price, price_currency_id, currency_id)
            line["unit_price"] = price_cur
        if prod.sale_tax_id is not None:
            line["tax_id"] = prod.sale_tax_id.id
        data = self.update_amounts(context)
        line["cost_price"]=prod.cost_price
        return data

    def onchange_qty(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        pricelist_id = data["price_list_id"]
        qty = line["qty"]
        if line.get("unit_price") is None:
            price = None
            if pricelist_id:
                price = get_model("price.list").get_price(pricelist_id, prod.id, qty)
                price_list = get_model("price.list").browse(pricelist_id)
                price_currency_id = price_list.currency_id.id
            if price is None:
                price = prod.sale_price
                settings = get_model("settings").browse(1)
                price_currency_id = settings.currency_id.id
            if price is not None:
                currency_id = data["currency_id"]
                price_cur = get_model("currency").convert(price, price_currency_id, currency_id)
                line["unit_price"] = price_cur
        data = self.update_amounts(context)
        return data

    def onchange_contact(self, context={}):
        data = context["data"]
        contact_id = data.get("contact_id")
        if not contact_id:
            return {}
        contact = get_model("contact").browse(contact_id)
        data["pay_term_id"] = contact.sale_pay_term_id.id
        data["price_list_id"] = contact.sale_price_list_id.id
        if contact.currency_id:
            data["currency_id"] = contact.currency_id.id
        else:
            settings = get_model("settings").browse(1)
            data["currency_id"] = settings.currency_id.id
        data["seller_contact_id"]=contact.seller_contact_id.id
        data["contact_person_id"]=contact.contact_person_id.id
        return data

    def onchange_uom(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        uom_id = line.get("uom_id")
        if not uom_id:
            return {}
        uom = get_model("uom").browse(uom_id)
        if prod.sale_price is not None:
            line["unit_price"] = prod.sale_price * uom.ratio / prod.uom_id.ratio
        data = self.update_amounts(context)
        return data

    def copy(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "contact_id": obj.contact_id.id,
            "contact_person_id":obj.contact_person_id.id,
            "currency_id": obj.currency_id.id,
            "tax_type": obj.tax_type,
            "payment_terms": obj.payment_terms,
            "other_info": obj.other_info,
            "exp_date": obj.exp_date,
            "opport_id": obj.opport_id.id,
            "lines": [],
        }
        if "revise" in context and context["revise"]:
            vals.update({
                "contact_person_id":obj.contact_person_id.id if obj.contact_person_id else None,
                "ref": obj.ref,
                "sale_categ_id": obj.sale_categ_id.id if obj.sale_categ_id else None,
                "project_id": obj.project_id.id if obj.project_id else None,
                "pay_term_id": obj.pay_term_id.id if obj.pay_term_id else None,
            })
        for line in obj.lines:
            line_vals = {
                "sequence": line.sequence,
                "type": line.type,
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "discount": line.discount,
                "tax_id": line.tax_id.id,
                "cost_price": line.cost_price,
            }
            vals["lines"].append(("create", line_vals))
        new_id = self.create(vals, context=context)
        new_obj = self.browse(new_id)
        return {
            "new_id": new_id,
            "next": {
                "name": "quot",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Quotation %s copied from %s" % (new_obj.number, obj.number),
        }

    def revise(self, ids, context={}):
        obj = self.browse(ids)[0]
        context["revise"] = True
        res = self.copy(ids, context)
        obj.write({"state": "revised"})
        return res

    def copy_to_sale_order(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.sales:
            raise Exception("Sales order already created for quotation %s"%obj.number)
        settings=get_model("settings").browse(1)
        prod_types={}
        for line in obj.lines:
            prod=line.product_id
            if prod and settings.sale_split_service:
                #prod_type="service" if prod.type=="service" else "non_service"
                prod_type=prod.type
            else:
                prod_type=None
            prod_types.setdefault(prod_type,[]).append(line)
        n=0
        sale_id=None
        for prod_type,lines in prod_types.items():
            sale_vals={
                "ref": obj.number,
                "quot_id": obj.id,
                "related_id": "sale.quot,%s"%obj.id,
                "contact_id": obj.contact_id.id,
                "bill_address_id": obj.contact_id.addresses[0].id if obj.contact_id.addresses else None,
                "currency_id": obj.currency_id.id,
                "tax_type": obj.tax_type,
                "lines": [],
                "user_id": obj.user_id.id,
                "other_info": obj.other_info,
                "pay_term_id": obj.pay_term_id.id,
                "price_list_id": obj.price_list_id.id,
                "job_template_id": obj.job_template_id.id,
                "seller_id": obj.seller_id.id,
                "currency_rates": [],
            }
            for line in lines:
                prod=line.product_id
                line_vals={
                    "sequence": line.sequence,
                    "type": line.type,
                    "product_id": prod.id,
                    "description": line.description,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "unit_price": line.unit_price,
                    "cost_price": line.cost_price,
                    "discount": line.discount,
                    "tax_id": line.tax_id.id,
                    "location_id": prod.locations[0].location_id.id if prod and prod.locations else None,
                    "cost_price": line.cost_price,
                    "notes": line.notes,
                }
                sale_vals["lines"].append(("create",line_vals))
            if obj.extra_amount:
                prod=obj.extra_product_id
                line_vals={
                    "product_id": prod.id,
                    "description": prod.description or "Extra Amount",
                    "qty": 1,
                    "uom_id": prod.uom_id.id if prod else None,
                    "unit_price": obj.extra_amount,
                    "tax_id": prod.sale_tax_id.id if prod else None,
                    "location_id": prod.locations[0].location_id.id if prod and prod.locations else None,
                }
                sale_vals["lines"].append(("create",line_vals))
            if obj.extra_discount:
                prod=obj.extra_discount_product_id
                line_vals={
                    "product_id": prod.id,
                    "description": prod.description or "Extra Discount",
                    "qty": 1,
                    "uom_id": prod.uom_id.id if prod else None,
                    "unit_price": -obj.extra_discount,
                    "tax_id": prod.sale_tax_id.id if prod else None,
                    "location_id": prod.locations[0].location_id.id if prod and prod.locations else None,
                }
                sale_vals["lines"].append(("create",line_vals))
            for r in obj.currency_rates:
                rate_vals={
                    "currency_id": r.currency_id.id,
                    "rate": r.rate,
                }
                sale_vals["currency_rates"].append(("create",rate_vals))
            sale_id=get_model("sale.order").create(sale_vals,context=context)
            n+=1
        if not sale_id:
            raise Exception("Quotation is empty")
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": sale_id,
            },
            "flash": "%s sales orders created"%n,
        }

    def do_won(self, ids, context={}):
        for obj in self.browse(ids):
            assert obj.state == "approved"
            obj.write({"state": "won"})

    def do_lost(self, ids, context={}):
        for obj in self.browse(ids):
            assert obj.state == "approved"
            obj.write({"state": "lost"})

    def do_reopen(self, ids, context={}):
        for obj in self.browse(ids):
            assert obj.state in ("won", "lost")
            obj.write({"state": "approved"})

    def get_state(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            state = obj.state
            if state == "approved":
                found = False
                for sale in obj.sales:
                    if sale.state in ("confirmed", "done"):
                        found = True
                        break
                if found:
                    state = "won"
            vals[obj.id] = state
        return vals

    def view_link(self, ids, context={}):
        obj = self.browse(ids)[0]
        uuid = obj.uuid
        dbname = get_active_db()
        return {
            "next": {
                "type": "url",
                "url": "/view_quot?dbname=%s&uuid=%s" % (dbname, uuid),
            }
        }

    def get_template_quot_form(self, ids, context={}):
        obj = self.browse(ids)[0]
        has_discount=False
        for line in obj.lines:
            if line.discount:
                has_discount=True
        if has_discount:
            return "quot_form_disc"
        else:
            return "quot_form"

    def to_draft(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "draft"})

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "voided"})

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

    def onchange_cost_product(self,context):
        data=context["data"]
        path=context["path"]
        line=get_data_path(data,path,parent=True)
        prod_id=line.get("product_id")
        if prod_id:
            prod=get_model("product").browse(prod_id)
            line["description"]=prod.name
            line["list_price"]=prod.purchase_price
            line["purchase_price"]=prod.purchase_price
            line["landed_cost"]=prod.landed_cost
            line["qty"]=1
            line["uom_id"]=prod.uom_id.id
            line["currency_id"]=prod.purchase_currency_id.id
            line["purchase_duty_percent"]=prod.purchase_duty_percent
            line["purchase_ship_percent"]=prod.purchase_ship_percent
            line["landed_cost"]=prod.landed_cost
            line["purcase_price"]=prod.purchase_price

            if prod.suppliers:
                line["supplier_id"]=prod.suppliers[0].supplier_id.id
        return data

    def get_profit(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_cost=0
            for line in obj.lines:
                total_cost+=line.cost_amount or 0
            profit = (obj.amount_subtotal or 0) - total_cost
            margin=profit*100/obj.amount_subtotal if obj.amount_subtotal else None
            vals[obj.id] = {
                "cost_amount": total_cost,
                "profit_amount": profit,
                "margin_percent": margin,
            }
        return vals

    def create_est_costs(self,ids,context={}):
        obj=self.browse(ids[0])
        del_ids=[]
        for cost in obj.est_costs:
            if cost.product_id:
                del_ids.append(cost.id)
        get_model("quot.cost").delete(del_ids)
        #obj.write({"est_costs":[("delete_all",)]})
        for line in obj.lines:
            prod=line.product_id
            if not prod:
                continue
            if not prod.purchase_price:
                continue
            if not line.sequence:
                continue
            if "bundle" == prod.type:
                continue
            vals={
                "quot_id": obj.id,
                "sequence": line.sequence if not line.is_hidden else line.parent_sequence,
                "product_id": prod.id,
                "description": prod.name,
                "supplier_id": prod.suppliers[0].supplier_id.id if prod.suppliers else None,
                "list_price": prod.purchase_price,
                "purchase_price": prod.purchase_price,
                "landed_cost": prod.landed_cost,
                "purchase_duty_percent": prod.purchase_duty_percent,
                "purchase_ship_percent": prod.purchase_ship_percent,
                "qty": line.qty,
                "currency_id": prod.purchase_currency_id.id,
            }
            get_model("quot.cost").create(vals)

    def merge_quotations(self,ids,context={}):
        if len(ids)<2:
            raise Exception("Can not merge less than two quotations")
        contact_ids=[]
        currency_ids=[]
        tax_types=[]
        for obj in self.browse(ids):
            contact_ids.append(obj.contact_id.id)
            currency_ids.append(obj.currency_id.id)
            tax_types.append(obj.tax_type)
        contact_ids=list(set(contact_ids))
        currency_ids=list(set(currency_ids))
        tax_types=list(set(tax_types))
        if len(contact_ids)>1:
            raise Exception("Quotation customers have to be the same")
        if len(currency_ids)>1:
            raise Exception("Quotation currencies have to be the same")
        if len(tax_types)>1:
            raise Exception("Quotation tax types have to be the same")
        vals = {
            "contact_id": contact_ids[0],
            "currency_id": currency_ids[0],
            "tax_type": tax_types[0],
            "lines": [],
            "est_costs": [],
        }
        seq=0
        for obj in self.browse(ids):
            seq_map={}
            for line in obj.lines:
                seq+=1
                seq_map[line.sequence]=seq
                line_vals = {
                    "sequence": seq,
                    "product_id": line.product_id.id,
                    "description": line.description,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "unit_price": line.unit_price,
                    "discount": line.discount,
                    "tax_id": line.tax_id.id,
                }
                vals["lines"].append(("create", line_vals))
            for cost in obj.est_costs:
                cost_vals={
                    "sequence": seq_map.get(cost.sequence),
                    "product_id": cost.product_id.id,
                    "description": cost.description,
                    "supplier_id": cost.supplier_id.id,
                    "list_price": cost.list_price,
                    "purchase_price": cost.purchase_price,
                    "landed_cost": cost.landed_cost,
                    "qty": cost.qty,
                    "currency_id": cost.currency_id.id,
                }
                vals["est_costs"].append(("create",cost_vals))
        new_id = self.create(vals, context=context)
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "quot",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Quotations merged",
        }

    def get_relative_currency_rate(self,ids,currency_id):
        obj=self.browse(ids[0])
        rate=None
        for r in obj.currency_rates:
            if r.currency_id.id==currency_id:
                rate=r.rate
                break
        if rate is None:
            rate_from=get_model("currency").get_rate([currency_id],obj.date) or Decimal(1)
            rate_to=obj.currency_id.get_rate(obj.date) or Decimal(1)
            rate=rate_from/rate_to
        return rate

    def get_opport_email(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            email_id=None
            if obj.opport_id and obj.opport_id.emails:
                email_id=obj.opport_id.emails[-1].id
            vals[obj.id]=email_id
        return vals

    def apply_discount(self,ids,context={}):
        obj=self.browse(ids[0])
        for line in obj.lines:
            if line.unit_price:
                disc=obj.discount
            else:
                disc=None
            line.write({"discount":disc})
        #obj.write({"discount":None})
        return {
            "alert": "Discount applied successfully",
        }

    def calc_discount(self,ids,context={}):
        obj=self.browse(ids[0])
        amt=obj.amount_after_discount
        if amt is None:
            return
        obj.write({"discount":0,"extra_discount":0})
        obj.function_store()
        obj=obj.browse()[0]
        obj.apply_discount()
        obj.function_store() # XXX
        obj=obj.browse()[0]
        old_amt=obj.amount_subtotal
        disc_amt=old_amt-amt
        disc=round(disc_amt*100/(old_amt-(obj.extra_amount or 0))-Decimal("0.005"),2)
        obj.write({"discount":disc})
        obj.apply_discount()
        obj.function_store()
        obj=obj.browse()[0]
        extra_disc=obj.amount_subtotal-amt
        obj.write({"extra_discount":extra_disc})
        obj.function_store()
        return {
            "alert": "Old amount: %s, new amount: %s, discount amount: %s => discount percent: %s, extra discount: %s"%(old_amt,amt,disc_amt,disc,extra_disc),
        }

    def get_groups(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            groups=[]
            group_vals=None
            for line in obj.lines:
                if line.type=="group":
                    group_vals={
                        "sequence": line.sequence,
                        "description": line.description,
                        "lines": [],
                        "amount_total": 0,
                    }
                    groups.append(group_vals)
                else:
                    line_vals={
                        "sequence": line.sequence,
                        "description": line.description,
                        "qty": line.qty,
                        "unit_price": line.unit_price,
                        "amount": line.amount,
                    }
                    if line.uom_id:
                        line_vals["uom_id"]={
                            "name": line.uom_id.name,
                        }
                    if group_vals:
                        group_vals["lines"].append(line_vals)
                        group_vals["amount_total"]+=line_vals["amount"] or 0
            vals[obj.id]=groups
        return vals

    def get_tax_details(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            taxes={}
            for line in obj.lines:
                if not line.amount:
                    continue
                tax_id=line.tax_id.id
                if tax_id and obj.tax_type != "no_tax":
                    base_amt = get_model("account.tax.rate").compute_base(tax_id, line.amount, tax_type=obj.tax_type)
                    tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                    for comp_id, tax_amt in tax_comps.items():
                        tax_vals = taxes.setdefault(comp_id, {"tax_amt": 0, "base_amt": 0})
                        tax_vals["tax_amt"] += tax_amt
                        tax_vals["base_amt"] += base_amt
            vals[obj.id]=taxes
        return vals

SaleQuot.register()
