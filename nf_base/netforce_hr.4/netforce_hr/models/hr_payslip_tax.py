from netforce.model import Model, fields, get_model

class Tax(Model):
    _name="hr.payslip.tax"
    _fields={
        "payslip_id": fields.Many2One("hr.payslip","Payslip"),
        "name": fields.Char("Description",size=255),
        "code": fields.Char("Code"),
        "amount": fields.Decimal("Amount"),
    }

    def onchange_amount(self,context={}):
        data=context["data"]
        print(data)
        return data

Tax.register()
