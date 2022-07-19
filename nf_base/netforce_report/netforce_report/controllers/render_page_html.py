from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import utils
from netforce_report import render_page_html
import json
import time
import os

class Report(Controller):
    _path = "/render_page_html"

    def get(self):
        try:
            print("render_page_text")
            dbname=self.get_argument("database")
            if dbname:
                database.set_active_db(dbname)
            user_id=self.get_argument("user_id",None)
            if user_id:
                user_id=int(user_id)
            token=self.get_argument("token",None)
            no_download = self.get_argument("no_download",None)
            if user_id and token:
                if not utils.check_token(dbname, user_id, token):
                    raise Exception("Invalid token")
            else:
                user_id=1
            page_id = self.get_argument("page_id")
            filename = self.get_argument("filename",None) or "report.html"
            props={}
            for n in self.request.arguments.keys():
                props[n]=self.get_argument(n)
            print("props",props)
            with database.Transaction():
                access.set_active_user(1) 
                user=get_model("base.user").browse(user_id)
                company_id=user.company_id.id # XXX
                access.set_active_user(user_id)
                access.set_active_company(company_id)
                res=get_model("page.layout").search([["id","=",page_id]])
                if not res:
                    raise Exception("Page not found: %s"%page_name)
                page_id=res[0]
                page=get_model("page.layout").browse(page_id)
                try:
                    layout=json.loads(page.layout)
                except:
                    raise Exception("Invalid layout")
                if page.model_id:
                    props["model"]=page.model_id.name
                res=render_page_html(layout,props)
                out=res["data"]
                filename=res["filename"]
                content_type="text/html; charset=\"UTF-8\""
                self.set_header("Content-Type", content_type)
                if not no_download:
                    self.set_header("Content-Disposition", "attachment; filename=%s" % filename)
                self.add_header("Access-Control-Allow-Origin","*")
                self.write(out)
        except Exception as e:
            import traceback
            traceback.print_exc()
            msg="Error: "+str(e)
            self.write(msg)

    def options(self):
        self.add_header("Access-Control-Allow-Origin","*")
        self.add_header("Access-Control-Allow-Headers","Content-Type, X-Database, X-Schema, X-Locale")
        self.add_header("Access-Control-Allow-Methods","POST, GET, OPTIONS")

Report.register()
