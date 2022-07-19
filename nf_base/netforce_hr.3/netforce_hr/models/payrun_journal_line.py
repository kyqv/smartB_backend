from netforce.model import Model, fields, get_model

class PayRunJournalLine(Model):
    _name="hr.payrun.journal.line"
    _transient=True

    _fields={
        "payrun_journal_id": fields.Many2One("hr.payrun.journal","Payrun Journal",required=True,on_delete="cascade"),
        'description': fields.Text("Description"),
        'debit': fields.Decimal("Debit"),
        'credit': fields.Decimal("Credit"),
        'account_id': fields.Many2One("account.account","Account",condition=[['type','!=','view']]),
    }
     
    _order="debit desc"

PayRunJournalLine.register()
