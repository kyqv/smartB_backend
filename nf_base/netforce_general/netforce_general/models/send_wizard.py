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
from netforce.access import get_active_company
from netforce_report import render_report_to_file
import json


class SendWizard(Model):
    _name = "send.wizard"
    _transient = True
    _fields = {
        "model": fields.Char("Model", required=True),
        "ids": fields.Text("IDs", required=True),
        "template_type": fields.Char("Template Type"),
        "template_id": fields.Many2One("report.template", "Report Template", required=True,on_delete="cascade"),
        "email_template_id": fields.Many2One("email.template", "Email Template",required=True,on_delete="cascade"),
    }

    def get_ids(self,context={}):
        if "refer_id" in context:
            ids=[context["refer_id"]]
        elif "ids" in context:
            ids=context["ids"]
        else:
            raise Exception("Missing ids")
        return json.dumps(ids)

    def _get_template(self,context={}):
        template_type=context.get("template_type")
        if not template_type:
            return
        res=get_model("report.template").search([["type","=",template_type]])
        if not res:
            return
        return res[0]

    _defaults = {
        "model": lambda self, ctx: ctx["model"],
        "ids": get_ids,
        "template_type": lambda self, ctx: ctx["template_type"],
        "template_id": _get_template,
    }

    def create_email(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.email_template_id:
            raise Exception("Missing email template")
        model_ids=json.loads(obj.ids)
        report_file=render_report_to_file(obj.model,None,obj.template_id.name,model_ids)
        report_obj=get_model(obj.model).browse(model_ids[0])
        data = {
            "obj": report_obj,
            "report_file": report_file,
        }
        email_id = obj.email_template_id.create_email(data,state="draft")
        return {
            "next": {
                "name": "email",
                "mode": "form",
                "active_id": email_id,
            },
        }

SendWizard.register()
