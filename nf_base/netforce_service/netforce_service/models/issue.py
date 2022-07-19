from netforce.model import Model, fields, get_model, clear_cache
from netforce.database import get_connection
from datetime import *
import time
from netforce import access

class Issue(Model):
    _name = "issue"
    _string = "Issue"
    _name_field = "title"
    _fields = {
        "number": fields.Char("Number",required=True,search=True),
        "project_id": fields.Many2One("project","Project",required=True,search=True),
        "title": fields.Char("Title",search=True,required=True),
        "date_created": fields.Date("Date Created",required=True),
        "age_days": fields.Integer("Age (Days)",function="get_age_days"),
        "date_planned": fields.Date("Planned Close Date"),
        "date_closed": fields.Date("Date Closed"),
        "description": fields.Text("Problem Description (English)"),
        "description2": fields.Text("Problem Description (Thai)"),
        "screenshot": fields.File("Screenshot (old)"),
        "url": fields.Char("URL"),
        "priority": fields.Selection([["0","Low"],["1","Medium"],["2","High"]],"Priority",required=True,search=True),
        "state": fields.Selection([["new","New"],["incomplete","Incomplete"],["planned","Planned"],["closed","Closed"]],"Status",required=True),
        "response": fields.Text("Support Response"),
        "screenshots": fields.One2Many("image","related_id","Screenshots"),
        "sequence": fields.Decimal("Sequence"),
        "type": fields.Selection([["bug","Bug"],["change","Modification Request"],["new_feature","New Feature Request"],["question","Question"]],"Issue Type",required=True,search=True),
    }
    _order = "priority desc,sequence,date_created,id"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="issue")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            user_id = access.get_active_user()
            access.set_active_user(1)
            res = self.search([["number", "=", num]])
            access.set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults={
        "date_created": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "new",
        "number": _get_number,
        "priority": "0",
    }

    def get_age_days(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            days=(datetime.today()-datetime.strptime(obj.date_created,"%Y-%m-%d")).days
            vals[obj.id]=days
        return vals

    def create(self,vals,*args,**kw):
        new_id=super().create(vals,*args,**kw)
        obj=self.browse(new_id)
        obj.trigger("create")
        return new_id

    def write(self,ids,vals,*args,**kw):
        super().write(ids,vals,*args,**kw)
        for obj in self.browse(ids):
            obj.trigger("write")

Issue.register()
