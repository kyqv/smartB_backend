from netforce.model import Model, fields, get_model
from netforce import access
import time


class Approval(Model):
    _name = "approval"
    _string = "Approval"
    _fields = {
        "date": fields.DateTime("Request Date", required=True, search=True),
        "approve_date": fields.DateTime("Approve Date", search=True),
        "user_id": fields.Many2One("base.user","Approved By",required=True,on_delete="cascade"),
        "related_id": fields.Reference([["purchase.order","Purchase Order"]],"Related To"),
        "state": fields.Selection([["pending","Awaiting Approval"],["approved","Approved"],["rejected","Rejected"],["cancel","Cancelled"]],"Status"),
        "wkf_step_id": fields.Many2One("approve.wkf.step","Workflow Step"),
        "company_id": fields.Many2One("company","Company",required=True),
    }
    _order="date"
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "pending",
        "company_id": lambda *a: access.get_active_company(),
    }

    def request_approval(self,user=None,context={}):
        trigger_model = context.get("trigger_model")
        if not trigger_model:
            raise Exception("Missing trigger model")
        tm = get_model(trigger_model)
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        res=get_model("base.user").search([["login","=",user]])
        if not res:
            raise Exception("User not found: %s"%user)
        req_user_id=res[0]
        vals={
            "user_id": req_user_id,
            "related_id": "%s,%s"%(trigger_model,trigger_ids[0]),
        }
        new_id=self.create(vals)
        self.trigger([new_id],"requested")

    def check_model(self,ids,model=None,context={}):
        filter_ids=[]
        for obj in self.browse(ids):
            rel=obj.related_id
            if rel and rel._model==model:
                filter_ids.append(obj.id)
        return filter_ids

Approval.register()
