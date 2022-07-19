from netforce.model import Model, fields, get_model
from netforce import access

class ApproveWkfStep(Model):
    _name = "approve.wkf.step"
    _name_field="sequence"
    _fields = {
        "wkf_id": fields.Many2One("approve.wkf","Workflow",required=True,on_delete="cascade"),
        "sequence": fields.Integer("Sequence",required=True),
        "user_type": fields.Selection([["select","Select User"],["pic","PIC"],["mic","MIC"]],"User Type",required=True),
        "approve_user_id": fields.Many2One("base.user","Approve By"),
        "company_id": fields.Many2One("company","Company",required=True),
    }
    _defaults={
        "company_id": lambda *a: access.get_active_company(),
    }

    _order="sequence,id"

    def delete(self,ids,context={}):
        user_id=access.get_active_user()
        try:
            access.set_active_user(1)
            for obj in self.browse(ids):
                res=get_model("approval").search([["wkf_step_id","=",obj.id],["state","=","pending"]])
                if res:
                    raise Exception("Can not delete workflow step %s because pending approval requests"%obj.id)
            super().delete(ids,context={})
        finally:
            access.set_active_user(user_id)

ApproveWkfStep.register()
