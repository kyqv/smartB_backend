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
import json


class PrintWizard(Model):
    _name = "print.wizard"
    _transient = True
    _fields = {
        "model": fields.Char("Model", required=True),
        "ids": fields.Text("IDs", required=True),
        "method": fields.Char("Method"),
        "template_type": fields.Char("Template Type"),
        "template_name": fields.Char("Template Name"),
        "template_id": fields.Many2One("report.template", "Report Template", required=True, on_delete="cascade"),
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
        template_name=context.get("template_name")
        if template_type:
            cond=[["type","=",template_type]]
        elif template_name:
            cond=[["name","=",template_name]]
        else:
            return
        res=get_model("report.template").search(cond)
        if not res:
            return
        return res[0]

    _defaults = {
        "model": lambda self, ctx: ctx["model"],
        "ids": get_ids,
        "method": lambda self, ctx: ctx.get("method"),
        "template_type": lambda self, ctx: ctx.get("template_type") or "other",
        "template_name": lambda self, ctx: ctx.get("template_name"),
        "template_id": _get_template,
    }

    def print(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.template_id:
            raise Exception("Missing template")
        action={
            "type": "report",
            "model": obj.model,
            "ids": json.loads(obj.ids),
            "method": obj.method,
            "template": obj.template_id.name,
        }
        return {
            "next": action,
        }

    def open_new_tab(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.template_id:
            raise Exception("Missing template")
        action={
            "type": "report",
            "model": obj.model,
            "ids": json.loads(obj.ids),
            "template": obj.template_id.name,
            "no_download": True,
        }
        return {
            "next": action,
        }

    def cloud_print(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.template_id:
            raise Exception("Missing template")
        return {
            "next": {
                "type": "cloud_print",
                "model": obj.model,
                "ids": json.loads(obj.ids),
                "template": obj.template_id.name,
            }
        }

PrintWizard.register()
