from netforce.model import Model, fields, get_model
from decimal import *

class PayItem(Model):
    _name="hr.payitem"
    _string="Pay Item"

    _fields={
        "name": fields.Char("Name",required=True,search=True),
        "description": fields.Text("Description"),
        "type": fields.Selection([
            ["salary","Salary"],
            ["overtime","Overtime"],
            ["commission","Commission"],
            ["mobile","Mobile"],
            ["travel","Travel"],
            ["other_income","Other Income"],
            ["tax","Tax"],
            ["sso","SSO"],
            ["pvd","PVD"],
            ["other_expense","Other Expenses"],
            ],"Pay Item Type",required=True,search=True),
        "account_id": fields.Many2One("account.account","Account",multi_company=True),
        "active": fields.Boolean("Active"),
        "sequence": fields.Integer("Sequence"),
    }

    _defaults={
        "active": True,
    }
    _order="sequence,name"

PayItem.register()
