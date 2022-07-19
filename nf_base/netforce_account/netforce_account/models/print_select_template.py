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
from netforce.action import get_action


class SelectTemplate(Model):
    _name = "print.select.template"
    _transient = True
    _fields = {
        "report_action": fields.Char("Report Action", required=True),
        "refer_id": fields.Integer("Refer ID", required=True),
        "template_type": fields.Char("Template Type", required=True),
        "template_id": fields.Many2One("report.template", "Template", required=True, on_delete="cascade"),
        "format": fields.Selection([["pdf", "PDF"], ["odt", "ODT"], ["docx", "DOCX"], ["xlsx", "XLSX"]], "File Format", required=True),
    }

    _defaults = {
        "report_action": lambda self, ctx: ctx["report_action"],
        "refer_id": lambda self, ctx: ctx["refer_id"],
        "template_type": lambda self, ctx: ctx["template_type"],
    }

    def onchange_template(self, context={}):
        data = context["data"]
        tmpl_id = data["template_id"]
        obj = get_model("report.template").browse([tmpl_id])[0]
        if obj.format in ("odt", "odt2"):
            data["format"] = "odt"
        elif obj.format == "docx":
            data["format"] = "docx"
        elif obj.format == "xlsx":
            data["format"] = "xlsx"
        elif obj.format in ("jrxml", "jrxml2"):
            data["format"] = "pdf"
        return data

    def print(self, ids, context={}):
        print("SelectTemplate.print", ids)
        obj = self.browse(ids)[0]
        tmpl = obj.template_id
        action = {
            "name": obj.report_action,
            "template": obj.template_id.name,
            "refer_id": obj.refer_id,
        }
        if tmpl.method:
            action["method"] = tmpl.method
        if tmpl.format == "odt":
            action["type"] = "report_odt"
        elif tmpl.format == "odt2":
            action["type"] = "report_odt2"
        elif tmpl.format == "docx":
            action["type"] = "report_doc"
        elif tmpl.format == "xlsx":
            action["type"] = "report_xls"
        elif tmpl.format == "jrxml":
            action["type"] = "report"
        elif tmpl.format == "jrxml2":
            action["type"] = "report_jasper"
        else:
            raise Exception("Invalid template format")
        if obj.format != tmpl.format:
            action["convert"] = obj.format
        return {
            "next": action,
        }

SelectTemplate.register()
