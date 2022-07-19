from netforce.model import Model, fields, get_model

class PayslipJournalLine(Model):
    _name="hr.payslip.journal.line"
    _transient=True

    _fields={
        "payslip_journal_id": fields.Many2One("hr.payslip.journal","Payslip Journal",required=True,on_delete="cascade"),
        'description': fields.Text("Description"),
        'debit': fields.Decimal("Debit"),
        'credit': fields.Decimal("Credit"),
        'account_id': fields.Many2One("account.account","Account",condition=[['type','!=','view']]),
        'contrib': fields.Boolean("Contribution Employer"),
    }
     
    _order="debit desc"

PayslipJournalLine.register()
