from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import utils
from netforce_report import render_page_text
import json
import time
import os
import requests

class Conv(Controller):
    _path = "/convert_to_pdf"

    def get(self):
        try:
            print("convert_to_pdf")
            url=self.get_argument("url",None)
            print("url",url)
            params={
                "url": url,
            }
            req=requests.get("http://localhost:8200/web_to_pdf",params=params)
            data=req.content
            try:
                h = req.headers.get('content-disposition')
                if h:
                    filename = re.findall("filename=(.+)", h)[0]
                    filename=filename.replace(".pdf","")+".pdf"
                else:
                    filename="report.pdf"
            except:
                filename="report.pdf"
            self.set_header("Content-Type", "application/pdf")
            self.set_header("Content-Disposition", "attachment; filename=%s" % filename)
            self.add_header("Access-Control-Allow-Origin","*")
            self.write(data)
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
