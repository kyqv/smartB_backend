from netforce.model import Model, fields, get_model
from netforce import access
import time

class Expense(Model):
    _name="expense"
    _string="Expense"
    _multi_company=True
    _fields={
        "claim_id": fields.Many2One("expense.claim","Expense Claim",search=True),
        "merchant": fields.Char("Merchant Name",required=True),
        "amount": fields.Decimal("Amount",required=True),
        "description": fields.Text("Description"),
        "qty": fields.Decimal("Qty"), # XXX: deprecated
        "unit_price": fields.Decimal("Unit Price"), # XXX: deprecated
        "account_id": fields.Many2One("account.account","Account",condition=[["type","!=","view"]]),
        "tax_id": fields.Many2One("account.tax.rate","Tax Rate"),
        "track_id": fields.Many2One("account.track.categ","Track-1",condition=[["type","=","1"]]),
        "track2_id": fields.Many2One("account.track.categ","Track-2",condition=[["type","=","2"]]),
        "supplier_id": fields.Many2One("contact","Supplier",search=True,condition=[["supplier","=",True]]), # XXX: deprecated
        "date": fields.Date("Date",required=True,search=True),
        "currency_id": fields.Many2One("currency","Currency",required=True),
        "currency_rate": fields.Decimal("Currency Rate"),
        "employee_id": fields.Many2One("hr.employee","Employee",required=True,search=True),
        "project_id": fields.Many2One("project","Project"),
        "image": fields.File("Image"),
        "company_id": fields.Many2One("company","Company"),
        "categ_id": fields.Many2One("expense.categ","Expense Category"),
        "product_id": fields.Many2One("product","Product"),
        "related_id": fields.Reference(["jc.job","Job"],"Related To"),
        "invoice_id": fields.Many2One("account.invoice","Invoice"),
    }

    def _get_employee(self,context={}):
        user_id=access.get_active_user()
        res=get_model("hr.employee").search([["user_id","=",user_id]])
        if not res:
            return None
        return res[0]

    def _get_currency(self,context={}):
        settings=get_model("settings").browse(1)
        return settings.currency_id.id

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "employee_id": _get_employee,
        "currency_id": _get_currency,
    }
    _order="date desc,id desc"

    def onchange_product(self,context={}):
        print("onchange_product")
        data=context.get("data")
        prod_id=data["product_id"]
        prod=get_model("product").browse(prod_id)
        data["account_id"]=prod.purchase_account_id.id
        data["tax_id"]=prod.purchase_tax_id.id
        print("=> data",data)
        return data

Expense.register()
