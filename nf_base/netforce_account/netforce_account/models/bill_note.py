from netforce.model import Model, fields, get_model
from netforce import access
import time


class BillNote(Model):
    _name = "bill.note"
    _string = "Billing Note"
    _name_field="number"
    _audit_log=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "date": fields.Date("Date",required=True),
        "customer_id": fields.Many2One("contact","Customer",required=True,search=True),
        "remarks": fields.Text("Remarks"),
        "amount_total": fields.Decimal("Total Amount",function="get_total",function_multi=True),
        "amount_due": fields.Decimal("Due Amount",function="get_total",function_multi=True),
        "invoices": fields.One2Many("account.invoice","bill_note_id","Customer Invoices"),
        "payments": fields.One2Many("account.payment","related_id","Payments"),
        "company_id": fields.Many2One("company", "Company"),
    }
    _order = "id desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="bill_note")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    _defaults={
        "number": _get_number,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: access.get_active_company(),
    }

    def get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total=0
            due=0
            for inv in obj.invoices:
                total+=inv.amount_total
                due+=inv.amount_due
            vals[obj.id]={
                "amount_total": total,
                "amount_due": due,
            }
        return vals

    def copy_to_payment(self,ids,context={}):
        obj=self.browse(ids[0])
        pmt_vals={
            "contact_id": obj.customer_id.id,
            "type": "in",
            "pay_type": "invoice",
            "related_id": "bill.note,%s"%obj.id,
            "lines": [],
        }
        for inv in obj.invoices:
            line_vals={
                "invoice_id": inv.id,
                "amount_invoice": inv.amount_total,
                "amount": inv.amount_total,
            }
            pmt_vals["lines"].append(("create",line_vals))
        pmt_id=get_model("account.payment").create(pmt_vals,context={"type":"out"})
        pmt=get_model("account.payment").browse(pmt_id)
        return {
            "next": {
                "name": "payment",
                "mode": "form",
                "active_id": pmt_id,
            },
            "alert": "Payment %s copied from billing note"%pmt.number,
        }

BillNote.register()
