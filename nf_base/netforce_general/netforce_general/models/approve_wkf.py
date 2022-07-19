from netforce.model import Model, fields
from netforce import access


class ApproveWkf(Model):
    _name = "approve.wkf"
    _string="Approval Workflow"
    _name_field = "name"
    _multi_company=True
    _fields = {
        "name": fields.Char("Workflow Name"), # XXX: deprecated
        "type": fields.Selection([["expense","Expense Approval"],["leave","Leave Approval"]],"Approval Type",required=True,search=True),
        "steps": fields.One2Many("approve.wkf.step","wkf_id","Workflow Steps"),
        "user_id": fields.Many2One("base.user","User",search=True),
        "group_id": fields.Many2One("user.group","Group",search=True),
        "min_amount": fields.Decimal("Minimum Amount"),
        "max_amount": fields.Decimal("Maximum Amount"),
        "company_id": fields.Many2One("company","Company",required=True,search=True),
    }
    _defaults={
        "company_id": lambda *a: access.get_active_company(),
    }

    def find_wkf(self,type,user_id,company_id=None,context={}):
        print("find_wkf",type,user_id)
        for wkf in self.search_browse([["type","=",type]]):
            print("  try %s"%wkf.id)
            if company_id and wkf.company_id.id!=company_id:
                continue
            if wkf.user_id and wkf.user_id.id!=user_id:
                print("    user diff")
                continue
            if wkf.group_id:
                user_ids=[u.id for u in wkf.group_id.users]
                if user_id not in user_ids:
                    print("    group diff")
                    continue
            return wkf.id
        return None

ApproveWkf.register()
