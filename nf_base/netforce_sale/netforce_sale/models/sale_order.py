from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
from netforce.access import get_active_user, set_active_user
from netforce.access import get_active_company, check_permission_other, set_active_company
from netforce import access
from netforce import database
from netforce import utils
from datetime import datetime, timedelta
from decimal import Decimal
import time
import random


class SaleOrder(Model):
    _name = "sale.order"
    _string = "Sales Order"
    _audit_log = True
    _name_field = "number"
    _multi_company = True
    _key = ["company_id", "number"]
    _content_search=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Ref", search=True),
        "contact_id": fields.Many2One("contact", "Customer", required=True, search=True, condition=[["customer","=",True]]),
        "contact_person_id": fields.Many2One("contact", "Contact Person", condition=[["type", "=", "person"]], search=True),
        "date": fields.Date("Order Date", required=True, search=True),
        "state": fields.Selection([("draft", "Draft"), ("reserved","Reserved"), ("confirmed", "Confirmed"), ("done", "Completed"), ("voided", "Voided")], "Status", required=True),
        "lines": fields.One2Many("sale.order.line", "order_id", "Lines"),
        "amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True, store=True),
        "amount_tax": fields.Decimal("Tax Amount", function="get_amount", function_multi=True, store=True),
        "amount_total": fields.Decimal("Total Amount", function="get_amount", function_multi=True, store=True),
        "amount_total_discount": fields.Decimal("Total Discount", function="get_amount", function_multi=True, store=True),
        "amount_subtotal_before_discount": fields.Decimal("Subtotal Before Discount", function="get_amount", function_multi=True, store=True),
        "amount_total_words": fields.Char("Total Words", function="get_amount_total_words"),
        "amount_total_cur": fields.Decimal("Total", function="get_amount", function_multi=True, store=True),
        "qty_total": fields.Decimal("Total", function="get_qty_total"),
        "currency_id": fields.Many2One("currency", "Currency", required=True),
        "quot_id": fields.Many2One("sale.quot", "Quotation", search=True), # XXX: deprecated
        "user_id": fields.Many2One("base.user", "Owner", search=True),
        "tax_type": fields.Selection([["tax_ex", "Tax Exclusive"], ["tax_in", "Tax Inclusive"], ["no_tax", "No Tax"]], "Tax Type", required=True),
        "invoice_lines": fields.One2Many("account.invoice.line", "related_id", "Invoice Lines"),
        "invoices_direct": fields.One2Many("account.invoice", "related_id", "Invoices"),
        "invoices": fields.Many2Many("account.invoice", "Invoices", function="get_invoices"),
        "pickings": fields.Many2Many("stock.picking", "Stock Pickings", function="get_pickings"),
        "is_delivered": fields.Boolean("Shipped", function="get_delivered"),
        "is_paid": fields.Boolean("Paid", function="get_paid"),
        "is_invoiced": fields.Boolean("Invoiced", function="get_invoiced"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "activities": fields.One2Many("sale.activ", "related_id", "Activities"),
        "location_id": fields.Many2One("stock.location", "Warehouse", search=True),  # XXX: deprecated
        "price_list_id": fields.Many2One("price.list", "Price List", condition=[["type", "=", "sale"]]),
        "payment_terms": fields.Text("Payment Terms"), # XXX: deprecated
        "pay_term_id": fields.Many2One("payment.term","Payment Terms"),
        "delivery_date": fields.Date("Due Date"),
        "due_date": fields.Date("Shipping Date (ETD)"),
        "ship_time": fields.Char("Shipping Time"),
        "delivery_date": fields.Date("Delivery Date (ETA)"),
        "team_id": fields.Many2One("mfg.team", "Production Team"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "addresses": fields.One2Many("address", "related_id", "Addresses"),
        "bill_address_id": fields.Many2One("address", "Billing Address"),
        "ship_address_id": fields.Many2One("address", "Shipping Address"),
        "coupon_id": fields.Many2One("sale.coupon", "Coupon"),
        "purchase_lines": fields.One2Many("purchase.order.line", "sale_id", "Purchase Orders"),
        "purchase_orders": fields.One2Many("purchase.order", "related_id", "Purchase Orders"),
        "sale_orders": fields.One2Many("sale.order", "related_id", "Sales Orders"),
        "production_orders": fields.One2Many("production.order", "sale_id", "Production Orders"),
        "other_info": fields.Text("Remarks"),
        "costs": fields.One2Many("sale.cost", "sale_id", "Costs"),
        "est_cost_total": fields.Decimal("Estimated Cost Total", function="get_profit_old", function_multi=True, store=True),
        "est_profit": fields.Decimal("Estimated Profit", function="get_profit_old", function_multi=True, store=True),
        "est_profit_percent": fields.Decimal("Estimated Profit Percent", function="get_profit_old", function_multi=True, store=True),
        "act_cost_total": fields.Decimal("Actual Cost Total", function="get_profit_old", function_multi=True, store=True),
        "act_profit": fields.Decimal("Actual Profit", function="get_profit_old", function_multi=True, store=True),
        "act_profit_percent": fields.Decimal("Actual Profit Percent", function="get_profit_old", function_multi=True, store=True),
        "company_id": fields.Many2One("company", "Company"),
        "production_status": fields.Json("Production", function="get_production_status"),
        "overdue": fields.Boolean("Overdue", function="get_overdue", function_search="search_overdue"),
        "ship_term_id": fields.Many2One("ship.term", "Shipping Terms"),
        "ship_port_id": fields.Many2One("ship.port", "Shipping Port"),
        "approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "sequence_id": fields.Many2One("sequence", "Number Sequence"),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "state_label": fields.Char("Status Label", function="get_state_label"),  # XXX: not needed
        "ship_tracking": fields.Char("Tracking Numbers", function="get_ship_tracking"),
        "job_template_id": fields.Many2One("job.template", "Service Order Template"),
        "jobs": fields.One2Many("job", "related_id", "Service Orders"),
        "agg_amount_total": fields.Decimal("Total Amount", agg_function=["sum", "amount_total"]),
        "agg_amount_total_cur": fields.Decimal("Total Amount (Converted)", agg_function=["sum", "amount_total_cur"]),
        "agg_amount_subtotal": fields.Decimal("Total Amount w/o Tax", agg_function=["sum", "amount_subtotal"]),
        "agg_est_profit": fields.Decimal("Total Estimated Profit", agg_function=["sum", "est_profit"]),
        "agg_act_profit": fields.Decimal("Total Actual Profit", agg_function=["sum", "act_profit"]),
        "year": fields.Char("Year", sql_function=["year", "date"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date"]),
        "month": fields.Char("Month", sql_function=["month", "date"]),
        "week": fields.Char("Week", sql_function=["week", "date"]),
        "pay_method_id": fields.Many2One("payment.method", "Payment Method",search=True),
        "sale_channel_id": fields.Many2One("sale.channel", "Sales Channel",search=True),
        "related_id": fields.Reference([["sale.quot", "Quotation"], ["ecom.cart", "Ecommerce Cart"], ["purchase.order", "Purchase Order"], ["sale.order","Sales Order"]], "Related To"),
        "est_costs": fields.One2Many("sale.cost","sale_id","Costs"),
        "est_cost_amount": fields.Float("Est. Cost Amount", function="get_est_profit", function_multi=True),
        "est_profit_amount": fields.Float("Est. Profit Amount", function="get_est_profit", function_multi=True),
        "est_margin_percent": fields.Float("Est. Margin %", function="get_est_profit", function_multi=True),
        "act_cost_amount": fields.Float("Act. Cost Amount", function="get_act_profit", function_multi=True),
        "act_profit_amount": fields.Float("Act. Profit Amount", function="get_act_profit", function_multi=True),
        "act_margin_percent": fields.Float("Act. Margin %", function="get_act_profit", function_multi=True),
        "act_mfg_cost": fields.Decimal("Actual Production Cost", function="get_act_mfg_cost"),
        "track_id": fields.Many2One("account.track.categ","Tracking Code"),
        "track_entries": fields.One2Many("account.track.entry",None,"Tracking Entries",function="get_track_entries",function_write="write_track_entries"),
        "track_balance": fields.Decimal("Tracking Balance",function="_get_related",function_context={"path":"track_id.balance"}),
        "used_promotions": fields.One2Many("sale.order.promotion", "sale_id", "Used Promotions"),
        "seller_id": fields.Many2One("seller","Seller"),
        "seller_contact_id": fields.Many2One("contact","Seller Contact"),
        "product_id": fields.Many2One("product","Product",store=False,function_search="search_product",search=True),
        "product_categ_id": fields.Many2One("product.categ","Product Category",store=False,function_search="search_product_categ",search=True),
        "currency_rates": fields.One2Many("custom.currency.rate","related_id","Currency Rates"),
        "delivery_slot_id": fields.Many2One("delivery.slot","Delivery Slot"),
        "transaction_no": fields.Char("Payment Transaction No.",search=True),
        "voucher_id": fields.Many2One("sale.voucher","Voucher"),
        "cost_amount": fields.Decimal("Cost Amount", function="get_profit", function_multi=True),
        "profit_amount": fields.Decimal("Profit Amount", function="get_profit", function_multi=True),
        "margin_percent": fields.Decimal("Margin %", function="get_profit", function_multi=True),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
        "sale_categ_id": fields.Many2One("sale.categ","Sales Category",search=True),
        "project_id": fields.Many2One("project","Project"),
        "is_voucher_applied": fields.Boolean("Is Voucher Applied",function="get_is_voucher_applied"),
        "transforms": fields.One2Many("stock.transform", "sale_id", "Transforms"),
        "raw_mats": fields.Json("Raw Materials",function="get_raw_mats"),
        "due_date_weekday": fields.Char("Shipping Date (ETD) - Weekday",function="get_due_date_agg"),
        "receipt_printed": fields.Boolean("Receipt Printed"), 
        "report_no": fields.Char("Report No."),
        "orig_sale_id": fields.Many2One("sale.order","Original Sales Order"),
        "incl_report": fields.Boolean("Included In Report",store=False,function_search="search_incl_report",search=True),
        "quote_id": fields.Many2One("sale.quot","Quotation"),
        "gross_weight": fields.Decimal("Gross Weight"),
        "net_weight": fields.Decimal("Net Weight"),
        "customer_date": fields.Date("Customer Date"),
        "agent_id": fields.Many2One("contact", "Notify To", search=True, condition=[["agent","=",True]]), #Chin
        "agent_person_id": fields.Many2One("contact", "Notify To Person", condition=[["type", "=", "person"]], search=True), #Chin
        "agent_address_id": fields.Many2One("address", "Notify To Address"), #Chin
        "freight_charges": fields.Decimal("Freight Charges"),
    }

    def _get_number(self, context={}):
        seq_id=context.get("sequence_id")
        if not seq_id:
            seq_id = get_model("sequence").find_sequence(type="sale_order",context=context)
        if not seq_id:
            raise Exception("Missing number sequence for sales orders")
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
        "user_id": lambda *a: get_active_user(),
        "company_id": lambda *a: get_active_company(),
    }
    _order = "date desc,number desc"

    def search_product(self, clause, context={}):
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        order_ids = []
        for line in get_model("sale.order.line").search_browse([["product_id","in",product_ids]]):
            order_ids.append(line.order_id.id)
        cond = [["id","in",order_ids]]
        return cond

    def search_product_categ(self, clause, context={}):
        categ_id = clause[2]
        order_ids=[]
        for line in get_model("sale.order.line").search_browse([["product_id.categ_id","child_of",categ_id]]):
            order_ids.append(line.order_id.id)
        cond = [["id","in",order_ids]]
        return cond

    def create(self, vals, context={}):
        #import pdb; pdb.set_trace()
        id = super(SaleOrder, self).create(vals, context)
        self.function_store([id])
        quot_id = vals.get("quot_id")
        if quot_id:
            get_model("sale.quot").function_store([quot_id])
        return id

    def write(self, ids, vals, **kw):
        quot_ids = []
        for obj in self.browse(ids):
            if obj.quot_id:
                quot_ids.append(obj.quot_id.id)
        super(SaleOrder, self).write(ids, vals, **kw)
        self.function_store(ids)
        quot_id = vals.get("quot_id")
        if quot_id:
            quot_ids.append(quot_id)
        if quot_ids:
            get_model("sale.quot").function_store(quot_ids)

    def delete(self, ids, **kw):
        quot_ids = []
        for obj in self.browse(ids):
            if obj.state in ("confirmed", "done"):
                raise Exception("Can not delete sales order in this status")
            if obj.quot_id:
                quot_ids.append(obj.quot_id.id)
        super(SaleOrder, self).delete(ids, **kw)
        if quot_ids:
            get_model("sale.quot").function_store(quot_ids)

    def get_amount(self, ids, context={}):
        res = {}
        settings = get_model("settings").browse(1)
        for obj in self.browse(ids):
            vals = {}
            subtotal = 0
            tax = 0
            discount = 0
            for line in obj.lines:
                discount += line.amount_discount or 0
                if line.tax_id:
                    line_tax = get_model("account.tax.rate").compute_tax(
                        line.tax_id.id, line.amount or 0, tax_type=obj.tax_type)
                else:
                    line_tax = 0
                tax += line_tax
                if obj.tax_type == "tax_in":
                    subtotal += (line.amount or 0)- line_tax
                else:
                    subtotal += (line.amount or 0)
            for line in obj.used_promotions:
                if line.product_id or line.percent:
                    continue
                prom=line.promotion_id
                prod=prom.product_id
                prom_tax=prod.sale_tax_id if prod else None
                if prom_tax:
                    line_tax = get_model("account.tax.rate").compute_tax(
                        prom_tax.id, line.amount, tax_type=obj.tax_type)
                else:
                    line_tax = 0
                tax -= line_tax
                if obj.tax_type == "tax_in":
                    subtotal -= line.amount - line_tax
                else:
                    subtotal -= line.amount
            vals["amount_subtotal"] = subtotal
            vals["amount_tax"] = tax
            #vals["amount_total"] = subtotal + tax
            vals["amount_total"] = subtotal + tax + (obj.freight_charges or 0) #Chin
            vals["amount_total_cur"] = get_model("currency").convert(
                vals["amount_total"], obj.currency_id.id, settings.currency_id.id)
            vals["amount_total_discount"] = discount
            vals["amount_subtotal_before_discount"] = subtotal+discount
            res[obj.id] = vals
        return res

    def get_qty_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.qty for line in obj.lines])
            res[obj.id] = qty or 0
        return res

    def confirm(self, ids, context={}):
        settings = get_model("settings").browse(1)
        if settings.approve_sale and not access.check_permission_other("approve_sale"):
            raise Exception("User does not have permission to approve sales orders (approve_sale).")
        obj = self.browse(ids)[0]
        if obj.state not in ("draft","reserved"):
            raise Exception("Invalid state")
        obj.check_min_prices()
        #for line in obj.lines:
        #    prod = line.product_id
        #    if prod and prod.type in ("stock", "consumable", "bundle") and not line.location_id:
        #        raise Exception("Missing location for product %s" % prod.code)
        obj.write({"state": "confirmed"})
        if settings.sale_copy_picking:
            res=obj.copy_to_picking()
            picking_ids=res.get("picking_ids")
            if picking_ids:
                get_model("stock.picking").pending(picking_ids)
        if settings.sale_copy_invoice:
            obj.copy_to_invoice()
        if settings.sale_copy_production:
            obj.copy_to_production()
        obj.trigger("confirm")
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": obj.id,
            },
            "flash": "Sales order %s confirmed" % obj.number,
        }

    def check_min_prices(self,ids,context={}):
        for obj in self.browse(ids):
            for line in obj.lines:
                prod=line.product_id
                if not prod:
                    continue
                if prod.sale_min_price and line.unit_price<prod.sale_min_price:
                    raise Exception("Product %s is below the minimum sales price"%prod.name)

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

    def update_amounts(self, context):
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
            if line.get("discount_amount"):
                amt -= line["discount_amount"]
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
        line["description"] = prod.description or prod.name or "/"
        line["qty"] = 1
        line["uom_id"] = prod.sale_uom_id.id or prod.uom_id.id
        line["discount"]=contact.sale_discount
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
            price_cur = round(price_cur,2)
            line["unit_price"] = price_cur
        if prod.categ_id and prod.categ_id.sale_tax_id:
            line["tax_id"] = prod.categ_id.sale_tax_id.id
        if prod.sale_tax_id:
            line["tax_id"] = prod.sale_tax_id.id
        if contact and contact.sale_tax_id:
            line["tax_id"]=contact.sale_tax_id.id
        if prod.locations:
            line["location_id"] = prod.locations[0].location_id.id
            line["reserve_location_id"] = prod.locations[0].reserve_location_id.id
        line["cost_price"]=prod.cost_price
        data = self.update_amounts(context)
        return data

    def onchange_qty(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        pricelist_id = data["price_list_id"]
        qty = line["qty"]
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

    def update_price(self):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        pricelist_id = data["price_list_id"]
        qty = line["qty"]
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

    def onchange_uom(self, context):
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

    def get_qty_to_deliver(self, ids):
        obj = self.browse(ids)[0]
        sale_quants = {}
        for line in obj.lines:
            prod = line.product_id
            if not prod or prod.type == "service":
                continue
            uom = line.uom_id
            sale_quants.setdefault((prod.id, uom.id), 0)
            sale_quants[(prod.id, uom.id)] += line.qty  # XXX: uom
        done_quants = {}
        for move in obj.stock_moves:
            if move.state == "cancelled":
                continue
            prod = move.product_id
            done_quants.setdefault(prod.id, 0)
            done_quants[prod.id] += move.qty  # XXX: uom
        to_deliver = {}
        for (prod_id, uom_id), qty in sale_quants.items():
            qty_done = done_quants.get(prod_id, 0)
            if qty_done < qty:
                to_deliver[(prod_id, uom_id)] = qty - qty_done
        return to_deliver

    def copy_to_picking(self, ids, context={}):
        id = ids[0]
        obj = self.browse(id)
        contact = obj.contact_id
        res = get_model("stock.location").search([["type", "=", "customer"]])
        if not res:
            raise Exception("Customer location not found")
        cust_loc_id = res[0]
        res = get_model("stock.location").search([["type", "=", "internal"]])
        if not res:
            raise Exception("Warehouse not found")
        wh_loc_id = res[0]
        pick_vals = {}
        for line in obj.lines:
            prod = line.product_id
            if not prod:
                continue
            if prod.type not in ("stock", "consumable", "bundle"):
                continue
            if line.qty <= 0:
                continue
            qty_remain = (line.qty_stock or line.qty) - line.qty_delivered
            if qty_remain <= 0:
                continue
            ship_address_id = line.ship_address_id.id or obj.ship_address_id.id
            ship_method_id = line.ship_method_id.id or obj.ship_method_id.id
            due_date = line.due_date or obj.due_date or time.strftime("%Y-%m-%d")
            if not due_date:
                raise Exception("Missing shipping date for sales order %s"%obj.number)
            pick_key = (ship_address_id,ship_method_id,due_date)
            if pick_key not in pick_vals:
                pick_vals[pick_key] = {
                    "type": "out",
                    "ref": obj.ref if obj.ref else obj.number,
                    "related_id": "sale.order,%s" % obj.id,
                    "contact_id": contact.id,
                    "ship_address_id": ship_address_id,
                    "lines": [],
                    "state": "draft",
                    "ship_method_id": ship_method_id,
                    "company_id": obj.company_id.id,
                    "date": due_date+" "+(obj.ship_time or "00:00:00"),
                }
                if contact and contact.pick_out_journal_id:
                    pick_vals[pick_key]["journal_id"] = contact.pick_out_journal_id.id
            line_vals = {
                "product_id": prod.id,
                "lot_id": line.lot_id.id,
                "qty": qty_remain,
                "uom_id": prod.uom_id.id if line.qty_stock else line.uom_id.id,
                "qty2": line.qty2,
                "uom2_id": line.uom2_id.id,
                "location_from_id": line.reserve_location_id.id or line.location_id.id or wh_loc_id,
                "location_to_id": cust_loc_id,
                "related_id": "sale.order,%s" % obj.id,
                "notes": line.notes,
            }
            pick_vals[pick_key]["lines"].append(("create", line_vals))
        if not pick_vals:
            raise Exception("Nothing left to deliver")
        pick_ids=[]
        for pick_key, pick_val in pick_vals.items():
            pick_id = get_model("stock.picking").create(pick_val, context={"pick_type": "out"})
            pick_ids.append(pick_id)
        return {
            "next": {
                "name": "pick_out",
                "mode": "form",
                "active_id": pick_ids[0],
            },
            "flash": "Picking created from sales order %s" % obj.number,
            "picking_ids": pick_ids,
            "picking_id": pick_ids[0] if pick_ids else None, # XXX: remove later
        }

    def copy_to_reserve_picking(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids[0])
        contact = obj.contact_id
        pick_vals = {
            "type": "internal",
            "ref": obj.number,
            "related_id": "sale.order,%s" % obj.id,
            "contact_id": contact.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
        }
        for line in obj.lines:
            prod = line.product_id
            if prod.type not in ("stock", "consumable"):
                continue
            remain_qty=line.qty
            if not line.location_id:
                raise Exception("Missing location for product '%s'"%prod.name)
            if not line.reserve_location_id.id:
                raise Exception("Missing reservation location for product '%s'"%prod.name)
            line_vals = {
                "product_id": prod.id,
                "qty": remain_qty,
                "uom_id": prod.uom_id.id,
                "location_from_id": line.location_id.id,
                "location_to_id": line.reserve_location_id.id,
                "related_id": "sale.order,%s" % obj.id,
            }
            pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            return {
                "alert": "Nothing to reserve",
            }
        pick_id = get_model("stock.picking").create(pick_vals, {"pick_type": "internal"})
        pick = get_model("stock.picking").browse(pick_id)
        return {
            "next": {
                "name": "pick_internal",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Goods transfer %s created from sales order %s" % (pick.number, obj.number),
            "picking_id": pick_id,
        }

    def copy_to_invoice(self, ids, context={}):
        print("sale.copy_to_invoice",ids)
        inv_vals=None
        for obj in self.browse(ids):
            if obj.state!="confirmed":
                raise Exception("Sales order must be confirmed first.")
            if inv_vals is None:
                inv_vals = {
                    "type": "out",
                    "inv_type": "invoice",
                    "contact_id": obj.contact_id.id,
                    "bill_address_id": obj.bill_address_id.id,
                    "currency_id": obj.currency_id.id,
                    "tax_type": obj.tax_type,
                    "pay_method_id": obj.pay_method_id.id,
                    "lines": [],
                    "company_id": obj.company_id.id,
                    "pay_term_id": obj.pay_term_id.id or obj.contact_id.pay_term_id.id,
                    "ref": "%s / %s"%(obj.number,obj.ref or ""),
                    "date": obj.due_date or time.strftime("%Y-%m-%d"),
                    "seller_id": obj.seller_id.id,
                    "sale_categ_id": obj.sale_categ_id.id,
                }
                if obj.pay_term_id and obj.pay_term_id.days:
                    d=datetime.strptime(inv_vals["date"],"%Y-%m-%d")
                    d+=timedelta(days=obj.pay_term_id.days)
                    inv_vals["due_date"]=d.strftime("%Y-%m-%d")
                set_active_company(obj.company_id.id) # XXX
            else:
                if obj.contact_id.id!=inv_vals["contact_id"]:
                    raise Exception("Sales orders are for different customers")
                if obj.bill_address_id.id!=inv_vals["bill_address_id"]:
                    raise Exception("Sales orders have different billing address")
                if obj.currency_id.id!=inv_vals["currency_id"]:
                    raise Exception("Sales orders have different currencies")
                if obj.tax_type!=inv_vals["tax_type"]:
                    raise Exception("Sales orders have different tax types")
                if obj.pay_method_id.id!=inv_vals["pay_method_id"]:
                    raise Exception("Sales orders have different payment methods")
                if obj.company_id.id!=inv_vals["company_id"]:
                    raise Exception("Sales orders are in different companies")
            for line in obj.lines:
                #if not line.unit_price:
                #    continue
                prod = line.product_id
                #remain_qty = line.qty - line.qty_invoiced
                remain_qty=line.qty # XXX
                if remain_qty <= 0:
                    continue
                sale_acc_id=None
                if prod:
                    sale_acc_id=prod.sale_account_id.id
                    if not sale_acc_id and prod.parent_id:
                        sale_acc_id=prod.parent_id.sale_account_id.id
                    if not sale_acc_id and prod.categ_id and prod.categ_id.sale_account_id:
                        sale_acc_id=prod.categ_id.sale_account_id.id
                line_vals = {
                    "sequence_no": line.sequence_no,
                    "product_id": prod.id,
                    "description": line.description,
                    "qty": remain_qty,
                    "uom_id": line.uom_id.id,
                    "unit_price": line.unit_price,
                    "discount": line.discount,
                    "discount_amount": line.discount_amount,
                    "account_id": sale_acc_id,
                    "tax_id": line.tax_id.id,
                    "amount": line.qty*line.unit_price*(1-(line.discount or Decimal(0))/100)-(line.discount_amount or Decimal(0)),
                    "related_id": "sale.order,%d"%obj.id,
                    "track_id": line.track_id.id, #2020-11-02 Chin
                    "track2_id": line.track2_id.id, #2020-11-02 Chin
                    "notes": line.notes,
                }
                inv_vals["lines"].append(("create", line_vals))
                if line.promotion_amount:
                    prom_acc_id=None
                    if prod:
                        prom_acc_id=prod.sale_promotion_account_id.id
                        if not prom_acc_id and prod.parent_id:
                            prom_acc_id=prod.parent_id.sale_promotion_account_id.id
                    if not prom_acc_id:
                        prom_acc_id=sale_acc_id
                    line_vals = {
                        "product_id": prod.id,
                        "description": "Promotion on product %s"%prod.code,
                        "account_id": prom_acc_id,
                        "tax_id": line.tax_id.id,
                        "amount": -line.promotion_amount,
                    }
                    inv_vals["lines"].append(("create", line_vals))
            for line in obj.used_promotions:
                if line.product_id or line.percent:
                    continue
                prom=line.promotion_id
                prod = prom.product_id
                line_vals = {
                    "product_id": prod.id,
                    "description": prom.name,
                    "account_id": prod and prod.sale_account_id.id or None,
                    "tax_id": prod and prod.sale_tax_id.id or None,
                    "amount": -line.amount,
                }
                inv_vals["lines"].append(("create", line_vals))
        if not inv_vals or not inv_vals["lines"]:
            #raise Exception("Nothing to invoice")
            return {
                "alert": "Nothing to invoice",
                "alert_type": "danger",
            }
        inv_id = get_model("account.invoice").create(inv_vals, {"type": "out", "inv_type": "invoice", "date": inv_vals["date"]})
        inv=get_model("account.invoice").browse(inv_id)
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv_id,
            },
            "flash": "Invoice %s created from sales order" % inv.number,
            "invoice_id": inv_id,
        }

    def get_delivered(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            is_delivered = True
            for line in obj.lines:
                prod = line.product_id
                if prod.type not in ("stock", "consumable", "bundle"):
                    continue
                remain_qty = (line.qty_stock or line.qty or 0) - line.qty_delivered
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
            is_paid = amt_paid >= obj.amount_subtotal # XXX: check this for tax-in
            vals[obj.id] = is_paid
        return vals

    def get_invoiced(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            amt_invoiced = 0
            for inv_line in obj.invoice_lines:
                inv=inv_line.invoice_id
                if inv.state not in ("waiting_payment","paid"):
                    continue
                amt_invoiced += inv_line.amount
            is_invoiced = amt_invoiced >= obj.amount_subtotal # XXX: check this for tax-in
            vals[obj.id] = is_invoiced
        return vals

    def void(self, ids, context={}):
        for obj in self.browse(ids):
            for pick in obj.pickings:
                if pick.state == "pending":
                    raise Exception("There are still pending goods issues for this sales order")
            for inv in obj.invoices:
                if inv.state == "waiting_payment":
                    raise Exception("There are still invoices waiting payment for this sales order")
            obj.write({"state": "voided"})

    def copy(self, ids, context):
        obj = self.browse(ids)[0]
        lines=[]
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "discount": line.discount,
                "discount_amount": line.discount_amount,
                "uom_id": line.uom_id.id,
                "location_id": line.location_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "cost_price": line.cost_price,
                "notes": line.notes,
            }
            lines.append(("create", line_vals))
        vals={
            "number": obj.number+" (copy)",
            "lines": lines,
            "due_date": None,
            "ship_time": None,
            "delivery_date": None,
        }
        new_id = obj._copy(vals)[0]
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Sales order %s copied to %s" % (obj.number, new_obj.number),
            "sale_id": new_id,
        }

    def get_invoices(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            inv_ids = []
            for inv in obj.invoices_direct:
                inv_ids.append(inv.id)
            for inv_line in obj.invoice_lines:
                inv_id = inv_line.invoice_id.id
                inv_ids.append(inv_id)
            vals[obj.id] = list(set(inv_ids))
        return vals

    def get_pickings(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            pick_ids = []
            for move in obj.stock_moves:
                pick_id = move.picking_id.id
                if pick_id and pick_id not in pick_ids:
                    pick_ids.append(pick_id)
            vals[obj.id] = pick_ids
        return vals

    def onchange_contact(self, context):
        data = context["data"]
        contact_id = data.get("contact_id")
        contact = get_model("contact").browse(contact_id) if contact_id else None
        #data["payment_terms"] = contact.payment_terms if contact else None
        data["contact_person_id"]=contact.contact_person_id.id if contact else None
        data["pay_term_id"]=contact.sale_pay_term_id.id
        data["price_list_id"] = contact.sale_price_list_id.id if contact else None
        data["bill_address_id"] = contact.get_address(pref_type="billing") if contact else None
        data["ship_address_id"] = contact.get_address(pref_type="shipping") if contact else None
        data["seller_contact_id"]=contact.seller_contact_id.id
        if contact.currency_id:
            data["currency_id"] = contact.currency_id.id
        else:
            settings = get_model("settings").browse(1)
            data["currency_id"] = settings.currency_id.id
        return data

    def onchange_agent(self, context):
        data = context["data"]
        agent_id = data.get("agent_id")
        agent = get_model("contact").browse(agent_id) if agent_id else None
        #data["payment_terms"] = contact.payment_terms if contact else None
        data["agent_person_id"]= agent.contact_person_id.id if agent else None
        data["agent_address_id"] = agent.get_address(pref_type="billing") if agent else None
        return data

    def check_delivered_qtys(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids)[0]
        for line in obj.lines:
            check_percent=settings.sale_check_delivered_qty
            if check_percent is not None:
                max_qty=line.qty*(100+check_percent)/Decimal(100)
                if line.qty_delivered > max_qty:
                    raise Exception("Can not deliver excess quantity for sales order %s and product %s (order qty: %s, delivered qty: %s)" % (
                        obj.number, line.product_id.code, line.qty_stock or line.qty, line.qty_delivered))

    def copy_to_purchase(self, ids, context={}):
        obj = self.browse(ids)[0]
        suppliers = {}
        for line in obj.lines:
            prod = line.product_id
            if not prod:
                continue
            #if prod.type!="stock":
            #    continue
            if prod.supply_method!="purchase":
                continue
            supplier_id=line.supplier_id.id
            if not supplier_id:
                #if prod.procure_method != "mto" or prod.supply_method != "purchase":
                #    continue
                if not prod.suppliers:
                    raise Exception("Missing supplier for product '%s'" % prod.name)
                supplier_id = prod.suppliers[0].supplier_id.id
            suppliers.setdefault(supplier_id, []).append((prod.id, line.qty, line.uom_id.id, line.description))
        if not suppliers:
            raise Exception("No purchase orders to create")
        po_ids = []
        for supplier_id, lines in suppliers.items():
            contact=get_model("contact").browse(supplier_id)
            purch_vals = {
                "contact_id": supplier_id,
                "ref": obj.number,
                "lines": [],
                "pay_term_id": contact.sale_pay_term_id.id,
                "related_id": "sale.order,%s"%obj.id,
            }
            for prod_id, qty, uom_id, desc in lines:
                prod = get_model("product").browse(prod_id)
                line_vals = {
                    "product_id": prod_id,
                    "description": desc or "/",
                    "qty": qty,
                    "uom_id": uom_id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "sale_id": obj.id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            po_ids.append(po_id)
        po_objs = get_model("purchase.order").browse(po_ids)
        return {
            "next": {
                "name": "purchase",
            },
            "flash": "Purchase orders created successfully: " + ", ".join([po.number for po in po_objs]),
        }

    def copy_to_production(self, ids, context={}):
        order_ids = []
        mfg_orders = {}
        for obj in self.browse(ids):
            for line in obj.lines:
                prod = line.product_id
                if not prod:
                    continue
                #if prod.procure_method!="mto" or prod.supply_method != "production":
                #    continue
                if prod.supply_method != "production":
                    continue
                due_date=line.due_date or obj.due_date
                if not due_date:
                    raise Exception("Missing shipping date in sales order %s"%obj.number)
                if context.get("due_date") and due_date!=context["due_date"]:
                    continue
                if line.production_id:
                    raise Exception("Production order already created for sales order %s, product %s"%(obj.number,prod.code))
                k=(prod.id,due_date)
                mfg_orders.setdefault(k,[]).append(line.id)
        for (prod_id,due_date),sale_line_ids in mfg_orders.items():
            prod=get_model("product").browse(prod_id)
            res=get_model("bom").search([["product_id","=",prod.id]]) # TODO: select bom in separate function
            if not res:
                raise Exception("BoM not found for product '%s'" % prod.name)
            bom_id = res[0]
            bom = get_model("bom").browse(bom_id)
            loc_id = bom.location_id.id
            if not loc_id:
                raise Exception("Missing FG location in BoM %s" % bom.number)
            loc_prod_id = bom.production_location_id.id
            if not loc_prod_id:
                raise Exception("Missing production location in BoM %s" % bom.number)
            uom = prod.uom_id
            mfg_qty=0
            for line in get_model("sale.order.line").browse(sale_line_ids):
                if line.qty_stock:
                    qty = line.qty_stock
                else:
                    qty = get_model("uom").convert(line.qty, line.uom_id.id, uom.id)
                mfg_qty+=qty
            mfg_date=(datetime.strptime(due_date,"%Y-%m-%d")-timedelta(days=prod.mfg_lead_time or 0)).strftime("%Y-%m-%d")
            order_vals = {
                "product_id": prod.id,
                "qty_planned": mfg_qty,
                "uom_id": uom.id,
                "bom_id": bom_id,
                "production_location_id": loc_prod_id,
                "location_id": loc_id,
                "order_date": mfg_date,
                "due_date": due_date,
                "state": "draft",
                "sale_id": ids[0], # XXX
                "customer_id": obj.contact_id.id, # XXX
            }
            order_id = get_model("production.order").create(order_vals)
            get_model("production.order").create_components([order_id])
            get_model("production.order").create_operations([order_id])
            order_ids.append(order_id)
            get_model("sale.order.line").write(sale_line_ids,{"production_id":order_id})
        if not order_ids:
            return {
                "flash": "No production orders to create",
            }
        return {
            "flash": "Production orders created successfully",
            "order_ids": order_ids,
        }

    def get_production_status(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            num_done = 0
            num_total = 0
            for prod in obj.production_orders:
                if prod.state == "done":
                    num_done += 1
                if prod.state not in ("voided", "split"):
                    num_total += 1
            if num_total != 0:
                percent = num_done * 100 / num_total
                vals[obj.id] = {
                    "percent": percent,
                    "string": "%d / %d" % (num_done, num_total)
                }
            else:
                vals[obj.id] = None
        return vals

    def get_overdue(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.due_date:
                vals[obj.id] = obj.due_date < time.strftime("%Y-%m-%d") and obj.state in ("draft", "waiting", "ready")
            else:
                vals[obj.id] = False
        return vals

    def search_overdue(self, clause, context={}):
        return [["due_date", "<", time.strftime("%Y-%m-%d")], ["state", "in", ["draft", "waiting", "ready"]]]

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

    def approve(self, ids, context={}):
        if not check_permission_other("sale_approve_done"):
            raise Exception("Permission denied")
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"approved_by_id": user_id})
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": obj.id,
            },
            "flash": "Sales order approved successfully",
        }

    def find_sale_line(self, ids, product_id, context={}):
        obj = self.browse(ids)[0]
        for line in obj.lines:
            if line.product_id.id == product_id:
                return line.id
        return None

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

    def get_state_label(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.state == "draft":
                s = "Draft"
            if obj.state == "confirmed":
                s = "Confirmed"
            elif obj.state == "done":
                s = "Completed"
            elif obj.state == "voided":
                s = "Voided"
            else:
                s = "/"
            vals[obj.id] = s
        return vals

    def get_ship_tracking(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            track_nos = []
            for pick in obj.pickings:
                if pick.ship_tracking:
                    track_nos.append(pick.ship_tracking)
            vals[obj.id] = ", ".join(track_nos)
        return vals

    def get_pickings(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            pick_ids = []
            for move in obj.stock_moves:
                if move.picking_id:
                    pick_ids.append(move.picking_id.id)
            pick_ids = sorted(list(set(pick_ids)))
            vals[obj.id] = pick_ids
        return vals

    def copy_to_project(self, ids, context={}):
        obj = self.browse(ids)[0]
        if obj.project_id:
            raise Exception("Project already created for sales order %s"%obj.number)
        if not obj.track_id:
            obj.create_track()
            obj=obj.browse()[0]
        vals={
            "name": obj.contact_id.name or "/",
            "contact_id": obj.contact_id.id,
            "sale_categ_id": obj.sale_categ_id.id,
            "track_id": obj.track_id.id,
            "sale_price": obj.amount_total,
        }
        proj_id=get_model("project").create(vals)
        obj.write({"project_id":proj_id})
        return {
            "flash": "Project created from sales order %s" % obj.number,
            "next": {
                "name": "project",
                "mode": "form",
                "active_id": proj_id,
            },
        }

    def copy_to_job(self, ids, context={}):
        obj = self.browse(ids)[0]
        tmpl = obj.job_template_id
        if not tmpl:
            raise Exception("Missing service order template in sales order")
        job_id = tmpl.create_job(sale_id=obj.id)
        job = get_model("job").browse(job_id)
        return {
            "flash": "Service order %s created from sales order %s" % (job.number, obj.number),
            "next": {
                "name": "job",
                "mode": "form",
                "active_id": job_id,
            },
        }

    def get_profit_old(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            est_cost_total = 0
            act_cost_total = 0
            for cost in obj.costs:
                amt = cost.amount or 0
                if cost.currency_id:
                    amt = get_model("currency").convert(amt, cost.currency_id.id, obj.currency_id.id)
                est_cost_total += amt
                act_amt = cost.actual_amount or 0
                if cost.currency_id:
                    act_amt = get_model("currency").convert(act_amt, cost.currency_id.id, obj.currency_id.id)
                act_cost_total += act_amt
            est_profit = obj.amount_subtotal - est_cost_total
            est_profit_percent = est_profit * 100 / obj.amount_subtotal if obj.amount_subtotal else None
            act_profit = obj.amount_subtotal - act_cost_total
            act_profit_percent = act_profit * 100 / obj.amount_subtotal if obj.amount_subtotal else None
            vals[obj.id] = {
                "est_cost_total": est_cost_total,
                "est_profit": est_profit,
                "est_profit_percent": est_profit_percent,
                "act_cost_total": act_cost_total,
                "act_profit": act_profit,
                "act_profit_percent": act_profit_percent,
            }
        return vals

    def onchange_cost_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if prod_id:
            prod = get_model("product").browse(prod_id)
            line["description"] = prod.description
            line["unit_price"] = prod.landed_cost
            line["qty"] = 1
            line["uom_id"] = prod.uom_id.id
            line["currency_id"] = prod.purchase_currency_id.id
            line["purchase_duty_percent"] = prod.purchase_duty_percent
            line["purchase_ship_percent"] = prod.purchase_ship_percent
            line["landed_cost"] = prod.landed_cost
            line["purchase_price"] = prod.purchase_price
            if prod.suppliers:
                line["supplier_id"] = prod.suppliers[0].supplier_id.id
        return data

    def get_cost_per_supplier(self, ids, context):
        vals = {}
        for obj in self.browse(ids):
            sup_cost = {}
            for line in obj.costs:
                sup = line.supplier_id.name if line.supplier_id else "/"
                sup_cost.setdefault(sup, [0, 0])
                sup_cost[sup][0] += line.amount or 0
                sup_cost[sup][1] += line.actual_amount or 0
            data = []
            for sup in sorted(sup_cost):
                data.append({
                    "name": sup,
                    "est_cost_total": sup_cost[sup][0],
                    "act_cost_total": sup_cost[sup][1],
                })
            vals[obj.id] = data
        return vals

    def cancel_unpaid_order(self, num_days=7):
        exp_date = datetime.now() - timedelta(days=num_days)
        exp_date = exp_date.strftime("%Y-%m-%d")
        res = self.search([["date", "<", exp_date], ["state", "=", "confirmed"]])
        number = "Expired Date-" + exp_date + " Order -"
        for obj in self.browse(res):
            if not obj.is_paid:
                number += obj.number + "-"
                for pick in obj.pickings:
                    pick.void()
                for inv in obj.invoices:
                    if inv.state == "waiting_payment":
                        inv.void()
                obj.void()
        print(number)

    def get_est_profit(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            cost=0
            for line in obj.lines:
                cost+=line.est_cost_amount or 0
            profit=obj.amount_subtotal-cost
            margin=profit*100/obj.amount_subtotal if obj.amount_subtotal else None
            vals[obj.id] = {
                "est_cost_amount": cost,
                "est_profit_amount": profit,
                "est_margin_percent": margin,
            }
        return vals

    def get_track_entries(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if not obj.track_id:
                vals[obj.id]=[]
                continue
            res=get_model("account.track.entry").search([["track_id","child_of",obj.track_id.id]])
            vals[obj.id]=res
        return vals

    def write_track_entries(self,ids,field,val,context={}):
        for op in val:
            if op[0]=="create":
                rel_vals=op[1]
                for obj in self.browse(ids):
                    if not obj.track_id:
                        continue
                    rel_vals["track_id"]=obj.track_id.id
                    get_model("account.track.entry").create(rel_vals,context=context)
            elif op[0]=="write":
                rel_ids=op[1]
                rel_vals=op[2]
                get_model("account.track.entry").write(rel_ids,rel_vals,context=context)
            elif op[0]=="delete":
                rel_ids=op[1]
                get_model("account.track.entry").delete(rel_ids,context=context)

    def get_act_profit(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            cost=0
            for line in obj.track_entries:
                cost-=line.amount
            cost+=obj.act_mfg_cost or 0 # XXX
            profit=obj.amount_subtotal-cost
            margin=profit*100/obj.amount_subtotal if obj.amount_subtotal else None
            vals[obj.id] = {
                "act_cost_amount": cost,
                "act_profit_amount": profit,
                "act_margin_percent": margin,
            }
        return vals

    def get_act_mfg_cost(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for mfg in obj.production_orders:
                amt+=mfg.total_cost or 0
            vals[obj.id]=amt
        return vals

    def create_track(self,ids,context={}):
        obj=self.browse(ids[0])
        code=obj.number
        res=get_model("account.track.categ").search([["code","=",code]])
        if res:
            sale_track_id=res[0]
        else:
            sale_track_id=get_model("account.track.categ").create({
                "code": code,
                "name": obj.contact_id.name,
                "type": "1",
                })
        obj.write({"track_id":sale_track_id})
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": obj.id,
            },
            "flash": "Tracking code created",
        }

    def create_est_costs(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"est_costs":[("delete_all",)]})
        for line in obj.lines:
            prod=line.product_id
            if not prod:
                continue
            if not line.sequence:
                continue
            if "bundle" == prod.type:
                continue
            vals={
                "sale_id": obj.id,
                "sequence": line.sequence,
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
                "currency_rate": prod.purchase_currency_rate,
            }
            get_model("sale.cost").create(vals)

    def copy_cost_to_purchase(self, ids, context={}):
        obj = self.browse(ids)[0]
        suppliers = {}
        for cost in obj.est_costs:
            prod = line.product_id
            if not prod:
                continue
            if not prod.suppliers:
                raise Exception("Missing supplier for product '%s'" % prod.name)
            supplier_id = prod.suppliers[0].supplier_id.id
            suppliers.setdefault(supplier_id, []).append((prod.id, line.qty, line.uom_id.id))
        if not suppliers:
            raise Exception("No purchase orders to create")
        po_ids = []
        for supplier_id, lines in suppliers.items():
            purch_vals = {
                "contact_id": supplier_id,
                "ref": obj.number,
                "lines": [],
            }
            for prod_id, qty, uom_id in lines:
                prod = get_model("product").browse(prod_id)
                line_vals = {
                    "product_id": prod_id,
                    "description": prod.description or "/",
                    "qty": qty,
                    "uom_id": uom_id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "sale_id": obj.id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            po_ids.append(po_id)
        po_objs = get_model("purchase.order").browse(po_ids)
        return {
            "next": {
                "name": "purchase",
                "search_condition": [["ref", "=", obj.number]],
            },
            "flash": "Purchase orders created successfully: " + ", ".join([po.number for po in po_objs]),
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

    def copy_to_sale_return(self,ids,context={}):
        for obj in self.browse(ids):
            order_vals = {}
            order_vals = {
                "contact_id":obj.contact_id.id,
                "date":obj.date,
                "ref":obj.number,
                "due_date":obj.due_date,
                "currency_id":obj.currency_id.id,
                "tax_type":obj.tax_type,
                "bill_address_id":obj.bill_address_id.id,
                "ship_address_id":obj.ship_address_id.id,
                "lines":[],
            }
            for line in obj.lines:
                line_vals = {
                    "product_id":line.product_id.id,
                    "description":line.description,
                    "qty":line.qty,
                    "uom_id":line.uom_id.id,
                    "unit_price":line.unit_price,
                    "discount":line.discount,
                    "discount_amount":line.discount_amount,
                    "tax_id":line.tax_id.id,
                    "amount":line.amount,
                    "location_id":line.location_id.id,
                }
                order_vals["lines"].append(("create", line_vals))
            sale_id = get_model("sale.return").create(order_vals)
            sale = get_model("sale.return").browse(sale_id)
        return {
            "next": {
                "name": "sale_return",
                "mode": "form",
                "active_id": sale_id,
            },
            "flash": "Sale Return %s created from sales order %s" % (sale.number, obj.number),
            "order_id": sale_id,
        }

    def create_invoice_payment(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.is_paid:
            raise Exception("Sales order %s is alredy paid"%obj.number)
        if obj.invoices:
            raise Exception("There are already invoices created for sales order %s"%obj.number)
        res=obj.copy_to_invoice()
        inv_id=res["invoice_id"]
        inv=get_model("account.invoice").browse(inv_id)
        inv.post()
        method=obj.pay_method_id
        if not method:
            raise Exception("Missing payment method for sales order %s"%obj.number)
        if not method.account_id:
            raise Exception("Missing account for payment method %s"%method.name)
        transaction_no=context.get("transaction_no")
        pmt_vals={
            "type": "in",
            "pay_type": "invoice",
            "contact_id": inv.contact_id.id,
            "account_id": method.account_id.id,
            "lines": [],
            "company_id": inv.company_id.id,
            "transaction_no": transaction_no,
        }
        line_vals={
            "invoice_id": inv_id,
            "amount": inv.amount_total,
        }
        pmt_vals["lines"].append(("create",line_vals))
        pmt_id=get_model("account.payment").create(pmt_vals,context={"type": "in"})
        get_model("account.payment").post([pmt_id])
        for pick in obj.pickings: # XXX
            if pick.state=="pending":
                pick.approve()

    def pay_online(self,ids,context={}):
        print("SaleOrder.pay_online",ids)
        obj=self.browse(ids[0])
        set_active_company(obj.company_id.id) # XXX
        pay_method_id=context.get("pay_method_id")
        if pay_method_id:
            method=get_model("payment.method").browse(pay_method_id)
            obj.write({"pay_method_id":method.id})
        else:
            method=obj.pay_method_id
            if not method:
                raise Exception("Missing payment method for sales order %s"%obj.number)
        ctx={
            "amount": obj.amount_total,
            "currency_id": obj.currency_id.id,
            "order_number": obj.number,
            "details": "Order %s"%obj.number,
            "contact_id": obj.contact_id.id,
            "sale_id": obj.id,
        }
        res=method.start_payment(context=ctx)
        if not res:
            raise Exception("Failed to start online payment for sales order %s"%obj.number)
        transaction_no=res["transaction_no"]
        print("transaction_no: %s"%transaction_no)
        obj.write({"transaction_no":transaction_no})
        if res.get("payment_done"):
            obj.create_invoice_payment()
        return {
            "transaction_no": transaction_no,
            "next": res.get("payment_action"),
        }

    def payment_received(self,ids,context={}):
        print("SaleOrder.payment_received",ids)
        obj=self.browse(ids[0])
        if not obj.invoices:
            raise Exception("Invoice not found for sales order %s"%obj.number)
        inv=obj.invoices[0]
        pay_method_id=context.get("pay_method_id")
        if not pay_method_id:
            raise Exception("Missing payment method")
        pay_method=get_model("payment.method").browse(pay_method_id)
        if not pay_method.account_id:
            raise Exception("Missing account for payment method %s"%pay_method.name)
        obj.write({"pay_method_id":pay_method_id})
        vals={
            "type": "in",
            "pay_type": "invoice",
            "contact_id": obj.contact_id.id,
            "account_id": pay_method.account_id.id,
            "pay_method_id": pay_method.id,
            "lines": [],
        }
        amt=inv.amount_total
        line_vals={
            "type": "invoice",
            "invoice_id": inv.id,
            "amount_invoice": amt,
            "amount": amt,
        }
        vals["lines"].append(("create",line_vals))
        payment_id=get_model("account.payment").create(vals,context={"type":vals["type"]})
        get_model("account.payment").post([payment_id])
        return {
            "payment_id": payment_id,
        }

    """
    def import_record(self,vals,context={}):
        print("SaleOrder.import_record",vals)
        if "contact" in vals:
            contact_id=get_model("contact").import_record(vals["contact"],context=context)
            vals["ship_address_id"]["contact_id"]=contact_id
        return super().import_record(vals,context=context)
    """

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

    def copy_to_cart(self, ids, context={}):
        obj=self.browse(ids[0])
        cart=obj.related_id
        if not cart or cart._model!="ecom2.cart":
            raise Exception("Missing cart")
        res=cart.copy()
        return {
            "cart_id": res["new_id"],
        }

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

    def copy_to_rm_picking(self, ids, context={}):
        settings=get_model("settings").browse(1)
        obj = self.browse(ids[0])
        contact = obj.contact_id
        pick_vals = {
            "type": "out",
            "ref": "RM-IN "+obj.number,
            "related_id": "sale.order,%s" % obj.id,
            "contact_id": contact.id,
            "currency_id": obj.currency_id.id,
            "lines": [],
        }
        if obj.due_date:
            pick_vals["date"]=obj.due_date
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
                for comp in bom.lines:
                    prod=comp.product_id
                    if prod.supply_method!="customer":
                        continue
                    if not prod.locations:
                        raise Exception("Missing location for product %s"%prod.name)
                    rm_loc_id=prod.locations[0].location_id.id
                    qty=comp.qty*ratio
                    line_vals = {
                        "product_id": prod.id,
                        "qty": qty,
                        "uom_id": comp.uom_id.id,
                        "location_from_id": rm_loc_id,
                        "location_to_id": comp.location_id.id,
                        "related_id": "sale.order,%s" % obj.id,
                    }
                    pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            raise Exception("No raw materials found to receive")
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

    def copy_to_customer_purchase(self,ids,context={}):
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
        access.set_active_company(other_company_id)
        purch_vals={
            "contact_id": contact_id,
            "ref": "%s: %s"%(company.name,obj.number),
            "delivery_date": obj.due_date,
            "lines": [],
        }
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
                "location_id": loc_id,
            }
            purch_vals["lines"].append(("create",line_vals))
        purch_id=get_model("purchase.order").create(purch_vals)
        purch=get_model("purchase.order").browse(purch_id)
        purch_num=purch.number
        access.set_active_company(company_id)
        return {
            "flash": "Purchase order %s created in company %s from sales order %s" % (purch_num, other_company.name, obj.number),
            "purchase_id": purch_id,
        }

    def apply_voucher(self,ids,context={}):
        print("apply_voucher",ids)
        obj=self.browse(ids[0])
        if obj.is_voucher_applied:
            raise Exception("Voucher is already applied")
        voucher=obj.voucher_id
        if not voucher:
            raise Exception("No voucher selected")
        ctx={
            "contact_id": obj.contact_id.id,
            "amount_total": obj.amount_total,
            "products": [],
        }
        for line in obj.lines:
            ctx["amount_total"]+=line.amount
            ctx["products"].append({
                "product_id": line.product_id.id,
                "unit_price": line.unit_price,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "amount": line.amount,
            })
        res=voucher.apply_voucher(context=ctx)
        disc_amount=res.get("discount_amount",0)
        error_message=res.get("error_message")
        print("disc_amount",disc_amount)
        print("error_message",error_message)
        if error_message:
            raise Exception(error_message)
        if disc_amount:
            vals={
                "order_id": obj.id,
                "product_id": voucher.product_id.id,
                "description": "Voucher %s"%voucher.code,
                "qty": 1,
                "unit_price": -disc_amount,
            }
            get_model("sale.order.line").create(vals)

    def apply_all_vouchers(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.voucher_id:
            raise Exception("Voucher already applied: %s"%obj.voucher_id.code)
        ctx={
            "contact_id": obj.contact_id.id,
            "amount_total": obj.amount_total,
            "products": [],
        }
        for line in obj.lines:
            ctx["amount_total"]+=line.amount
            ctx["products"].append({
                "product_id": line.product_id.id,
                "unit_price": line.unit_price,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "amount": line.amount,
            })
        found_voucher=None
        for voucher in get_model("sale.voucher").search_browse([]):
            res=voucher.apply_voucher(context=ctx)
            disc_amount=res.get("discount_amount",0)
            if disc_amount:
                found_voucher=voucher
                break
        if found_voucher:
            vals={
                "order_id": obj.id,
                "product_id": voucher.product_id.id,
                "description": "Voucher %s"%voucher.code,
                "qty": 1,
                "unit_price": -disc_amount,
            }
            get_model("sale.order.line").create(vals)
            obj.write({"voucher_id":found_voucher.id})
        else:
            raise Exception("No applicable voucher found")

    def get_is_voucher_applied(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            has_discount=False
            for line in obj.lines:
                if line.amount<0:
                    has_discount=True
            vals[obj.id]=has_discount
        return vals

    def get_raw_mats(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod_qtys={}
            for mo in obj.production_orders:
                for comp in mo.components:
                    k=(comp.product_id.id,comp.uom_id.id)
                    prod_qtys.setdefault(k,0)
                    prod_qtys[k]+=comp.qty_planned
            data=[]
            for (prod_id,uom_id),qty in prod_qtys.items():
                prod=get_model("product").browse(prod_id)
                uom=get_model("uom").browse(uom_id)
                name=prod.name
                if not prod.active:
                    name+=" [ARCHIVED]"
                data.append({
                    "product_code": prod.code,
                    "product_name": name,
                    "qty": qty,
                    "uom_name": uom.name,
                })
            data.sort(key=lambda r: r["product_code"])
            vals[obj.id]=data
        return vals

    def get_due_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d=None
            if obj.due_date:
                d=datetime.strptime(obj.due_date,"%Y-%m-%d")
            vals[obj.id]=d.strftime("%A") if d else None
        return vals

    def onchange_date(self, context={}):
        data = context["data"]
        ctx = {
            "date": data["date"],
        }
        if not data.get("id"):
            number = self._get_number(context=ctx)
            data["number"] = number
        return data

    def reserve(self, ids, context={}):
        obj=self.browse(ids[0])
        settings = get_model("settings").browse(1)
        if settings.reserve_sale_reserve and not access.check_permission_other("reserve_sale"):
            raise Exception("User does not have permission to reserve sales orders (reserve_sale).")
        obj.write({"state":"reserved"})
        if settings.sale_copy_reserve_picking:
            res=obj.copy_to_reserve_picking()
            picking_ids=res.get("picking_ids")
            if picking_ids:
                get_model("stock.picking").set_done(picking_ids)
        obj.trigger("reserve")
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": obj.id,
            },
            "flash": "Sales order %s reserved" % obj.number,
        }

    def gen_report(self,date_from=None,context={}):
        print("SO.gen_report",date_from)
        db=database.get_connection()
        report_seq=0
        db.execute("UPDATE sale_order SET report_no=null WHERE date>=%s",date_from)
        date_objs={}
        for obj in get_model("sale.order").search_browse([["date",">=",date_from]],order="date"):
            date_objs.setdefault(obj.date,[]).append(obj)
        date_targets={}
        for obj in get_model("sale.target").search_browse([["date_from",">=",date_from]],order="date_from"):
            date_targets[obj.date_from]=obj.amount_target
        dates=list(date_objs.keys())
        dates.sort()
        for date in dates:
            print("-"*80)
            print("date",date)
            target=date_targets.get(date)
            print("target",target)
            objs=date_objs[date]
            print("num SO",len(objs))
            incl_ids=[]
            total=0
            for obj in objs:
                incl=False
                if obj.receipt_printed:
                    incl=True
                if obj.pay_method_id and obj.pay_method_id.require_report:
                    incl=True
                if incl:
                    incl_ids.append(obj.id)
                    total+=obj.amount_total
            for obj in objs:
                if target and total>=target:
                    break
                if obj.id in incl_ids:
                    continue
                if obj.orig_sale_id:
                    incl_ids.append(obj.id)
                    incl_ids.append(obj.orig_sale_id.id)
                    total+=obj.amount_total
            rand_objs=[o for o in objs]
            random.shuffle(rand_objs)
            for obj in rand_objs:
                if target and total>=target:
                    break
                if obj.id in incl_ids:
                    continue
                incl_ids.append(obj.id)
                total+=obj.amount_total
            print("incl num",len(incl_ids))
            print("incl total",total)
            for obj in get_model("sale.order").browse(incl_ids):
                report_seq+=1
                prefix=datetime.strptime(obj.date,"%Y-%m-%d").strftime("%y%m-")
                report_no=prefix+"%.4d"%report_seq
                db.execute("UPDATE sale_order SET report_no=%s WHERE id=%s",report_no,obj.id)

    def search_incl_report(self,clause,context={}):
        val=clause[2]
        if val:
            return ["report_no","!=",None]
        else:
            return ["report_no","=",None]

    def update_cost_prices(self,ids,context={}):
        obj=self.browse(ids[0])
        prod_orders={}
        for mfg in obj.production_orders:
            prod_orders[mfg.product_id.id]=mfg # XXX: multi
        for line in obj.lines:
            prod=line.product_id
            if prod.supply_method!="production":
                continue
            mfg=prod_orders.get(prod.id)
            if mfg:
                cost_price=mfg.unit_cost or 0
            else: 
                cost_price=0
            line.write({"cost_price":cost_price})

    def set_tax_in(self,ids,context={}):
        for obj in self.browse(ids): 
            for line in obj.lines:
                prod=line.product_id
                if not prod:
                    continue
                line.write({"tax_id": prod.sale_tax_id.id})
            obj.write({"tax_type":"tax_in"})
            obj.function_store()
            for inv in obj.invoices:
                for line in inv.lines:
                    prod=line.product_id
                    if not prod:
                        continue
                    line.write({"tax_id": prod.sale_tax_id.id})
                    acc_id=prod.sale_tax_id.id
                    if not acc_id and prod.categ_id:
                        acc_id=prod.categ_id.sale_tax_id.id
                    if acc_id and not line.account_id: 
                        line.write({"account_id":acc_id})
                inv.write({"tax_type":"tax_in"})
                inv.function_store()

    def set_tax_in_all(self,context={}):
        ids=self.search([])
        self.set_tax_in(ids)

SaleOrder.register()
