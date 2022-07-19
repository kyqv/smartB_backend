from netforce.model import Model,fields,get_model
import time

class BugReport(Model):
    _name="bug.report"
    _string="Bug Report"
    _fields={
        "create_time": fields.DateTime("Create Time",required=True),
        "description": fields.Text("Description"),
        "email": fields.Char("Email"),
        "url": fields.Char("URL",size=4096),
        "state": fields.Selection([["open","Open"],["closed","Closed"]],"Status",required=True,search=True),
    }
    _order="create_time desc"
    _defaults={
        "create_time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "open",
    }

    def report_bug(self,description,email=None,url=None,context={}):
        vals={
            "description": description,
            "email": email,
            "url": url[:4096] if url else "N/A",
        }
        obj_id=self.create(vals)
        self.trigger([obj_id],"reported")
        return {
            "number": "B%.6d"%obj_id,
        }

BugReport.register()
