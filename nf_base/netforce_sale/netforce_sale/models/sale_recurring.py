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
from netforce import access
from datetime import *
import time


class SaleRec(Model):
    _name = "sale.recurring"
    _string = "Recurring Sales"
    _audit_log = True
    _multi_company = True
    _fields = {
        "contact_id": fields.Many2One("contact", "Contact", required=True, search=True),
        "description": fields.Text("Description", search=True, required=True),
        "product_id": fields.Many2One("product","Product",search=True),
        "qty": fields.Decimal("Qty",required=True),
        "unit_price": fields.Decimal("Unit Price",required=True),
        "amount": fields.Decimal("Amount",function="get_amount"),
        "supplier_id": fields.Many2One("contact","Supplier",condition=[["supplier","=",True]]),
        "interval_num": fields.Integer("Interval Number",required=True),
        "interval_unit": fields.Selection([["day","Day"],["month","Month"],["year","Year"]],"Interval Unit",search=True,required=True),
        "next_date": fields.Date("Next Date",search=True,required=True),
        "active": fields.Boolean("Active"),
        "company_id": fields.Many2One("company","Company"),
    }
    _order="next_date"
    _defaults={
        "active": True,
        "company_id": lambda *a: access.get_active_company(),
    }

    def get_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.qty or 0)*(obj.unit_price or 0)
        return vals

    def send_reminders(self,days_before=None,from_addr=None,to_addrs=None,context=None):
        if not days_before:
            return
        if not to_addrs:
            return
        today=datetime.today().strftime("%Y-%m-%d")
        from_d=(datetime.today().date()+timedelta(days=days_before)).strftime("%Y-%m-%d")
        ids1=self.search([["next_date","<=",from_d],["next_date",">",today]])
        if ids1:
            vals={
                "type": "out",
                "from_addr": from_addr or "donotreply@netforce.com",
                "to_addrs": to_addrs,
                "subject": "Reminder: %d subscriptions expiring soon"%len(ids1),
                "state": "to_send",
            }
            body="<pre>"
            for obj in self.browse(ids1):
                body+="%s %s %s\n"%(obj.next_date,obj.contact_id.name,obj.description)
                body+="="*80+"\n"
            body+="</pre>"
            vals["body"]=body
            get_model("email.message").create(vals)
        ids2=self.search([["next_date","<=",today]])
        if ids2:
            vals={
                "type": "out",
                "from_addr": from_addr or "donotreply@netforce.com",
                "to_addrs": to_addrs,
                "subject": "URGENT Reminder: %d subscriptions expired"%len(ids2),
                "state": "to_send",
            }
            body="<pre>"
            for obj in self.browse(ids2):
                body+="%s %s %s\n"%(obj.next_date,obj.contact_id.name,obj.description)
                body+="="*80+"\n"
            body+="</pre>"
            vals["body"]=body
            get_model("email.message").create(vals)
        get_model("email.message").send_emails_async()
        return "%d expiring soon, %d expired"%(len(ids1),len(ids2))

SaleRec.register()
