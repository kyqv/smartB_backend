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
from netforce.database import get_connection
import time
from datetime import *
from pprint import pprint
from netforce import database
from netforce.utils import get_file_path
from . import utils


def get_months(num_months):
    months = []
    d = date.today()
    m = d.month
    y = d.year
    months.append((y, m))
    for i in range(num_months - 1):
        if (m > 1):
            m -= 1
        else:
            m = 12
            y -= 1
        months.append((y, m))
    return reversed(months)


class ReportPurchase(Model):
    _name = "report.purchase"
    _store = False

    def purchases_per_month(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT to_char(date,'YYYY-MM') AS month,SUM(amount_total_cur) as amount FROM purchase_order WHERE state in ('confirmed','done') GROUP BY month")
        amounts = {}
        for r in res:
            amounts[r.month] = r.amount
        data = []
        months = get_months(6)
        for y, m in months:
            amt = amounts.get("%d-%.2d" % (y, m), 0)
            d = date(year=y, month=m, day=1)
            data.append((d.strftime("%B"), amt))
        return data

    def purchases_per_product(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT p.name,SUM(l.amount_cur) as amount FROM purchase_order_line l,purchase_order o,product p WHERE p.id=l.product_id AND o.id=l.order_id AND o.state in ('confirmed','done') GROUP BY p.name ORDER BY amount DESC")
        data = []
        for r in res[:5]:
            data.append((r.name, r.amount))
        amt = 0
        for r in res[5:]:
            amt += r.amount
        if amt > 0:
            data.append(("Other", amt))
        return data

    def purchases_per_product_categ(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT c.name,SUM(l.amount_cur) as amount FROM purchase_order_line l,purchase_order o,product p,product_categ c,m2m_product_product_categ r WHERE r.product_categ_id=c.id and r.product_id=p.id AND p.id=l.product_id AND o.id=l.order_id AND o.state in ('confirmed','done') GROUP BY c.name ORDER BY amount DESC")
        data = []
        for r in res[:5]:
            data.append((r.name, r.amount))
        amt = 0
        for r in res[5:]:
            amt += r.amount
        if amt > 0:
            data.append(("Other", amt))
        return data

    def purchases_per_supplier(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT p.name,SUM(o.amount_total_cur) as amount FROM purchase_order o,contact p WHERE p.id=o.contact_id AND o.state in ('confirmed','done') GROUP BY p.name ORDER BY amount DESC")
        data = []
        for r in res[:5]:
            data.append((r.name, r.amount))
        amt = 0
        for r in res[5:]:
            amt += r.amount
        if amt > 0:
            data.append(("Other", amt))
        return data

    def get_data_purchase_form(self, context={}):
        obj_id = int(context["refer_id"])
        obj = get_model("purchase.order").browse(obj_id)
        dbname = database.get_active_db()
        settings = get_model("settings").browse(1)
        comp_name = settings.name
        comp_phone = settings.phone
        comp_fax = settings.fax
        comp_addr = settings.get_address_str()
        comp_tax_no = settings.tax_no
        contact = obj.contact_id
        cust_name = contact.name
        cust_fax = contact.fax
        cust_phone = contact.phone
        cust_tax_no = contact.tax_no
        cust_addr = contact.get_address_str()
        data = {
            "comp_name": comp_name,
            "comp_addr": comp_addr,
            "comp_phone": comp_phone or "-",
            "comp_fax": comp_fax or "-",
            "comp_tax_no": comp_tax_no or "-",
            "cust_name": cust_name,
            "cust_addr": cust_addr,
            "cust_phone": cust_phone or "-",
            "cust_fax": cust_fax or "-",
            "cust_tax_no": cust_tax_no or "-",
            "date": obj.date or "-",
            "number": obj.number or "-",
            "ref": obj.ref or "-",
            "delivery_date": obj.delivery_date or "-",
            "ship_method": obj.ship_method_id.name or "-",
            "payment_terms": obj.payment_terms or "-",
            "lines": [],
        }
        index = 0
        for line in obj.lines:
            if line.tax_id:
                break
            index += 1
        if not index:
            tax_rate = obj.lines[index].tax_id.rate
            tax_rate = tax_rate and tax_rate or "0"
        else:
            tax_rate = "0"

        if settings.logo:
            data["logo"] = get_file_path(settings.logo)
        for line in obj.lines:
            data["lines"].append({
                "code": line.product_id.code,
                "description": line.description,
                "qty": line.qty,
                "uom": line.uom_id.name,
                "unit_price": line.unit_price,
                "tax_rate": line.tax_id.rate,
                "amount": line.amount,
            })
        data.update({
            "amount_subtotal": obj.amount_subtotal,
            "amount_tax": obj.amount_tax,
            "amount_total": obj.amount_total,
            "amount_total_words": utils.num2word(obj.amount_total),
            "currency_code": obj.currency_id.code,
            "tax_rate": int(tax_rate),
            "qty_total": obj.qty_total
        })
        return data

    def get_purchase_form_template(self, context={}):
        obj = get_model("purchase.order").browse(int(context["refer_id"]))
        if obj.state == "draft":
            return "rfq_form"
        else:
            return "purchase_form"

ReportPurchase.register()
