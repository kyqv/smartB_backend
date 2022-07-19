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
from netforce.database import get_active_db
from PIL import Image
import io
import os
import base64
import json
import time
import urllib
from netforce import utils
import random
#from netforce_report import get_report_jasper # deprecated
from pprint import pprint
from decimal import *
from netforce import access
import requests
import urllib.parse
from lxml import etree
from decimal import *
from . import th_utils
import math


class Cart(Model):
    _name = "ecom.cart"
    _string = "Cart"
    _name_field="number"
    _fields = {
        "number": fields.Char("Number",required=True,search=True),
        "lines": fields.One2Many("ecom.cart.line", "cart_id", "Lines"),
        "used_promotions": fields.One2Many("ecom.cart.promotion", "cart_id", "Used Promotions"),
        "amount_subtotal": fields.Decimal("Subtotal",function="_get_total_amount",function_multi=True),
        "amount_ship": fields.Decimal("Shipping Amount"),
        "amount_discount": fields.Decimal("Additional Discount",function="_get_total_amount",function_multi=True),
        "amount_total": fields.Decimal("Total Amount", function="_get_total_amount", function_multi=True),
        "amount_total_words": fields.Char("Total Words", function="get_amount_total_words"),
        "total_qty": fields.Integer("Total Qty", function="_get_total_qty", function_multi=True),
        "total_weight": fields.Decimal("Total Weight", function="_get_total_weight", function_multi=True),
        "comments": fields.Text("Comments"),
        "email": fields.Char("Contact Email",search=True),
        "tax_no": fields.Char("Tax ID"),
        "tax_branch_no" :fields.Char("Tax Branch No"),
        "bill_first_name": fields.Char("First Name"),
        "bill_last_name": fields.Char("Last Name"),
        "bill_company": fields.Char("Company"),
        "bill_address": fields.Char("Address"),
        "bill_address2": fields.Char("Address2"),
        "bill_city": fields.Char("City"),
        "bill_country_id": fields.Many2One("country", "Country"),
        "bill_province_id": fields.Many2One("province", "Province"),
        "bill_district_id": fields.Many2One("district", "District"),
        "bill_subdistrict_id": fields.Many2One("subdistrict", "Sub District"),
        "bill_postal_code": fields.Char("Postal Code"),
        "bill_phone": fields.Char("Phone"),
        "ship_to_bill": fields.Boolean("Ship to billing address"),
        "ship_first_name": fields.Char("First Name"),
        "ship_last_name": fields.Char("Last Name"),
        "ship_company": fields.Char("Company"),
        "ship_address": fields.Char("Address"),
        "ship_address2": fields.Char("Address2"),
        "ship_city": fields.Char("City"),
        "ship_country_id": fields.Many2One("country", "Country"),
        "ship_province_id": fields.Many2One("province", "Province"),
        "ship_district_id": fields.Many2One("district", "District"),
        "ship_subdistrict_id": fields.Many2One("subdistrict", "Sub District"),
        "ship_postal_code": fields.Char("Postal Code"),
        "ship_phone": fields.Char("Phone"),
        "accept_marketing": fields.Boolean("Accept Marketing"),
        "payment_ref": fields.Char("Payment Ref",search=True),
        "contact_id": fields.Many2One("contact", "Contact",search=True),
        "sale_id": fields.Many2One("sale.order", "Sales Order",search=True), # XXX: deprecated
        "date_created": fields.DateTime("Date Created",search=True),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),  # XXX: deprecated
        "promotion_message": fields.Text("Promotion Message"),
        "coupon_code": fields.Char("Coupon Code"),
        "user_id": fields.Many2One("base.user", "Created By"),
        "ip_addr": fields.Char("IP Address",readonly=True,search=True),
        "state": fields.Selection([["draft","Draft"],["confirmed","Confirmed"],["done","Completed"],["canceled","Canceled"]],"Status",required=True),
        "website_id": fields.Many2One("website","Website",required=True,search=True),
        "pricelist_id": fields.Many2One("price.list","Price List"), # TODO: remove this field
        "sale_orders": fields.One2Many("sale.order","related_id","Sales Orders"),
        "display_promotions": fields.Many2Many("sale.promotion", "Display Promotions", function="get_display_promotions"),
        "payments": fields.One2Many("account.payment","related_id","Payments"),
        "pay_method_id": fields.Many2One("payment.method", "Payment Method"),
        "payment_notes": fields.Text("Payment Notes"),
        "is_paid": fields.Boolean("Paid",function="_is_paid"),
        "is_delivered": fields.Boolean("Delivered",function="_is_delivered"),
        "date_confirmed": fields.DateTime("Date Confirmed",search=True),
        "payment_checked": fields.Boolean("Payment Checked"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "ecom_can_cancel": fields.Boolean("Can Cancel", function="get_ecom_can_cancel"),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "stock_exceed": fields.Char("Stock Exceed", function="get_stock_exceed"),
        "ship_tracking": fields.Char("Ship Tracking no.", function="get_tracking"),
        "related_comments": fields.One2Many("message", "related_id", "Comments"),
        "product_id": fields.Many2One("product","Product",store=False,function_search="search_product",search=True),
    }
    _order = "date_created desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="ecom_cart")
        if not seq_id:
            return None
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
        "ship_to_bill": True,
        "accept_marketing": False,
        "date_created": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "draft",
        "number": _get_number,
        "payment_checked": False,
    }

    def search_product(self, clause, context={}):
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        cart_ids = []
        for line in get_model("ecom.cart.line").search_browse([["product_id","in",product_ids]]):
            cart_ids.append(line.cart_id.id)
        cond = [["id","in",cart_ids]]
        return cond

    def copy(self, ids, context={}):
        obj = self.browse(ids[0])
        vals = {
            "website_id": obj.website_id.id,
            "pricelist_id": obj.pricelist_id.id,
            "user_id": access.get_active_user(),
            "contact_id": obj.contact_id.id,
            "email": obj.email,
            "tax_no": obj.tax_no,
            "bill_first_name": obj.bill_first_name,
            "bill_last_name": obj.bill_last_name,
            "bill_company": obj.bill_company,
            "bill_address": obj.bill_address,
            "bill_address2": obj.bill_address2,
            "bill_city": obj.bill_city,
            "bill_country_id": obj.bill_country_id.id,
            "bill_province_id": obj.bill_province_id.id,
            "bill_district_id": obj.bill_district_id.id,
            "bill_subdistrict_id": obj.bill_subdistrict_id.id,
            "bill_postal_code": obj.bill_postal_code,
            "bill_phone": obj.bill_phone,
            "ship_to_bill": obj.ship_to_bill,
            "ship_first_name": obj.ship_first_name,
            "ship_last_name": obj.ship_last_name,
            "ship_company": obj.ship_company,
            "ship_address": obj.ship_address,
            "ship_address2": obj.ship_address2,
            "ship_city": obj.ship_city,
            "ship_country_id": obj.ship_country_id.id,
            "ship_province_id": obj.ship_province_id.id,
            "ship_district_id": obj.ship_district_id.id,
            "ship_subdistrict_id": obj.ship_subdistrict_id.id,
            "ship_postal_code": obj.ship_postal_code,
            "ship_phone": obj.ship_phone,
            "pay_method_id": obj.pay_method_id.id,
            "payment_ref": obj.payment_ref,
            "payment_notes": obj.payment_notes,
            "amount_ship": obj.amount_ship,
            "comments": obj.comments,
            "lines": [],
            "used_promotions": [],
        }
        for line in obj.lines:
            line_vals = {
                "sequence": line.sequence,
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "unit_price": line.unit_price,
                "discount_percent": line.discount_percent,
                "discount_amount": line.discount_amount,
                "promotion_amount": line.promotion_amount,
                "ship_method_id": line.ship_method_id.id,
            }
            vals["lines"].append(("create", line_vals))
        for prom in obj.used_promotions:
            prom_vals = {
                "promotion_id": prom.promotion_id.id,
                "product_id": prom.product_id.id,
                "qty": prom.qty,
                "percent": prom.percent,
                "amount": prom.amount,
                "cond_product_id": prom.cond_product_id.id,
                "cond_qty": prom.cond_qty,
            }
            vals["used_promotions"].append(("create", prom_vals))
        new_id = self.create(vals)
        cart = self.browse(new_id)
        return {
            "next": {
                "name": "ecom_cart",
                "mode": "form",
                "active_id": new_id,
            },
            "cart_id": new_id,
            "flash": "Coppied to cart %s"%cart.number,
        }

    def _get_total_amount(self, ids, context={}):
        print("Cart._get_total_amount")
        vals = {}
        for obj in self.browse(ids):
            subtotal = 0
            for line in obj.lines:
                subtotal += line.amount
            disc=0
            for prom in obj.used_promotions:
                if not prom.product_id and not prom.percent:
                    disc+=prom.amount or 0
            vals[obj.id] = {
                "amount_subtotal": subtotal,
                "amount_discount": disc,
                "amount_total": subtotal + (obj.amount_ship or 0) - disc,
            }
        return vals

    def _get_total_qty(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_qty = 0
            for line in obj.lines:
                total_qty += line.qty
            vals[obj.id] = {
                "total_qty": total_qty,
            }
        return vals

    def _get_total_weight(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_weight = 0
            for line in obj.lines:
                total_weight += (line.product_id.weight or 0) * line.qty
            vals[obj.id] = {
                "total_weight": total_weight,
            }
        return vals

    def get_ship_methods(self, ids, context={}):
        obj = self.browse(ids)[0]
        allowed_ids = get_model("ship.method").search([])
        allowed_ids = set(allowed_ids)
        for line in obj.lines:
            prod = line.product_id
            if prod.ship_methods:
                meth_ids = set([x.id for x in prod.ship_methods])
            else:
                meth_ids = allowed_ids
            if allowed_ids is not None:
                allowed_ids = allowed_ids.intersection(meth_ids)
        total_without_ship = obj.amount_without_ship
        total_weight = obj.total_weight
        methods = {}
        exclude_methods = set()
        for method in get_model("ship.method").search_browse([], order="sequence"):
            if method.id not in allowed_ids:
                continue
            price = None
            for rate in method.rates:
                if rate.country_id and rate.country_id.id != obj.ship_country_id.id:
                    continue
                if rate.province_id and rate.province_id.id != obj.ship_province_id.id:
                    continue
                if rate.district_id and rate.district_id.id != obj.ship_district_id.id:
                    continue
                if rate.postal_code and rate.postal_code != obj.ship_postal_code:
                    continue
                if rate.min_amount and rate.min_amount > total_without_ship:
                    continue
                if rate.min_weight and rate.min_weight > total_weight:
                    continue
                if price is None or rate.ship_price < price:
                    price = rate.ship_price
            if price != None:
                methods[method.id] = {
                    "method_id": method.id,
                    "method_name": method.name,
                    "ship_price": price,
                    "sequence": method.sequence or 0,
                }
                for x in method.exclude_ship_methods:
                    exclude_methods.add(x.id)
        for method_id in exclude_methods:
            if method_id in methods:
                del methods[method_id]
        res = list(methods.values())
        res.sort(key=lambda m: m["sequence"])
        return res

    def copy_to_contact(self, ids, context={}):
        print("Cart.copy_to_contact", ids)
        obj = self.browse(ids[0])
        website = obj.website_id
        categ_id = website.contact_categ_id.id
        cont_vals = {
            "type": "person",
            "first_name": obj.bill_first_name,
            "last_name": obj.bill_last_name,
            "email": obj.email,
            "phone": obj.bill_phone,
            "addresses": [("delete_all",)],
            "categ_id": categ_id,
            "tax_no": obj.tax_no,
            "account_receivable_id": website.account_receivable_id.id,
            "customer" : True,
        }
        addr_vals_bill = {
            "type": "billing",
            "first_name": obj.bill_first_name,
            "last_name": obj.bill_last_name,
            "company": obj.bill_company,
            "address": obj.bill_address,
            "address2": obj.bill_address2,
            "city": obj.bill_city,
            "postal_code": obj.bill_postal_code,
            "country_id": obj.bill_country_id.id,
            "province_id": obj.bill_province_id.id,
            "district_id": obj.bill_district_id.id,
            "subdistrict_id": obj.bill_subdistrict_id.id,
            "phone": obj.bill_phone,
        }
        cont_vals["addresses"].append(("create", addr_vals_bill))
        if obj.ship_to_bill:
            addr_vals_ship=addr_vals_bill.copy()
            addr_vals_ship["type"] = "shipping"
        else:
            addr_vals_ship = {
                "type": "shipping",
                "first_name": obj.ship_first_name,
                "last_name": obj.ship_last_name,
                "company": obj.ship_company,
                "address": obj.ship_address,
                "address2": obj.ship_address2,
                "city": obj.ship_city,
                "postal_code": obj.ship_postal_code,
                "country_id": obj.ship_country_id.id,
                "province_id": obj.ship_province_id.id,
                "district_id": obj.ship_district_id.id,
                "subdistrict_id": obj.ship_subdistrict_id.id,
                "phone": obj.ship_phone,
            }
        cont_vals["addresses"].append(("create", addr_vals_ship))
        res = get_model("contact").search([["email", "=", obj.email], ["categ_id", "=", categ_id]])
        if res:
            cont_id = res[0]
            if context.get('force_write', True): get_model("contact").write([cont_id], cont_vals)
        else:
            cont_id = get_model("contact").create(cont_vals)
            obj.trigger("contact_created")
        obj.write({"contact_id": cont_id})
        return cont_id

    def copy_to_sale(self, ids, context={}): #this copies data to the sales order
        obj = self.browse(ids)[0]
        if obj.state!="draft":
            raise Exception("Invalid cart status")
        website=obj.website_id
        if obj.sale_orders:
            raise Exception("Sales orders already created for this cart")
        if not obj.contact_id:
            raise Exception("Contact not yet created for this order")
        if not obj.bill_address:
            raise Exception("Missing billing address")
        if not obj.bill_postal_code:
            raise Exception("Missing billing postal code")
        if not obj.bill_country_id:
            raise Exception("Missing billing country")
        if not obj.ship_address:
            raise Exception("Missing shipping address")
        if not obj.ship_postal_code:
            raise Exception("Missing shipping postal code")
        if not obj.ship_country_id:
            raise Exception("Missing shipping country")
        bill_addr_vals = {
            "first_name": obj.bill_first_name,
            "last_name": obj.bill_last_name,
            "company": obj.bill_company,
            "address": obj.bill_address,
            "address2": obj.bill_address2,
            "city": obj.bill_city,
            "postal_code": obj.bill_postal_code,
            "country_id": obj.bill_country_id.id,
            "province_id": obj.bill_province_id.id,
            "district_id": obj.bill_district_id.id,
            "subdistrict_id": obj.bill_subdistrict_id.id,
            "phone": obj.bill_phone,
        }
        ship_addr_vals = {
            "first_name": obj.ship_first_name,
            "last_name": obj.ship_last_name,
            "company": obj.ship_company,
            "address": obj.ship_address,
            "address2": obj.ship_address2,
            "city": obj.ship_city,
            "postal_code": obj.ship_postal_code,
            "country_id": obj.ship_country_id.id,
            "province_id": obj.ship_province_id.id,
            "district_id": obj.ship_district_id.id,
            "subdistrict_id": obj.ship_subdistrict_id.id,
            "phone": obj.ship_phone,
        }
        get_model("address").create(bill_addr_vals)
        res=get_model("company").search([["parent_id","=",None]],order="id")
        default_company_id=res[0]
        company_ids=[]
        for line in obj.lines:
            prod=line.product_id
            company_id=prod.sale_company_id.id or prod.company_id.id or default_company_id
            company_ids.append(company_id)
        company_ids=list(set(company_ids))
        res=self.get_shipping_amounts(ids,context=context)
        ship_amounts=res["ship_amounts"]
        seller_ship_amounts={}
        for (seller_id,meth_id),amt in ship_amounts.items():
            seller_ship_amounts.setdefault((seller_id, meth_id) ,0)
            seller_ship_amounts[(seller_id, meth_id)]+=amt
        for sale_company_id in company_ids:
            sale_vals = {
                "company_id": sale_company_id,
                "related_id": "ecom.cart,%d"%obj.id,
                "contact_id": obj.contact_id.id,
                "bill_address_id": get_model("address").create(bill_addr_vals),  # FIXME
                "ship_address_id": get_model("address").create(ship_addr_vals),  # FIXME
                "tax_type": "tax_in",
                "lines": [],
                "used_promotions": [],
                "pay_method_id": obj.pay_method_id.id,
                "ecom_tax_no": obj.tax_no,
                "ecom_tax_branch_no": obj.tax_branch_no,
                "ref": obj.number,
            }
            prods_in_sale = []
            ship_methods = []
            for line in obj.lines:
                prod = line.product_id
                if not prod.locations:
                    raise Exception("Missing product locations for product %s"%prod.code)
                loc_id=prod.locations[0].location_id.id #XXX support multi location ?
                line_company_id=prod.sale_company_id.id or prod.company_id.id or default_company_id
                if line_company_id!=sale_company_id:
                    continue
                desc = line.description or prod.name
                prod_tax_id = None
                if prod.sale_tax_id:
                    prod_tax_id = prod.sale_tax_id.id
                elif prod.parent_id and prod.parent_id.sale_tax_id:
                    prod_tax_id = prod.parent_id.sale_tax_id.id
                #else: #XXX some ICC's product doesn't have VAT
                    #prod_tax_id = website.sale_tax_id.id
                #if not prod_tax_id:
                    #raise Exception("Missing Tax rate in product %s"%prod.code)
                line_vals={
                    "product_id": prod.id,
                    "description": desc,
                    "qty": line.qty,
                    "uom_id": prod.uom_id.id,
                    "unit_price": line.unit_price,
                    "discount": line.discount_percent,
                    "discount_amount": line.discount_amount,
                    "location_id": loc_id,
                    "tax_id": prod_tax_id,
                    "ship_method_id": line.ship_method_id.id,
                }
                sale_vals["lines"].append(("create", line_vals))
                prods_in_sale.append(prod.id) #XXX
                if line.ship_method_id: ship_methods.append(line.ship_method_id)
                if prod.type == "bundle":
                    for comp in prod.components:
                        line_vals={
                            "product_id": comp.component_id.id,
                            "description": "Bundle product of %s"%prod.code,
                            "qty": line.qty*comp.qty,
                            "uom_id": comp.component_id.uom_id.id,
                            "unit_price": 0,
                            #"discount": line.discount_percent,
                            #"discount_amount": line.discount_amount,
                            "location_id": loc_id,
                            #"tax_id": prod_tax_id,
                            "ship_method_id": line.ship_method_id.id,
                        }
                        sale_vals["lines"].append(("create", line_vals))
            if not sale_vals["lines"]:
                raise Exception("Sales order is empty")
            '''
            amt_ship=seller_ship_amounts.get(sale_company_id,0)
            if amt_ship:
                prod=website.ship_product_id
                if not prod:
                    raise Exception("Missing shipping product in website configuration")
                prod_tax_id = None
                if prod.sale_tax_id:
                    prod_tax_id = prod.sale_tax_id.id
                line_vals={
                    "product_id": prod.id,
                    "description": prod.name,
                    "qty": 1,
                    "uom_id": prod.uom_id.id,
                    "unit_price": amt_ship,
                    "tax_id": prod_tax_id,
                }
                if prod.ship_methods:
                    line_vals.update({"ship_method_id": prod.ship_methods[0].id})
                sale_vals["lines"].append(("create", line_vals))
            '''
            for ship_method in ship_methods:
                amt_ship = seller_ship_amounts.get((sale_company_id, ship_method.id), 0)
                if amt_ship:
                    prod = ship_method.ship_product_id
                    tax_id = None
                    if prod.sale_tax_id:
                        tax_id = prod.sale_tax_id.id
                    if not prod: raise Exception("Missing shipping product in website configuration")
                    line_vals={
                        "product_id": prod.id,
                        "description": prod.name,
                        "qty": 1,
                        "uom_id": prod.uom_id.id,
                        "unit_price": amt_ship,
                        "tax_id": tax_id,
                        "ship_method_id": ship_method.id,
                    }
                    if ("create", line_vals) not in sale_vals["lines"]:
                        sale_vals["lines"].append(("create", line_vals))
            for line in obj.used_promotions:
                prom=line.promotion_id
                if prom.company_id.id!=sale_company_id:
                    continue
                if not line.product_id and line.percent: #XXX
                    prods_in_sale = list(set(prods_in_sale))
                    for prod_id in prods_in_sale:
                        prom_vals={
                            "promotion_id": prom.id,
                            "product_id": prod_id,
                            "percent": line.percent,
                        }
                        sale_vals["used_promotions"].append(("create", prom_vals))
                else:
                    prom_vals={
                        "promotion_id": prom.id,
                        "product_id": line.product_id.id,
                        "percent": line.percent,
                        "amount": line.amount,
                    }
                    sale_vals["used_promotions"].append(("create", prom_vals))
            sale_id = get_model("sale.order").create(sale_vals)
            print("sales order created: %s" % sale_id)
            for line in obj.lines:
                prod = line.product_id
                line_company_id=prod.company_id.id or default_company_id
                if line_company_id!=sale_company_id:
                    continue
                for img in line.images:
                    if not website.preview_doc_categ_id.id:
                        raise Exception("Missing document category for product preview images")
                    vals = {
                        "file": img.image,
                        "description": img.name,
                        "related_id": "sale.order,%d" % sale_id,
                        "categ_id": website.preview_doc_categ_id.id,
                    }
                    get_model("document").create(vals)
            print("sales order %s written in cart %s" % (sale_id, obj.id))
            sale = get_model("sale.order").browse(sale_id)
            sale.confirm()
            obj.trigger("order_created")
            sale.copy_to_picking()
            for picking in sale.pickings:
                if picking.type != "out":
                    continue
                picking.pending()

        if obj.pay_method_id.type == "bank":
            if website.payment_slip_template_id:
                data = obj.get_report_data()
                tmpl_name = website.payment_slip_template_id.name
                out = get_report_jasper(tmpl_name, data)  # TODO: support non-jasper templates
                rand = base64.urlsafe_b64encode(os.urandom(8)).decode()
                fname = "payment-slip-%s,%s.pdf" % (obj.number, rand)
                path = utils.get_file_path(fname)
                open(path, "wb").write(out)
                vals = {
                    "file": fname,
                    "related_id": "ecom.cart,%d" % obj.id,
                }
                get_model("document").create(vals)  # save document to be able to include payment slip in email template
            obj.trigger("confirm_bank")
        obj.trigger("confirm")
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        obj.write({"state":"confirmed", "date_confirmed": t})

    def create_new_cart(self,website_id):
        website=get_model("website").browse(website_id)
        vals = {
            "website_id": website_id,
        }
        #if website.sale_channel_id:
            #vals["pricelist_id"]=website.sale_channel_id.pricelist_id.id
        #user_id = access.get_active_user()
        #if user_id:
                #user_id=int(user_id)
                #user=get_model("base.user").browse(user_id)
                #contact = user.contact_id
                #pricelist_ids=[website.sale_channel_id.pricelist_id.id]
                #for group in contact.groups:
                    #if group.sale_price_list_id:
                        #pricelist_ids.append(group.sale_price_list_id.id)
                #vals["pricelist_id"] = pricelist_ids
        cart_id = self.create(vals)
        self.set_default_address([cart_id])
        return cart_id

    def set_default_address(self, ids):
        print("Cart.set_default_address", ids)
        obj = self.browse(ids[0])
        user_id = access.get_active_user()
        if user_id:
            user = get_model("base.user").browse(user_id)
            vals = {
                "email": user.email,
            }
            contact = user.contact_id
            if contact:
                addr = contact.default_address_id
                if addr:
                    vals.update({
                        "bill_first_name": addr.first_name,
                        "bill_last_name": addr.last_name,
                        "bill_company": addr.company,
                        "bill_address": addr.address,
                        "bill_address2": addr.address2,
                        "bill_city": addr.city,
                        "bill_postal_code": addr.postal_code,
                        "bill_country_id": addr.country_id.id,
                        "bill_province_id": addr.province_id.id,
                        "bill_phone": addr.phone,
                        "ship_first_name": addr.first_name,
                        "ship_last_name": addr.last_name,
                        "ship_company": addr.company,
                        "ship_address": addr.address,
                        "ship_address2": addr.address2,
                        "ship_city": addr.city,
                        "ship_postal_code": addr.postal_code,
                        "ship_country_id": addr.country_id.id,
                        "ship_province_id": addr.province_id.id,
                        "ship_phone": addr.phone,
                    })
                if contact.tax_no:
                    vals.update({
                        "tax_no": contact.tax_no,
                    })
                if contact.tax_branch_no:
                    vals.update({
                    "tax_branch_no" : contact.tax_branch_no,
                    })
            obj.write(vals)

    def add_product(self, ids, product_id, description, qty, images):
        print("Cart.add_product", ids, "product_id", product_id, "description", description, "qty", qty, "images", images)
        obj = self.browse(ids)[0]

        #website_id=self.request.headers.get("X-Website-ID")
        #if website_id:
            #website_id=int(website_id)
        #else:
        res=get_model("website").search([["state","=","active"]])
        if not res:
            raise Exception("No website found")
        website_id=res[0]
        self.website_id=website_id
        website=get_model("website").browse(website_id)
        vals = {
            "website_id": website_id,
        }
        
        pricelist_ids=[website.sale_channel_id.pricelist_id.id]
        user_id = access.get_active_user()
        if user_id:
            user_id=int(user_id)
            user=get_model("base.user").browse(user_id)
            contact = user.contact_id
            if contact.groups:
                for group in contact.groups:
                    if group.sale_price_list_id:
                        pricelist_ids.append(group.sale_price_list_id.id)
            vals["pricelist_ids"] = pricelist_ids

        #contact=user.contact_id ...
        #pricelist_ids=[  website pricelist ]
        #pricelist_ids.append(contact.get_price_lists())
        ctx={
            #"pricelist_id": obj.pricelist_id.id, # TODO: remove
            "pricelist_ids": pricelist_ids,# get from contact of user,
        }
        product = get_model("product").browse(product_id,context=ctx)
        master=product.parent_id
        if obj.lines:
            seq = obj.lines[-1].sequence + 1
        else:
            seq = 0
        list_price=product.sale_price or 0
        if not list_price and master:
            list_price=master.sale_price or 0
        amount_before_discount=list_price*qty
        special_price=product.customer_price or 0
        discount_percent=product.customer_discount_percent or 0
        if not special_price and master:
            special_price=master.customer_price or 0
            discount_percent=master.customer_discount_percent or 0
        amount=special_price*qty
        discount_amount=amount_before_discount*(1-discount_percent/Decimal(100))-amount
        vals = {
            "cart_id": obj.id,
            "sequence": seq,
            "product_id": product.id,
            "qty": qty,
            "description": description or product.name,
            "unit_price": list_price,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "image": product.image,
        }
        if master:
            if not vals["description"]:
                vals["description"]=master.name
            if not vals["image"]:
                vals["image"]=master.image
        if images:
            vals["image"] = images[0][1]
        line_id = get_model("ecom.cart.line").create(vals)
        for data, fname in images:
            path = utils.get_file_path(fname)
            open(path, "wb").write(data)
            vals = {
                "line_id": line_id,
                "image": fname,
                "name": fname,  # XXX
            }
            get_model("ecom.cart.line.image").create(vals)
        obj.update_promotions()
        obj.auto_apply_promotions()

    def create_account(self, ids, context={}):
        print("Cart.create_account", ids)
        obj = self.browse(ids[0])
        contact_id = obj.copy_to_contact()
        website = obj.website_id
        res = get_model("base.user").search([["email", "=", obj.email]])
        if res:
            raise Exception("An account already exists for email %s" % obj.email)
        if not website.user_profile_id:
            raise Exception("Missing customer user profile in website settings")
        new_pass = "%.6d" % random.randint(0, 999999)
        names = []
        if obj.bill_first_name:
            names.append(obj.bill_first_name)
        if obj.bill_last_name:
            names.append(obj.bill_last_name)
        vals = {
            "name": " ".join(names),
            "login": obj.email,
            "password": new_pass,
            "email": obj.email,
            "profile_id": website.user_profile_id.id,
            "contact_id": contact_id,
        }
        user_id = get_model("base.user").create(vals)
        get_model("base.user").trigger([user_id],"create_user",context={"password": new_pass})
        return user_id

    def set_ship_method(self, ids, ship_method_id, context={}):
        print("Cart.set_ship_method", ids, ship_method_id)
        obj = self.browse(ids)[0]
        methods = obj.get_ship_methods()
        found = True
        for m in methods:
            if m["method_id"] != ship_method_id:
                continue
            vals = {
                "ship_method_id": ship_method_id,
                "amount_ship": m["ship_price"],
            }
            obj.write(vals)
            found = True
            break
        if not found:
            raise Exception("Invalid shipping emthod")

    def qty_not_available(self, ids, context={}):
        for obj in self.browse(ids):
            prods_qty = []
            for line in obj.lines:
                is_append = True
                if line.variant_id:
                    product_id = line.variant_id.id
                elif line.product_id:
                    product_id = line.product_id.id
                qty = line.qty
                for i, dic in enumerate(prods_qty):
                    if dic['id'] == product_id:
                        prods_qty[i]['qty'] += qty
                        is_append = False
                if is_append:
                    prods_qty.append({'id':product_id,'qty':qty})
            for prod_qty in prods_qty:
                prod = get_model("product").browse(prod_qty['id'])
                if prod_qty['qty'] > prod.stock_qty:
                    return {
                        "product": prod.name,
                        "qty": max(prod.stock_qty,0),
                    }
        return False

    def get_display_promotions(self,ids,context={}):
        obj=self.browse(ids[0])
        cart_prod_ids=set()
        for line in obj.lines:
            prod=line.product_id
            cart_prod_ids.add(prod.id)
            if prod.parent_id:
                cart_prod_ids.add(prod.parent_id.id)
        today=time.strftime("%Y-%m-%d")
        prom_ids=[]
        for prom in get_model("sale.promotion").search_browse([["state","=","active"]]):
            if prom.date_from and today<prom.date_from:
                continue
            if prom.date_to and today>prom.date_to:
                continue
            if prom.contact_groups:
                if not obj.contact_id:
                    continue
                group_ids=[g.id for g in prom.contact_groups]
                in_group=False
                for group in obj.contact_id.groups: 
                    if group.id in group_ids:
                        in_group=True
                        break
                if not in_group:
                    continue
            if prom.buy_products:
                prom_prod_ids=[p.id for p in prom.buy_products]
            elif prom.buy_prod_groups:
                group_ids=[g.id for g in prom.buy_prod_groups]
                prom_prod_ids=get_model("product").search([["groups.id","in",group_ids]])
            else:
                prom_prod_ids=None
            if prom.related_products:
                rel_prod_ids+=[p.id for p in prom.related_products]
            elif prom.display_prod_groups:
                group_ids=[g.id for g in prom.related_prod_groups]
                rel_prod_ids=get_model("product").search([["groups.id","in",group_ids]])
            else:
                rel_prod_ids=None
            if prom_prod_ids and rel_prod_ids:
                prom_prod_ids+=rel_prod_ids
            if prom_prod_ids:
                if not set(prom_prod_ids)&cart_prod_ids:
                    continue
            prom_ids.append(prom.id)
        vals={obj.id:prom_ids}
        return vals

    def can_apply_promotion(self,ids,prom_id):
        print("#"*80)
        print("cart.can_apply_promotion",ids,prom_id)
        obj=self.browse(ids[0])
        today=time.strftime("%Y-%m-%d")
        prom=get_model("sale.promotion").browse(prom_id)
        print("trying promotion '%s'..."%prom.name)
        if prom.contact_groups:
            if not obj.contact_id:
                print("skipped because no contact in cart")
                return
            group_ids=[g.id for g in prom.contact_groups]
            res=get_model("contact").search([["id","=",obj.contact_id.id],["groups.id","in",group_ids]])
            if not res:
                print("skipped because cart contact not in promotion group")
                return
        if prom.date_from and today<prom.date_from:
            print("skipped because of date_from (%s < %s)"%(today,prom.date_from))
            return
        if prom.date_to and today>prom.date_to:
            print("skipped because of date_to (%s > %s)"%(today,prom.date_to))
            return
        for line in obj.used_promotions:
            if line.promotion_id.id==prom.id and not line.cond_product_id:
                print("skipped because promotion already applied on whole order")
                return
        use_qtys={}
        for line in obj.used_promotions:
            prod=line.cond_product_id
            if prod:
                use_qtys.setdefault(prod.id,0)
                use_qtys[prod.id]+=line.cond_qty or 0
            prod=line.product_id
            if prod:
                use_qtys.setdefault(prod.id,0)
                use_qtys[prod.id]+=line.qty or 0
        print("use_qtys",use_qtys)
        buy_qtys={}
        for line in obj.lines:
            prod=line.product_id
            buy_qtys.setdefault(prod.id,0)
            buy_qtys[prod.id]+=line.qty
        print("buy_qtys",buy_qtys)
        avail_qtys={}
        for prod_id,avail_qty in buy_qtys.items():
            avail_qtys[prod_id]=buy_qtys[prod_id]-use_qtys.get(prod_id,0)
        print("avail_qtys",avail_qtys)
        cond_prod_id=None
        if prom.buy_min_qty:
            if prom.buy_products:
                buy_prod_ids=[p.id for p in prom.buy_products]
            elif prom.buy_prod_groups:
                group_ids=[g.id for g in prom.buy_prod_groups]
                buy_prod_ids=get_model("product").search([["groups.id","in",group_ids]])
            else:
                buy_prod_ids=[]
            for prod_id,avail_qty in avail_qtys.items():
                prod=get_model("product").browse(prod_id)
                master_prod=prod.parent_id and prod.parent_id or prod
                if (prod_id in buy_prod_ids or master_prod.id in buy_prod_ids) and avail_qty>=prom.buy_min_qty:
                    cond_prod_id=prod_id
            print("cond_prod_id",cond_prod_id)
            if not cond_prod_id:
                print("skipped, because of min qty")
                return
            avail_qtys[cond_prod_id]-=prom.buy_min_qty
            cond_qty=prom.buy_min_qty
        else:
            cond_qty=None
        print("promotion conditions verified!")
        print("avail_qtys after cond",avail_qtys)
        if prom.discount_products:
            disc_prod_ids=[p.id for p in prom.discount_products]
        elif prom.discount_prod_groups:
            group_ids=[g.id for g in prom.discount_prod_groups]
            disc_prod_ids=get_model("product").search([["groups.id","in",group_ids]])
        else:
            disc_prod_ids=None
        if disc_prod_ids:
            disc_prod_id=None
            for line in obj.lines:
                prod=line.product_id
                master_prod=prod.parent_id and prod.parent_id or prod
                if (prod.id in disc_prod_ids or master_prod.id in disc_prod_ids) and avail_qtys[prod.id]>0:
                    disc_prod_id=prod.id
            print("disc_prod_id",disc_prod_id)
            if not disc_prod_id:
                print("skipped, because no discount product")
                return
            disc_qty=0
            disc_amt=0
            disc_pct=prom.discount_percent_item or 0
            remain_qty=prom.discount_max_qty or 0
            for line in obj.lines:
                prod=line.product_id
                avail_qty=avail_qtys[prod.id]
                if avail_qty<=0:
                    continue
                if prod.id==disc_prod_id:
                    qty=min(line.qty,avail_qty,remain_qty)
                    disc_qty+=qty
                    avail_qtys[prod.id]-=qty
                    remain_qty-=qty
                    if prom.discount_percent_item:
                        price=line.unit_price*(1-(line.discount_percent or Decimal(0))/100)-(line.discount_amount or Decimal(0))/line.qty
                        amt=qty*price*prom.discount_percent_item/100
                    elif prom.discount_amount_item:
                        amt=qty*prom.discount_amount_item
                    disc_amt+=amt
                    if remain_qty<=0:
                        break
            print("disc_qty",disc_qty)
            print("disc_amt",disc_amt)
        else:
            disc_prod_id=None
            disc_qty=None
            disc_amt=0
            disc_pct=None
            if prom.discount_percent_order:
                disc_pct=prom.discount_percent_order
                for line in obj.lines:
                    price=(line.unit_price*(1-(line.discount_percent or Decimal(0))/100)-(line.discount_amount or Decimal(0))/line.qty)
                    price_disc=math.ceil(price*disc_pct/100) # promotion line amount rounding (ICC)
                    disc_amt+=price_disc*line.qty
            elif prom.discount_amount_order:
                disc_amt=prom.discount_amount_order
        if not disc_amt:
            print("skipped, because no discount amount")
            return
        res={
            "cond_prod_id": cond_prod_id,
            "cond_qty": cond_qty,
            "disc_prod_id": disc_prod_id,
            "disc_qty": disc_qty,
            "disc_pct": disc_pct,
            "disc_amt": disc_amt,
        }
        print("=> res",res)
        return res

    def apply_promotion(self,ids,prom_id):
        print("apply_promotion",ids,prom_id)
        obj=self.browse(ids[0])
        today=time.strftime("%Y-%m-%d")
        prom=get_model("sale.promotion").browse(prom_id)
        res=obj.can_apply_promotion(prom.id)
        if not res:
            raise Exception("Failed to apply promotion")
        vals={
            "cart_id": obj.id,
            "promotion_id": prom.id,
            "cond_product_id": res["cond_prod_id"],
            "cond_qty": res["cond_qty"],
            "product_id": res["disc_prod_id"],
            "qty": res["disc_qty"],
            "percent": res["disc_pct"],
            "amount": res["disc_amt"],
        }
        get_model("ecom.cart.promotion").create(vals)

    def apply_promotion_multi(self,ids,prom_id):
        obj=self.browse(ids[0])
        while obj.can_apply_promotion(prom_id):
            obj.apply_promotion(prom_id)

    def unapply_promotion(self,ids,prom_id):
        print("unapply_promotion",ids,prom_id)
        obj=self.browse(ids[0])
        del_ids=[]
        for prom in obj.used_promotions:
            if prom.promotion_id.id==prom_id:
                del_ids.append(prom.id)
        get_model("ecom.cart.promotion").delete(del_ids)

    def is_promotion_applied(self,ids,prom_id):
        obj=self.browse(ids[0])
        for prom in obj.used_promotions:
            if prom.promotion_id.id==prom_id:
                return True
        return False

    def update_promotions(self,ids,context={}):
        print("cart.update_promotions",ids)
        obj=self.browse(ids[0])
        prom_ids=[]
        for line in obj.used_promotions:
            prom_ids.append(line.promotion_id.id)
        prom_ids=list(set(prom_ids))
        for prom_id in prom_ids:
            obj.unapply_promotion(prom_id)
        for prom_id in prom_ids:
            obj.apply_promotion_multi(prom_id)

    def auto_apply_promotions(self,ids,context={}):
        print("cart.auto_apply_promotions",ids)
        obj=self.browse(ids[0])
        for prom in get_model("sale.promotion").search_browse([["state","=","active"],["auto_apply","=",True]]):
            if obj.is_promotion_applied(prom.id):
                continue
            obj.apply_promotion_multi(prom.id)

    def get_shipping_amounts(self,ids,context={}):
        obj=self.browse(ids[0])
        shippings={}
        for line in obj.lines:
            prod=line.product_id
            seller_id=prod.sale_company_id.id or prod.company_id.id
            meth_id=line.ship_method_id.id
            if not meth_id:
                continue
            key=(seller_id,meth_id)
            shippings.setdefault(key,{"amount":0,"weight":0})
            shippings[key]["amount"]+=line.amount
            shippings[key]["weight"]+=line.weight or 0
        ship_total=0
        ship_amounts={}
        for key in shippings.keys():
            seller_id,meth_id=key
            ship_amount=shippings[key]["amount"]
            ship_weight=shippings[key]["weight"]
            price=None
            meth=get_model("ship.method").browse(meth_id)
            for rate in meth.rates:
                if rate.country_id and rate.country_id.id!=obj.ship_country_id.id:
                    continue
                if rate.province_id and rate.province_id.id!=obj.ship_province_id.id:
                    continue
                if rate.district_id and rate.district_id.id!=obj.ship_district_id.id:
                    continue
                if rate.postal_code and rate.postal_code!=obj.ship_postal_code:
                    continue
                if rate.min_amount and ship_amount<rate.min_amount:
                    continue
                if rate.min_weight and ship_weight<rate.min_weight:
                    continue
                price=rate.ship_price or 0
                break
            if price is None:
                raise Exception("No shipping rate found for shipping method '%s' for cart %s"%(meth.name,obj.number))
            ship_amounts[key]=price
            ship_total+=price
        return {
            "ship_amounts": ship_amounts,
            "ship_total": ship_total,
        }

    def calc_shipping(self,ids,context={}):
        obj=self.browse(ids[0])
        res=obj.get_shipping_amounts(context=context)
        obj.write({"amount_ship": res["ship_total"]})

    def cancel_order(self,ids,context={}):
        obj=self.browse(ids[0])
        for sale in obj.sale_orders:
            if not sale.ecom_can_cancel:
                raise Exception("Can not cancel sales order %s" % sale.number)
            for pick in sale.pickings:
                pick.void()
            for inv in sale.invoices:
                if inv.state == "waiting_payment":
                    inv.void()
                else:
                    inv.copy_to_credit_note(context)
            if not sale.invoices:
                sale.void() #XXX ICC don't want to void SO
        user_id = access.get_active_user()
        user = get_model("base.user").browse(user_id)
        comment_vals = {
            "related_id": "ecom.cart,"+str(obj.id),
            "body": "Order canceled by %s (%s)"%(user.login,user.name),
        }
        get_model("message").create(comment_vals)
        obj.write({"state": "canceled"})

    def import_paypal_payment(self, ids, token="", context={}):
        print("IMPORT PAYPAL")
        obj = self.browse(ids[0])
        website=obj.website_id
        meth=website.paypal_method_id
        if not meth:
            raise Exception("Paypal not configured on website")
        if not meth.paypal_user:
            raise Exception("Missing paypal user")
        if not meth.paypal_password:
            raise Exception("Missing paypal password")
        if not meth.paypal_signature:
            raise Exception("Missing paypal signature")
        if not meth.paypal_url:
            raise Exception("Missing paypal server URL")
        if not token:
            raise Exception("Missing Token")
        if meth.paypal_url == "test":
            url = "https://api-3t.sandbox.paypal.com/nvp"
        else:
            url = "https://api-3t.paypal.com/nvp"
        params = {
            "method": "GetExpressCheckoutDetails",
            "TOKEN": token,
            "version": "104.0",
            "user": meth.paypal_user,
            "pwd": meth.paypal_password,
            "signature": meth.paypal_signature,
        }
        try:
            r = requests.get(url, params=params, timeout=100)
            print("URL", r.url)
            trans_details = urllib.parse.parse_qs(r.text)
            print("TRANS DETAILS", trans_details)
        except:
            raise Exception("Failed to get paypal transaction details")

        if meth.paypal_url == "test":
            url = "https://api-3t.sandbox.paypal.com/nvp"
        else:
            url = "https://api-3t.paypal.com/nvp"
        params = {
            "method": "DoExpressCheckoutPayment",
            "TOKEN": token,
            "PAYMENTREQUEST_0_AMT": trans_details["PAYMENTREQUEST_0_AMT"][0],
            "PAYMENTREQUEST_0_CURRENCYCODE": trans_details["PAYMENTREQUEST_0_CURRENCYCODE"][0],
            "PAYMENTREQUEST_0_PAYMENTACTION": "Sale",
            "PAYERID": trans_details["PAYERID"][0],
            "version": "104.0",
            "user": meth.paypal_user,
            "pwd": meth.paypal_password,
            "signature": meth.paypal_signature,
        }
        try:
            r = requests.get(url, params=params, timeout=100)
            print("URL", r.url)
            res = urllib.parse.parse_qs(r.text)
            print("RES", res)
            if res["ACK"][0] not in ("Success", "SuccessWithWarning"):
                raise Exception("Invalid response code")
        except:
            raise Exception("Failed to commit paypal transaction")
        invoice_ids=[]
        for sale in obj.sale_orders:
            inv_id = sale.copy_to_invoice()["invoice_id"]
            inv = get_model("account.invoice").browse(inv_id)
            inv.write({"due_date": sale.date, "date": sale.date})  # XXX
            for line in inv.lines:
                if not line.account_id:
                    if not website.sale_account_id:
                        raise Exception("Missing sale account in website settings")
                    line.write({"account_id": website.sale_account_id.id})
                if not line.tax_id:
                    line.write({"tax_id": website.sale_tax_id.id})
            inv.approve()
            invoice_ids.append(inv.id)
        if not meth.account_id:
            raise Exception("Missing payment method account")
        vals = {
            "contact_id": obj.contact_id.id,
            "type": "in",
            "pay_type": "invoice",
            "account_id": meth.account_id.id,
            "related_id": "ecom.cart,%d"%obj.id,
            "lines": [],
        }
        for inv_id in invoice_ids:
            inv=get_model("account.invoice").browse(inv_id)
            vals["lines"].append(("create",{
                "invoice_id": inv_id,
                "amount": inv.amount_due,
            }))
        pmt_id = get_model("account.payment").create(vals, context={"type": "in"})
        get_model("account.payment").post([pmt_id])
        obj.write({"payment_checked": True})
        obj.set_done()
        for sale in obj.sale_orders:
            if not sale.pickings:
                raise Exception("Missing goods issue for this sales order")
            pick = sale.pickings[0]
            pick.approve()

    def import_scb_payment(self, ids, context={}):
        try:
            print("IMPORT SCB")
            obj = self.browse(ids[0])
            website=obj.website_id
            meth=website.scb_method_id
            if obj.is_paid:
                raise Exception("Payment already made for this cart")
            if not meth:
                raise Exception("SCB gateway not configured on website")
            if not meth.scb_mid:
                raise Exception("Missing SCB merchant ID")
            mid = meth.scb_mid
            if not meth.scb_terminal:
                raise Exception("Missing SCB terminal ID")
            terminal = meth.scb_terminal
            if not meth.scb_url:
                raise Exception("Missing SCB server URL")
            sale_date = time.strptime(obj.date_created, '%Y-%m-%d %H:%M:%S')
            date = time.strftime('%Y%m%d%H%M%S', sale_date)
            data={
                'mid': mid,
                'terminal': terminal,
                'command': 'CRINQ',
                'ref_no': obj.number,
                'ref_date': date,
                'service_id': 10,
                'cur_abbr': 'THB',
                'amount': '%.2f' % obj.amount_total,
            }
            if meth.scb_url == "test":
                url = 'https://nsips-test.scb.co.th:443/NSIPSWeb/NsipsMessageAction.do?'
                r = requests.post(url, data=data, verify=False, timeout=100)
            else:
                url = 'https://nsips.scb.co.th/NSIPSWeb/NsipsMessageAction.do?'
                r = requests.post(url, data=data, timeout=100)
            te = r.text
            print("SCB response: %s"%te)
            p = urllib.parse.parse_qsl(te)
            params = dict(list(map(lambda x: (x[0], x[1]), p)))
            payment_status = params.get('payment_status') or ''
            response_code = params.get('response_code') or ''

            # Inquiry Log
            f = open("scbimport", "a")
            s = "####################################################################" + "\n"
            s += "Order : " + obj.number + "\n"
            s += "Inquiry Date : " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
            s += "Param send to SCB : " + str(data) + "\n"
            s += "Param recieved from SCB : " + te + "\n"
            s += "Payment Status : " + payment_status + "\n"
            s += "Response Code : " + response_code + "\n"
            s += "####################################################################" + "\n"
            f.write(s)
            f.close()

            if payment_status != "002":
                raise Exception("Invalid payment status: %s, response code: %s\n%s" % (payment_status, response_code, s))
            payment_amount = params['amount'] or ''
            payment_amount = Decimal(payment_amount)
            if payment_amount!=obj.amount_total:
                raise Exception("Payment amount is not the same as order amount (%s / %s)" %
                                (payment_amount, obj.amount_total))
            invoice_ids=[]
            for sale in obj.sale_orders:
                sale.copy_to_invoice()
                for inv in sale.invoices:
                    if inv.type != "out":
                        continue
                    if inv.inv_type != "invoice":
                        continue
                    inv = get_model("account.invoice").browse(inv.id)
                    inv.write({"due_date": sale.date, "date": sale.date})  # XXX
                    for line in inv.lines:
                        if not line.account_id:
                            if not website.sale_account_id:
                                raise Exception("Missing sale account in cms settings")
                            line.write({"account_id": website.sale_account_id.id})
                        if not line.tax_id:
                            line.write({"tax_id": website.sale_tax_id.id})
                    inv.approve()
                    invoice_ids.append(inv.id)
            if not meth.account_id:
                raise Exception("Missing payment method account")
            vals = {
                "contact_id": obj.contact_id.id,
                "type": "in",
                "pay_type": "invoice",
                "account_id": meth.account_id.id,
                "related_id": "ecom.cart,%d"%obj.id,
                "lines": [],
            }
            for inv_id in invoice_ids:
                inv=get_model("account.invoice").browse(inv_id)
                vals["lines"].append(("create",{
                    "invoice_id": inv_id,
                    "amount": inv.amount_due,
                }))
            pmt_id = get_model("account.payment").create(vals, context={"type": "in"})
            get_model("account.payment").post([pmt_id])
            obj.write({"payment_checked": True})
            print("IMPORT SCB SUCCESS!!!!")
            print(inv_id)
            print(pmt_id)
            obj.set_done()
            for sale in obj.sale_orders:
                if not sale.pickings:
                    raise Exception("Missing goods issue for this sales order")
                for pick in sale.pickings:
                    if pick.type != "out":
                        continue
                    pick.approve()
        except Exception as e:
            error_message = str(e)
            print(error_message)
            return {
                "next": {
                    "name": "ecom_cart",
                    "mode": "form",
                    "active_id": obj.id,
                },
                "flash": "%s"%error_message,
            }

    def update_paysbuy_method(self, ids, method=""):
        obj=self.browse(ids[0])
        website=obj.website_id
        notes="Paysbuy method: %s"%method
        obj.write({"payment_notes": notes})

    def import_paysbuy_payment(self, ids, context={}):
        try:
            obj = self.browse(ids[0])
            website=obj.website_id
            meth=website.paysbuy_method_id
            if obj.is_paid:
                raise Exception("Payment already made for this cart")
            if not meth:
                raise Exception("Paysbuy not configured on website")
            psbID = meth.paysbuy_id
            if not meth.paysbuy_username:
                raise Exception("Missing paysbuy username")
            username = meth.paysbuy_username
            if not meth.paysbuy_securecode:
                raise Exception("Missing paysbuy secure code")
            secureCode = meth.paysbuy_securecode
            if not meth.paysbuy_url:
                raise Exception("Missing paysbuy server URL")
            if meth.paysbuy_url == "test":
                url = "http://demo.paysbuy.com/psb_ws/getTransaction.asmx/getTransactionByInvoice"
            else:
                url = "https://paysbuy.com/psb_ws/getTransaction.asmx/getTransactionByInvoice"
            data = {
                "psbID": psbID,
                "biz": username,
                "secureCode": secureCode,
                "invoice": obj.number,
            }
            try:
                r = requests.post(url, data=data, timeout=100)
                print("URL", r.url)
                res = r.text.encode(encoding="utf-8")
                parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
                tree = etree.fromstring(res, parser)
                val = tree.getchildren()[0].getchildren()
                res = {}
                for item in val:
                    tag = item.tag[21:]
                    val = item.text
                    res[tag] = val
                # XXX
                # TODO: Need for checking whether it's succeeded or not
                print("Paysbuy param =============>")
                f = open("paysbuyimport", "a")
                s = "####################################################################" + "\n"
                s += "Order : " + obj.number + "\n"
                s += "Inquiry Date : " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
                s += "Param send to Paysbuy : " + str(data) + "\n"
                s += "Param recieved from Paysbuy : " + str(res) + "\n"
                s += "####################################################################" + "\n"
                f.write(s)
                f.close()
            except:
                raise Exception("Failed to check paysbuy transaction")

            if res['result'] == "02":
                raise Exception("Payment under process (paysbuy counter-service) response code: %s" % res['result'])

            if res['result'] != "00":
                raise Exception("Invalid payment response code: %s" % res['result'])

            payment_amount = Decimal(res['amt'])
            if payment_amount!=obj.amount_total:
                raise Exception("Payment amount is not the same as order amount (%s / %s)" %
                                (payment_amount, obj.amount_total))

            if 'method' in res and res['method'] is not None:
                obj.update_paysbuy_method(res['method'])

            invoice_ids=[]
            for sale in obj.sale_orders:
                sale.copy_to_invoice()
                for inv in sale.invoices:
                    if inv.type != "out":
                        continue
                    if inv.inv_type != "invoice":
                        continue
                    inv = get_model("account.invoice").browse(inv.id)
                    inv.write({"due_date": sale.date, "date": sale.date})  # XXX
                    for line in inv.lines:
                        if not line.account_id:
                            if not website.sale_account_id:
                                raise Exception("Missing sale account in cms settings")
                            line.write({"account_id": website.sale_account_id.id})
                        if not line.tax_id:
                            line.write({"tax_id": website.sale_tax_id.id})
                    inv.approve()
                    invoice_ids.append(inv.id)
            if not meth.account_id:
                raise Exception("Missing payment method account")
            vals = {
                "contact_id": obj.contact_id.id,
                "type": "in",
                "pay_type": "invoice",
                "account_id": meth.account_id.id,
                "related_id": "ecom.cart,%d"%obj.id,
                "lines": [],
            }
            for inv_id in invoice_ids:
                inv=get_model("account.invoice").browse(inv_id)
                vals["lines"].append(("create",{
                    "invoice_id": inv_id,
                    "amount": inv.amount_due,
                }))
            pmt_id = get_model("account.payment").create(vals, context={"type": "in"})
            get_model("account.payment").post([pmt_id])
            obj.write({"payment_checked": True})
            obj.set_done()
            for sale in obj.sale_orders:
                if not sale.pickings:
                    raise Exception("Missing goods issue for this sales order")
                for pick in sale.pickings:
                    if pick.type != "out":
                        continue
                    pick.approve()
        except Exception as e:
            error_message = str(e)
            print(error_message)
            return {
                "next": {
                    "name": "ecom_cart",
                    "mode": "form",
                    "active_id": obj.id,
                },
                "flash": "%s"%error_message,
            }

    def _is_paid(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            paid_amt=0
            for sale in obj.sale_orders:
                for inv in sale.invoices:
                    if inv.state=="paid":
                        paid_amt+=inv.amount_total
            vals[obj.id]=paid_amt>=obj.amount_total
            if obj.amount_total ==0:
                vals[obj.id]= 0
        print (vals)
        return vals

    def _is_delivered(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            is_delivered=True
            for sale in obj.sale_orders:
                if not sale.pickings:
                    is_delivered=False
                for pick in sale.pickings:
                    if pick.state!="done":
                        is_delivered=False
            vals[obj.id]=is_delivered
        return vals

    def get_amount_total_words(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            amount_total_words = th_utils.num2word(float(obj.amount_total))
            vals[obj.id] = amount_total_words
            return vals

    def void(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "canceled"})
            obj.trigger("cart_cancelled")

    def set_done(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "done"})
            obj.trigger("payment_paid")

    def get_ecom_can_cancel(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            can = False
            for sale in obj.sale_orders:
                can = sale.state == "confirmed" and not sale.is_paid
                for pick in sale.pickings:
                    if pick.state == "done":
                        can = False
                        break
            vals[obj.id] = can
        return vals

    def ecom_cancel_cart(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.ecom_can_cancel:
            raise Exception("Can not cancel cart %s" % obj.number)
        for sale in obj.sale_orders:
            for pick in sale.pickings:
                pick.void()
            for inv in sale.invoices:
                if inv.state == "waiting_payment":
                    inv.void()
                else:
                    inv.copy_to_credit_note(context)
            if not sale.invoices:
                sale.void() #XXX ICC don't want to void SO
        user_id = access.get_active_user()
        user = get_model("base.user").browse(user_id)
        comment_vals = {
            "related_id": "ecom.cart,"+str(obj.id),
            "body": "Order canceled by %s (%s)"%(user.login,user.name),
        }
        get_model("message").create(comment_vals)
        obj.void()
        obj.trigger("cart_cancel")

    def get_stock_exceed(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            exd_string = ""
            prod_lines = []
            for line in obj.lines:
                is_append = True
                for prod in prod_lines:
                    if prod["id"] == line.product_id.id:
                        prod["qty"] += line.qty
                        is_append = False
                if is_append:
                    prod_lines.append({
                        "id": line.product_id.id,
                        "qty": line.qty,
                    })
            for line in prod_lines:
                prod = get_model("product").browse(line["id"])
                if line["qty"] > prod.stock_qty:
                    exd_string += "Can not purchase product %s more than %d<br>"%(prod.name, prod.stock_qty)
            vals[obj.id] = exd_string
        return vals

    def get_tracking(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            track_nos = []
            for sale in obj.sale_orders:
                for pick in sale.pickings:
                    if pick.ship_tracking:
                        track_nos.append(pick.ship_tracking)
            track_str = ",".join(track_nos)
            vals[obj.id] = track_str
        return vals

Cart.register()
