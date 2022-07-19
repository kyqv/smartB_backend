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
from netforce.utils import get_file_path
from netforce.access import get_active_company


class ReportStock(Model):
    _name = "report.stock"
    _store = False

    def get_data_pick_internal_form(self, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        obj_id = int(context["refer_id"])
        obj = get_model("stock.picking").browse(obj_id)
        settings = get_model("settings").browse(1)
        comp_addr = settings.get_address_str()
        comp_name = comp.name
        comp_phone = settings.phone
        comp_fax = settings.fax
        comp_tax_no = settings.tax_no
        contact = obj.contact_id
        cust_addr = contact.get_address_str()
        cust_name = contact.name
        cust_fax = contact.fax
        cust_phone = contact.phone
        cust_tax_no = contact.tax_no

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
            "date": obj.date,
            "number": obj.number,
            "ref": obj.ref,
            "lines": [],
        }
        if settings.logo:
            data["logo"] = get_file_path(settings.logo)
        for line in obj.lines:
            data["lines"].append({
                "product": line.product_id.name,
                "description": line.product_id.description,
                "qty": line.qty,
                "uom": line.uom_id.name,
                "location_from": line.location_from_id.name,
                "location_to": line.location_to_id.name,
                "cost_price": line.cost_price,
            })
        return data

    def get_data_pick_form(self, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        obj_id = int(context["refer_id"])
        obj = get_model("stock.picking").browse(obj_id)
        settings = get_model("settings").browse(1)
        comp_addr = settings.get_address_str()
        comp_name = comp.name
        comp_phone = settings.phone
        comp_fax = settings.fax
        comp_tax_no = settings.tax_no
        contact = obj.contact_id
        if contact:
            cust_addr = contact.get_address_str()
            cust_name = contact.name
            cust_fax = contact.fax
            cust_phone = contact.phone
            cust_tax_no = contact.tax_no
        else:
            cust_addr = "-"
            cust_name = "-"
            cust_fax = "-"
            cust_phone = "-"
            cust_tax_no = "-"
        payment_terms = ""
        related_id = ""
        if obj.related_id:
            payment_terms = obj.related_id.payment_terms
            related_id = obj.related_id.number
        data = {
            "comp_name": comp_name,
            "comp_addr": comp_addr,
            "comp_phone": comp_phone or "-",
            "comp_fax": comp_fax or "-",
            "comp_tax_no": comp_tax_no or "-",
            "cust_name": cust_name,
            "cust_addr": cust_addr,
            "cust_phone": cust_phone,
            "cust_fax": cust_fax,
            "cust_tax_no": cust_tax_no,
            "date": obj.date,
            "number": obj.number,
            "ref": obj.ref,
            "qty_total": obj.qty_total,
            "payment_terms": payment_terms or "-",
            "related_id": related_id or "-",
            "lines": [],
        }
        if settings.logo:
            data["logo"] = get_file_path(settings.logo)
        for line in obj.lines:
            data["lines"].append({
                "product": line.product_id.name,
                "code": line.product_id.code,
                "description": line.product_id.description,
                "qty": line.qty,
                "uom": line.uom_id.name,
                "location_from": line.location_from_id.name,
                "location_to": line.location_to_id.name,
                "cost_price": line.cost_price,
                "serial_no": line.serial_no,
            })
        return data

    def get_template_pick_form(self, context={}):
        obj = get_model("stock.picking").browse(int(context["refer_id"]))
        if obj.type == "in":
            return "pick_in_form"
        elif obj.type == "out":
            return "pick_out_form"

    def get_template_pick_internal_form(self, context={}):
        obj = get_model("stock.picking").browse(int(context["refer_id"]))
        if obj.type == "internal":
            return "pick_internal_form"
ReportStock.register()
