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
from netforce_report import render_template_hbs
import time

class SmsTemplate(Model):
    _name = "sms.template"
    _string = "SMS Template"
    _name_field = "sender"
    _fields = {
        "name": fields.Char("Template Name", required=True, search=True),
        "phone": fields.Char("Phone Number", required=True, size=256, search=True),
        "body": fields.Text("Body", search=True),
        "account_id": fields.Many2One("sms.account","SMS Account"),
    }
    _order = "name"

    def create_sms(self, ids, data={}, name_id=None, related_id=None, state=None, context={}):
        print("SMSTemplate.create_sms",ids)
        obj = self.browse(ids)[0]
        try:
            phone = render_template_hbs(obj.phone or "", data)
        except:
            raise Exception("Failed to render 'Phone' in template: %s" % obj.name)
        try:
            body = render_template_hbs(obj.body or "", data)
        except:
            raise Exception("Failed to render 'Body' in template: %s" % obj.name)
        if obj.related and not related_id:
            try:
                related_id = render_template_hbs(obj.related or "", data)
            except:
                raise Exception("Failed to render 'Related To' in template: %s" % obj.name)
        if obj.contact and not name_id:
            try:
                name_id = render_template_hbs(obj.contact or "", data)
            except:
                raise Exception("Failed to render 'Contact' in template: %s" % obj.name)
        else:
            name_id=None
        vals = {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phone": phone,
            "body": body,
            "state": state or "to_send",
            "account_id": obj.account_id.id,
        }
        print("vals",vals)
        sms_id = get_model("sms.message").create(vals)
        return sms_id

SmsTemplate.register()
