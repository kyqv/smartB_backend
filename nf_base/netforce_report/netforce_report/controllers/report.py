from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import utils
from netforce_report import render_template_jsx,render_template_hbs,render_template_odt,render_template_docx,render_template_xlsx,format_report_data,get_module_report_template,render_template_jasper,render_template_nfjson_xlsx,render_template_nfjson_pdf,get_fields_nfjson
import json
import time
import os

class Report(Controller):
    _path = "/report"

    def get(self):
        try:
            model = self.get_argument("model")
            method = self.get_argument("method",None)
            template = self.get_argument("template")
            no_download = self.get_argument("no_download",None)
            ids=self.get_argument("ids",None)
            if ids:
                ids = json.loads(ids)
            res = self.get_argument("context",None)
            if res:
                ctx=json.loads(res)
            else:
                ctx={}
            dbname=ctx.get("database")
            if dbname:
                database.set_active_db(dbname)
            company_id=ctx.get("company_id")
            if company_id:
                company_id=int(company_id)
                access.set_active_company(company_id)
            user_id=None
            if "user_id" in ctx:
                user_id=int(ctx["user_id"])
                token=ctx.get("token")
                dbname=database.get_active_db()
                if not utils.check_token(dbname, user_id, token):
                    user_id=None
            access.set_active_user(user_id)
            access.set_active_user(1) # FIXME
            with database.Transaction():
                tmpl=None
                tmpl_path=None
                tmpl_format=None
                convert_pdf=False
                convert_png=False
                res=get_model("report.template").search([["name","=",template]])
                if res:
                    tmpl_id=res[0]
                    tmpl=get_model("report.template").browse(tmpl_id)
                    tmpl_path=utils.get_file_path(tmpl.file) if tmpl.file else None
                    tmpl_format=tmpl.format
                    convert_pdf=tmpl.convert_pdf
                    if self.get_argument("convert_pdf",None):
                        convert_pdf=True
                    elif self.get_argument("convert_png",None):
                        convert_png=True
                else:
                    tmpl_path=get_module_report_template(template)
                    if not tmpl_path:
                        raise Exception("Template not found: %s"%template)
                    tmpl_format=os.path.splitext(tmpl_path)[1][1:]
                    if self.get_argument("convert_pdf",None):
                        convert_pdf=True
                    else:
                        convert_pdf=False
                if method:
                    m=get_model(model)
                    f=getattr(m,method)
                    if ids is not None:
                        data=f(ids,context=ctx)
                    else:
                        data=f(context=ctx) # XXX
                else:
                    if tmpl and tmpl.field_names:
                        field_names=[n.strip() for n in tmpl.field_names.split(",")]
                    else:
                        field_names=[]
                    if tmpl_format=="nfjson":
                        field_names=get_fields_nfjson(tmpl.body,model)
                    res = get_model(model).read_path(ids,field_names,context=ctx)
                    if tmpl_format=="xlsx":
                        data=res
                    else:
                        data = [format_report_data(vals,model) for vals in res]
                if tmpl_format=="nfjson":
                    report_data=data
                elif tmpl and tmpl.multi_render:
                    report_data=data
                else:
                    report_data={"data":data}
                if tmpl_format=="hbs":
                    out=render_template_hbs(tmpl.body,report_data)
                    out_fmt="txt"
                elif tmpl_format=="jsx":
                    out = render_template_jsx(tmpl.body, report_data, orientation=tmpl.orientation or "portrait", header=tmpl.header, footer=tmpl.footer) # TODO: split render / pdf conv
                    out_fmt="pdf"
                elif tmpl_format=="odt":
                    out = render_template_odt(tmpl_path, report_data, convert_pdf=convert_pdf)
                    if convert_pdf:
                        out_fmt="pdf"
                    else:
                        out_fmt="odt"
                elif tmpl_format=="docx":
                    out = render_template_docx(tmpl_path, report_data, convert_pdf=convert_pdf)
                    if convert_pdf:
                        out_fmt="pdf"
                    else:
                        out_fmt="docx"
                elif tmpl_format=="xlsx":
                    out = render_template_xlsx(tmpl_path, report_data, convert_pdf=convert_pdf)
                    if convert_pdf:
                        out_fmt="pdf"
                    else:
                        out_fmt="xlsx"
                elif tmpl_format=="jrxml":
                    out = render_template_jasper(tmpl_path, report_data["data"]) # XXX
                    out_fmt="pdf"
                elif tmpl_format=="nfjson":
                    if convert_pdf:
                        out=render_template_nfjson_pdf(tmpl.body,report_data,model)
                        out_fmt="pdf"
                    elif convert_png:
                        out=render_template_nfjson_pdf(tmpl.body,report_data,model,convert_png=True)
                        out_fmt="png"
                    else:
                        out=render_template_nfjson_xlsx(tmpl.body,report_data,model)
                        out_fmt="xlsx"
                else:
                    raise Exception("Invalid report template format: '%s'"%tmpl_format)
                fname=None
                if tmpl and tmpl.out_filename:
                    fname=render_template_hbs(tmpl.out_filename,{"data":report_data})
                if out_fmt=="txt":
                    content_type="text/plain"
                    if not fname:
                        fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".txt"
                elif out_fmt=="odt":
                    content_type="application/vnd.oasis.opendocument.text"
                    if not fname:
                        fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".odt"
                elif out_fmt=="docx":
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    if not fname:
                        fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".docx"
                elif out_fmt=="xlsx":
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if not fname:
                        fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".xlsx"
                elif out_fmt=="pdf":
                    content_type="application/pdf"
                    if not fname:
                        fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".pdf"
                elif out_fmt=="png":
                    content_type="image/png"
                    if not fname:
                        fname = template + "-" + time.strftime("%Y-%m-%dT%H:%M:%S") + ".png"
                else:
                    raise Exception("Invalid output format: %s"%out_fmt)
                self.set_header("Content-Type", content_type)
                if not no_download:
                    self.set_header("Content-Disposition", "attachment; filename=%s" % fname)
                self.write(out)
        except Exception as e:
            import traceback
            traceback.print_exc()
            msg="Error: "+str(e)
            self.write(msg)

Report.register()
