from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import utils
from netforce_report import render_page_text
import json
import time
import os

class Conv(Controller):
    _path = "/convert_to_xlsx"

    def get(self):
        try:
            print("convert_to_xlsx")
            url=self.get_argument("url",None)
            print("url",url)
            path="/tmp/report_web.html" # XXX
            cmd="/home/datrus/netforce/netforce_report/netforce_report/web_to_pdf/web_to_html.js \"%s\" %s"%(url,path)
            os.system(cmd)
            path2="/tmp/report_web.xlsx"
            #cmd="unoconv -f xlsx %s"%path
            cmd="cd /tmp; libreoffice --headless --calc --convert-to xlsx report_web.html"
            os.system(cmd)
            time.sleep(5)
            out=open(path2,"rb").read()
            try:
                title=open("/tmp/report_web_title.txt","r").read() # XXX
                if not title:
                    raise Exception("Missing title")
                filename=title+".xlsx"
            except:
                filename="report.xlsx"
            self.set_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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

Conv.register()
