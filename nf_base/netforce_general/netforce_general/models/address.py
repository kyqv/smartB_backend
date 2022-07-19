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
from netforce import access

class Address(Model):
    _name = "address"
    _name_field = "address_text"
    _export_field = "address"
    _fields = {
        "type": fields.Selection([["billing", "Billing"], ["shipping", "Shipping"], ["mailing", "Mailing"], ["reporting", "Reporting"], ["other", "Other"]], "Address Type"),
        "first_name": fields.Char("First Name", translate=True),
        "last_name": fields.Char("Last Name", translate=True),
        "company": fields.Char("Company", translate=True),
        "unit_no": fields.Char("Unit No"),  # XXX: not used any more
        "floor": fields.Char("Floor"),  # XXX: not used any more
        "bldg_name": fields.Char("Bldg Name"),  # XXX: not used any more
        "bldg_no": fields.Char("Bldg No"),  # XXX: not used any more
        "village": fields.Char("Village"),  # XXX: not used any more
        "soi": fields.Char("Soi"),  # XXX: not used any more
        "moo": fields.Char("Moo"),  # XXX: not used any more
        "street": fields.Char("Street", size=256),  # XXX: not used any more
        "sub_district": fields.Char("Sub-district"),  # XXX: not used any more
        "district": fields.Char("District"),  # XXX: not used any more
        "address": fields.Char("Address", size=1024, required=True, translate=True),
        "address2": fields.Char("Address2", size=256, translate=True),
        "city": fields.Char("City", translate=True),
        "postal_code": fields.Char("Postal Code"),
        "province": fields.Char("Province"),  # XXX: deprecated
        "province_id": fields.Many2One("province", "Province"),
        "district_id": fields.Many2One("district", "District"),
        "subdistrict_id": fields.Many2One("subdistrict", "Subdistrict"),
        "country_id": fields.Many2One("country", "Country"),
        "phone": fields.Char("Phone"),
        "fax": fields.Char("Fax"),
        "contact_id": fields.Many2One("contact", "Contact"),  # XXX: use reference?
        "settings_id": fields.Many2One("settings", "Settings"),
        "lead_id": fields.Many2One("sale.lead", "Lead"),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "related_id": fields.Reference([], "Related To"),
        "address_text": fields.Text("Address Text", function="get_address_text"),
        "sequence": fields.Decimal("Sequence"),
        "company_id": fields.Many2One("company","Company"),
        "comments": fields.Text("Comments"),
        "coords": fields.Char("Coordinates"),
        "mobile": fields.Char("Mobile"),
        "name": fields.Char("Address Name"),
        "contact_name": fields.Char("Contact Name"),
        "is_active_company_address": fields.Boolean("Is Active Company Address",store=False,function_search="search_company_address"),
    }
    _defaults={
        "company_id": lambda *a: access.get_active_company(),
    }
    _order="sequence,id"

    def get_address_text(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            lines = []
            comps = []
            if obj.first_name:
                comps.append(obj.first_name)
            if obj.last_name:
                comps.append(obj.last_name)
            if comps:
                lines.append(" ".join(comps))
            if obj.company:
                lines.append(obj.company)
            if obj.address:
                lines.append(obj.address)
            if obj.address2:
                lines.append(obj.address2)
            comps = []
            if obj.city:
                comps.append(obj.city)
            if obj.subdistrict_id:
                comps.append(obj.subdistrict_id.name)
            if obj.district_id:
                comps.append(obj.district_id.name)
            if obj.province_id:
                comps.append(obj.province_id.name)
            if obj.postal_code:
                comps.append(obj.postal_code)
            #if obj.country_id:
            #    comps.append(obj.country_id.name)
            if comps:
                lines.append(", ".join(comps))
            s = "\n".join(lines)
            vals[obj.id] = s
        return vals

    def name_get(self, ids, context={}):
        vals = self.get_address_text(ids)
        return list(vals.items())

    def name_search(self, name, condition=[], limit=None, context={}):
        cond=[]
        cond.append(["or",["address","ilike",name],["address2","ilike",name]])
        cond.append(condition)
        ids = self.search(cond, limit=limit)
        return self.name_get(ids, context)

    def search_company_address(self, clause, context={}):
        company_id=access.get_active_company()
        comp=get_model("company").browse(company_id)
        return [["contact_id","=",comp.contact_id.id]]

Address.register()
