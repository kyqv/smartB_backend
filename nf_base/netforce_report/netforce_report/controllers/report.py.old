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

from netforce.controller import Controller
from netforce.model import get_model, clear_cache, fields
from netforce import database
from netforce import template
from netforce.action import get_action
from netforce.utils import get_data_path, set_data_path
from netforce_report import get_report_jasper, get_report_jasper_multi_page, report_render_xls, report_render_doc, report_render_odt, report_render_ods, convert_to_pdf, merge_pdf, report_render_jsx, get_report_template
from netforce.database import get_connection, get_active_db
from netforce import config
from netforce import static
from netforce import access
import json
from pprint import pprint
import os
import base64
import urllib
import netforce
import sys
import tempfile
from lxml import etree
import time


def parse_args(handler):
    res = {}
    for path in handler.request.arguments:
        for v in handler.get_arguments(path):
            if v == "":
                continue
            set_data_path(res, path, v)
    return res


class Report(Controller):
    _path = "/report"

    def get(self):  # TODO: cleanup
        db = get_connection()
        if db:
            db.begin()
        try:
            clear_cache()
            ctx = {
                "request": self.request,
                "request_handler": self,
                "dbname": get_active_db(),
            }
            data = self.get_cookies()
            if data:
                ctx.update(data)
            action_vals = parse_args(self)
            ctx.update(action_vals)
            name = action_vals.get("name")
            if name:
                action_ctx = action_vals
                action = get_action(name, action_ctx)
                for k, v in action.items():
                    if k not in action_vals:
                        action_vals[k] = v
            if "context" in action_vals:
                ctx.update(action_vals["context"])
            action_vals["context"] = ctx
            self.clear_flash()
            type = action_vals.get("type", "view")
            if type == "report":  # XXX: deprecated
                model = action_vals["model"]
                method = action_vals.get("method", "get_report_data")
                refer_id = action_vals.get("refer_id")
                format = action_vals.get("format", "pdf")
                if action_vals.get("ids") and isinstance(action_vals["ids"], str):
                    ids = json.loads(action_vals["ids"])
                    action_vals["ids"] = ids
                m = get_model(model)
                f = getattr(m, method, None)
                if action_vals.get("multi_page"):
                    datas = []
                    if "ids" in action_vals:
                        ids = action_vals["ids"]
                    else:
                        ids = [int(action_vals["refer_id"])]
                    for obj_id in ids:
                        ctx = action_vals.copy()
                        ctx["refer_id"] = obj_id
                        data = f(context=ctx)
                        datas.append(data)
                else:
                    data = f(context=action_vals)
                template = action_vals.get("template")
                if not template and action_vals.get("template_method"):
                    f = getattr(m, action_vals["template_method"])
                    template = f(ids, context=action_vals)
                if action_vals.get("multi_page"):
                    out = get_report_jasper_multi_page(template, datas, format=format)
                elif "pages" in data:
                    datas = []
                    for obj in data["pages"]:
                        d = data.copy()
                        d.update(obj)
                        datas.append(d)
                    out = get_report_jasper_multi_page(template, datas, format=format)
                else:
                    out = get_report_jasper(template, data, format=format)
                db = get_connection()
                if db:
                    db.commit()
                if format == "pdf":
                    fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/pdf")
                elif format == "xls":
                    fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".xls"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/vnd.ms-excel")
                elif format == "ods":
                    fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".ods"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/vnd.oasis.opendocument.spreadsheet")
                else:
                    raise Exception("Invalid format: %s" % format)
                self.write(out)
            elif type == "report_jasper":  # new jasper
                model = action_vals["model"]
                method = action_vals.get("method", "get_report_data")
                refer_id = action_vals.get("refer_id")
                if refer_id:
                    refer_id = int(refer_id)
                    ids = [refer_id]
                else:
                    ids = json.loads(action_vals.get("ids"))
                format = action_vals.get("format", "pdf")
                m = get_model(model)
                f = getattr(m, method, None)
                data = f(ids, context=action_vals)
                if not data:
                    raise Exception("Missing report data")
                template = action_vals.get("template")
                if not template and action_vals.get("template_method"):
                    f = getattr(m, action_vals["template_method"])
                    template = f(ids, context=action_vals)
                if action_vals.get("multi_page"):
                    datas = []
                    for obj in data["objs"]:
                        d = data.copy()
                        d["obj"] = obj
                        datas.append(d)
                    out = get_report_jasper_multi_page(template, datas, format=format)
                else:
                    out = get_report_jasper(template, data, format=format)
                db = get_connection()
                if db:
                    db.commit()
                if format == "pdf":
                    fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/pdf")
                elif format == "xls":
                    fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".xls"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/vnd.ms-excel")
                elif format == "ods":
                    fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".ods"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/vnd.oasis.opendocument.spreadsheet")
                else:
                    raise Exception("Invalid format: %s" % format)
                self.write(out)
            elif type == "report_html":  # XXX: deprecated
                model = action_vals["model"]
                method = action_vals["method"]
                m = get_model(model)
                f = getattr(m, method, None)
                ctx2 = ctx.copy()  # XXX
                ctx2.update(action_vals)
                data = f(context=ctx2)
                tmpl_name = action_vals.get("template")
                tmpl = netforce.template.get_template(tmpl_name)
                ctx2["data"] = data
                html = tmpl.render({"context": ctx2})
                out = netforce.report.html2pdf(html)
                db = get_connection()
                if db:
                    db.commit()
                fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                self.set_header("Content-Type", "application/pdf")
                self.write(out)
            elif type == "report_xls":
                model = action_vals["model"]
                method = action_vals["method"]
                m = get_model(model)
                f = getattr(m, method, None)
                ctx2 = ctx.copy()  # XXX
                ctx2.update(action_vals)
                data = f(context=ctx2)
                tmpl_name = action_vals.get("template")
                if not tmpl_name and action_vals.get("template_method"):
                    f = getattr(m, action_vals["template_method"])
                    tmpl_name = f(context=action_vals)
                out = report_render_xls(tmpl_name, data)
                db = get_connection()
                if db:
                    db.commit()
                fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".xlsx"
                self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                self.set_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.write(out)
            elif type == "report_doc":  # XXX: deprecated
                model = action_vals["model"]
                method = action_vals["method"]
                convert = action_vals.get("convert")
                m = get_model(model)
                f = getattr(m, method, None)
                ctx2 = ctx.copy()  # XXX
                ctx2.update(action_vals)
                data = f(context=ctx2)
                tmpl_name = action_vals.get("template")
                if not tmpl_name and action_vals.get("template_method"):
                    f = getattr(m, action_vals["template_method"])
                    tmpl_name = f(context=action_vals)
                out = report_render_doc(tmpl_name, data)
                db = get_connection()
                if db:
                    db.commit()
                if convert == "pdf":
                    fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/pdf")
                    out = convert_to_pdf(out, "docx")
                else:
                    fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".docx"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header(
                        "Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.write(out)
            elif type == "report_odt":  # XXX: deprecated
                model = action_vals["model"]
                method = action_vals.get("method", "get_report_data")
                convert = action_vals.get("convert")
                m = get_model(model)
                f = getattr(m, method, None)
                if action_vals.get("ids") and isinstance(action_vals["ids"], str):
                    ids = json.loads(action_vals["ids"])
                    action_vals["ids"] = ids
                    print("ids", ids)
                if action_vals.get("ids") and convert == "pdf":  # FIXME
                    outs = []
                    for id in ids:
                        ctx = action_vals.copy()
                        ctx["refer_id"] = str(id)
                        data = f(context=ctx)
                        tmpl_name = action_vals.get("template")
                        if not tmpl_name and action_vals.get("template_method"):
                            f = getattr(m, action_vals["template_method"])
                            tmpl_name = f(context=action_vals)
                        out_odt = report_render_odt(tmpl_name, data)
                        out_pdf = convert_to_pdf(out_odt, "odt")  # XXX
                        outs.append(out_pdf)
                    out = merge_pdf(outs)
                else:
                    ctx2 = ctx.copy()  # XXX
                    ctx2.update(action_vals)
                    data = f(context=ctx2)
                    tmpl_name = action_vals.get("template")
                    if not tmpl_name and action_vals.get("template_method"):
                        f = getattr(m, action_vals["template_method"])
                        tmpl_name = f(context=action_vals)
                    out = report_render_odt(tmpl_name, data)
                    if convert == "pdf":
                        out = convert_to_pdf(out, "odt")
                db = get_connection()
                if db:
                    db.commit()
                if convert == "pdf":
                    fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/pdf")
                else:
                    fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".odt"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/vnd.oasis.opendocument.text")
                self.write(out)
            elif type == "report_odt2":  # XXX: use this instead of report_odt later
                model = action_vals["model"]
                method = action_vals.get("method", "get_report_data")
                convert = action_vals.get("convert")
                refer_id = action_vals.get("refer_id")
                m = get_model(model)
                f = getattr(m, method, None)
                if "ids" in action_vals:
                    ids = json.loads(action_vals["ids"])
                elif "refer_id" in action_vals:
                    ids = [int(action_vals["refer_id"])]
                else:
                    raise Exception("Missing report ids")
                print("ids", ids)
                ctx = action_vals.copy()
                data = f(ids, context=ctx)
                tmpl_name = action_vals.get("template")
                if not tmpl_name and action_vals.get("template_method"):
                    f = getattr(m, action_vals["template_method"])
                    tmpl_name = f(ids, context=action_vals)
                out = report_render_odt(tmpl_name, data)
                db = get_connection()
                if db:
                    db.commit()
                if convert == "pdf":
                    out = convert_to_pdf(out, "odt")
                    fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/pdf")
                else:
                    fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".odt"
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                    self.set_header("Content-Type", "application/vnd.oasis.opendocument.text")
                self.write(out)
            elif type == "report_txt":  # XXX: deprecated
                model = action_vals["model"]
                method = action_vals["method"]
                m = get_model(model)
                f = getattr(m, method, None)
                if not f:
                    raise Exception("method %s of %s doesn't exist" % (method, m._name))
                ctx2 = ctx.copy()  # XXX
                ctx2.update(action_vals)
                res = f(context=ctx2)
                if isinstance(res, str):
                    res = {
                        "data": res,
                    }
                out = res.get("data", "").encode(action_vals.get("encoding", "utf-8"))
                filename = res.get("filename", "report.txt")
                db = get_connection()
                if db:
                    db.commit()
                self.set_header("Content-Disposition", "attachment; filename=%s" % filename)
                self.set_header("Content-Type", "text/plain")
                self.write(out)
            elif type == "report_file":
                model = action_vals["model"]
                method = action_vals.get("method", "get_report_data")
                m = get_model(model)
                f = getattr(m, method, None)
                if "ids" in action_vals:
                    ids = json.loads(action_vals["ids"])
                else:
                    ids = None
                print("ids", ids)
                ctx = action_vals.copy()
                if ids is not None:
                    res = f(ids, context=ctx)
                else:
                    res = f(context=ctx)
                db = get_connection()
                if db:
                    db.commit()
                out = res["data"]
                fname = res["filename"]
                mtype = res["mimetype"]
                self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                self.set_header("Content-Type", mtype)
                self.write(out)
            elif type == "report_jsx":
                model = action_vals["model"]
                method = action_vals.get("method", "get_report_data")
                m = get_model(model)
                f = getattr(m, method, None)
                if "ids" in action_vals:
                    ids = json.loads(action_vals["ids"])
                else:
                    ids=None
                print("ids", ids)
                ctx = action_vals.copy()
                data = f(ids, context=ctx)
                tmpl_name = action_vals.get("template")
                tmpl_body = get_report_template(tmpl_name, "jsx")
                out = report_render_jsx(tmpl_body, data)
                db = get_connection()
                if db:
                    db.commit()
                fname = tmpl_name + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                self.set_header("Content-Type", "application/pdf")
                self.write(out)
            else:
                raise Exception("Invalid report type: %s" % type)
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stdout)
            db = get_connection()
            if db:
                db.rollback()
            html = netforce.template.render("report_error", {"error": str(e)})
            self.write(html)

Report.register()
