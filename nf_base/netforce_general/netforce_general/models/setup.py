from netforce.model import Model, fields
from netforce import access


class Setup(Model):
    _name = "setup"
    _fields = {
        "company_type": fields.Selection([["company_vat","Company (VAT Registered)"],["company_novat","Company (No VAT)"],["freelance","Freelance"]],"Company Type"),
        "company_name": fields.Char("Company Name"),
        "phone": fields.Char("Phone"),
        "address": fields.Text("Address"),
        "tax_id": fields.Char("Tax ID"),
        "branch_no": fields.Char("Branch No."),
    }
    _order = "name"

    def next1(self,ids,context={}):
        obj=self.browse(ids[0])
        return {
            "next": {
                "name": "setup2",
                "active_id": obj.id,
            },
        }

    def back2(self,ids,context={}):
        obj=self.browse(ids[0])
        return {
            "next": {
                "name": "setup1",
                "active_id": obj.id,
            },
        }

Setup.register()
