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
from netforce import utils
from datetime import *
from dateutil.relativedelta import relativedelta
import time
from netforce import config
from netforce import database
from pprint import pprint
from netforce.access import get_active_company, get_active_user, set_active_user, set_active_company
from netforce.utils import get_file_path
from netforce import access
from decimal import *
import json


class FulfillmentBill(Model):
    _name = "fulfillment.bill"
    _string = "Fulfillment Billing"
    #_audit_log = True
    _key = ["contact_id", "month"]
    _name_field = "number"
    _multi_company = True
    _content_search = True
    _fields = {
        "number": fields.Char("Number", search=True),
        "ref": fields.Char("Ref", size=1024, search=True),
        "memo": fields.Char("Memo", size=1024, search=True),
        "contact_id": fields.Many2One("contact", "Contact", required=True, search=True),
        "date": fields.Date("Date", required=True, search=True),
        "currency_id": fields.Many2One("currency", "Currency", required=True, search=True),
        "state": fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed"), ("voided", "Voided")], "Status", search=True),
        "lines": fields.One2Many("fulfillment.bill.line", "fulfillment_id", "Lines"),
        #"amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True, store=True),
        "amount_total": fields.Decimal("Total", function="get_amount_total"),
        "qty_total": fields.Decimal("Total Quantity", function="get_qty_total"),
        "currency_rate": fields.Decimal("Currency Rate", scale=6),
        "related_id": fields.Reference([["account.invoice","Account Invoice"],["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["production.order","Production Order"], ["project", "Project"], ["job", "Service Order"], ["service.contract", "Service Contract"]], "Related To"),
        "company_id": fields.Many2One("company", "Company"),
        #"amount_discount": fields.Decimal("Discount", function="get_discount",function_multi=True),
        #"amount_subtotal_no_discount": fields.Decimal("Subtotal Before Discount", function="get_discount",function_multi=True),
        "bill_address_id": fields.Many2One("address", "Billing Address"),
        "sequence_id": fields.Many2One("sequence", "Sequence"),
        #"month": fields.Char("Month", sql_function=["month", "date"]),
        "month": fields.Selection([["1","January"],["2","February"],["3","March"],["4","April"],["5","May"],["6","June"],["7","July"],["8","August"],["9","September"],["10","October"],["11","November"],["12","December"]],"Month", required=True),
        "year" : fields.Integer("Year", required=True),
        "user_id": fields.Many2One("base.user", "Owner", search=True),
        "remarks": fields.Text("Remarks"),
    }
    #_order = "number desc,date desc,id desc"
    _order = "date desc,number desc,id desc" #Chin: 20201016

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(model="fulfillment.bill")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)
    
    def _get_month(self,context={}):
        now = datetime.now()
        return now.month-1 # previous month

    def _get_year(self,context={}):
        now = datetime.now()
        return now.year

    _defaults = {
        "state": "draft",
        "currency_id": _get_currency,
        "number": _get_number,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
        "user_id": lambda *a: get_active_user(),
        "month": _get_month,
        "year": _get_year,
    }

    def generate_bill_all(self,ids,context={}):
        for bill in self.browse(ids):
           self.generate_bill(ids,bill=bill)

    def generate_bill(self,ids,context={},bill=None):
        if not bill:
            bill = self.browse(ids[0])
        contact_id = bill.contact_id.id
        year = int(bill.year)
        month = int(bill.month)
        start_date = date(year,month,1)
        end_date = date(year,month+1,1)-timedelta(days=1) # end of previous month
        
        def get_data(contact=contact_id,pick_type=None,start=start_date,end=end_date):
            db = database.get_connection()
            q = " SELECT pf.product_id, SUM(sm.qty) qty, pf.uom_id, pf.unit_price, SUM(sm.qty)*pf.unit_price amount " \
                " FROM stock_move sm " \
                " LEFT JOIN product p ON sm.product_id=p.id " \
                " LEFT JOIN stock_picking sp ON sp.id=sm.picking_id " \
                " RIGHT JOIN product_fulfillment pf ON p.id=pf.fulfillment_product_id " \
                " WHERE true "
            if pick_type:
                q += f" AND sp.type='{pick_type}' AND pf.type='{pick_type}' "
            else:
                q += " AND sp.type=pf.type " 
            if contact:
                q += f" AND sm.contact_id='{contact}' "
            if start and end:
                q += f" AND sm.date BETWEEN '{start} 'AND '{end}' "
            q += " GROUP BY pf.product_id, pf.uom_id, pf.unit_price LIMIT NULL"
            res = db.query(q)
            print(res)
            return res
        
        #inbound = get_data(pick_type="in")
        #outbound = get_data(pick_type="out")
        data = get_data()
        for vals in data:
            vals["fulfillment_id"]=ids[0]
            prod_id = vals["product_id"]
            prod = get_model("product").browse(prod_id)
            vals["description"] = prod.description
            get_model("fulfillment.bill.line").create(vals) 

    def to_confirm(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.state not in ("draft"):
                raise Exception("Invalid billing state")
            obj.write({"state": "confirmed"})
            # add feature 
            # => auto-email billing to clients 

    def search_product(self, clause, context={}):
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        invoice_ids = []
        for line in get_model("account.invoice.line").search_browse([["product_id","in",product_ids]]):
            invoice_ids.append(line.invoice_id.id)
        cond = [["id","in",invoice_ids]]
        return cond

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            name = obj.number
            vals.append((obj.id, name))
        return vals

    """
    def submit_for_approval(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state != "draft":
                raise Exception("Invalid state")
            obj.write({"state": "waiting_approval"})
        self.trigger(ids, "submit_for_approval")
        return {
            "flash": "Invoice submitted for approval."
        }


    def approve_async(self, ids, context={}):
        user_id=access.get_active_user()
        company_id=access.get_active_company()
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "account.invoice",
            "method": "approve",
            "user_id": user_id,
            "company_id": company_id,
            "args": json.dumps({
                "ids": ids,
            }),
        }
        get_model("bg.task").create(vals)
    """
    
    def void(self, ids, context={}):
        print("fulfillment.bill.void", ids)
        obj = self.browse(ids)[0]
        if obj.state not in ("draft", "confirmed"):
            raise Exception("Invalid billing state")
        obj.write({"state": "voided"})

    def to_draft(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "draft"})

    def get_qty_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            total_qty = sum([line.qty or 0 for line in obj.lines])
            print("total_qty %s" % total_qty)
            res[obj.id] = total_qty  #{"qty_total":total_qty}
        return res

    def get_amount_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            total_amt = sum([line.amount or 0 for line in obj.lines])
            print("total_amt %s" % total_amt)
            res[obj.id] = total_amt  #{"amount_total":total_amt}
        return res

    def onchange_contact(self, context):
        data = context["data"]
        contact_id = data.get("contact_id")
        if not contact_id:
            return {}
        contact = get_model("contact").browse(contact_id)
        data["bill_address_id"] = contact.get_address(pref_type="billing")
        if contact.currency_id:
            data["currency_id"] = contact.currency_id.id
        else:
            settings = get_model("settings").browse(1)
            data["currency_id"] = settings.currency_id.id
        return data

    def onchange_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data,path,parent=True) 
        prod_id = line.get("product_id")
        if not prod_id:
            return data
        product = get_model("product").browse(prod_id)
        line["uom_id"] = product.uom_id.id
        line["description"] = product.description
        line["qty"] = 1
        return data

    def onchange_unit_price(self, context): 
        data = context["data"]
        path = context["path"]
        line = get_data_path(data,path,parent=True)
        qty = line.get("qty")
        unit_price = line.get("unit_price")
        if not qty or not unit_price:
            return data
        line["amount"] = qty*unit_price
        return data

    """ #future use
    def get_discount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            subtotal=0
            disc = 0
            for line in obj.lines:
                subtotal+=(line.qty or 1)*(line.unit_price or 0)
                disc += (line.amount_discount or 0)
            vals[obj.id] = {
                "amount_subtotal_no_discount": subtotal,
                "amount_discount": disc,
            }
        return vals
    """
    
    """ #future use
    def get_amount_total_words(self,ids,context={}):
        vals={}
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
    """

    def copy_to_cust_invoice(self, ids, context={}):
        obj = self.browse(ids)[0]
        res=get_model("company").search([["contact_id","=",obj.contact_id.id]])
        if not res:
            raise Exception("Company not found for contact %s"%obj.contact_id.name)
        inv_company_id=res[0]
        related_id="%s,%s"%(obj.related_id._model,obj.related_id.id) if obj.related_id else None
        inv_type = "invoice" # for MMC, copying to invoice
        inv_vals = {
            "type": "in",
            "inv_type": inv_type,
            "ref": obj.ref,
            "contact_id": obj.contact_id.id,
            "currency_id": obj.currency_id.id,
            "memo": obj.memo,
            "lines": [],
            "company_id": inv_company_id,
            "related_id": related_id,
        }
        company_id=access.get_active_company()
        access.set_active_company(inv_company_id)
        for line in obj.lines:
            prod=line.product_id
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "amount": line.amount,
                "related_id": related_id,
            }
            inv_vals["lines"].append(("create", line_vals))
        acc_inv = get_model("account.invoice")
        inv_id = acc_inv.create(inv_vals, context={"type": "out", "inv_type": inv_type})
        inv = acc_inv.browse(inv_id)
        access.set_active_company(company_id)
        return {
            "flash": "Fulfillment bill %s successfully copied to Invoice as  %s"%(obj.number, inv.number),
        }
    
    """ #future use
    def copy_to_sale(self,ids,context={}):
        obj=self.browse(ids[0])
        vals={
            "contact_id": obj.contact_id.id,
            "ref": obj.number,
            "lines": [],
        }
        for line in obj.lines:
            line_vals={
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
            }
            vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(vals)
        sale=get_model("sale.order").browse(sale_id)
        return {
            "alert": "Sales order %s created"%sale.number,
            "next": {
                "name": "sale",
                "model": "form",
                "active_id": sale_id,
            },
        }
     """

FulfillmentBill.register()
