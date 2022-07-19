from netforce.model import Model, fields, get_model


class PaymentPlan(Model):
    _name = "payment.plan"
    _string = "Payment Plan"
    _name_field="description"
    _fields = {
        "related_id": fields.Reference([],"Related To"),
        "sequence": fields.Integer("Sequence"),
        "description": fields.Char("Description"),
        "amount": fields.Decimal("Amount",required=True),
        "invoice_id": fields.Many2One("account.invoice","Invoice"),
        "period": fields.Selection([["one","One Time"],["month","Monthly"],["year","Yearly"]],"Periodicity"),
        "state": fields.Selection([["waiting","Waiting"],["draft_invoice","Draft Invoice Created"],["invoice_sent","Invoice Sent"],["invoice_paid","Invoice Paid"]],"Status",function="get_state"),
    }
    _order = "sequence"

    def get_state(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            state="waiting"
            inv=obj.invoice_id
            if inv:
                if inv.state=="draft":
                    state="draft_invoice"
                elif inv.state=="waiting_payment":
                    state="invoice_sent"
                elif inv.state=="paid":
                    state="invoice_paid"
            vals[obj.id]=state
        return vals

PaymentPlan.register()
