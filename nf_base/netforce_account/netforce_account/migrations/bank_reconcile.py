from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.bank_reconcile"
    _version="1.95.0"

    def migrate(self):
        recs={}
        for obj in get_model("account.move.line").search_browse([["statement_line_id","!=",None]]):
            st_line_id=obj.statement_line_id.id
            recs.setdefault(st_line_id,[]).append(obj.id)
        for st_line_id,acc_line_ids in recs.items():
            rec_id=get_model("account.bank.reconcile").create({})
            get_model("account.statement.line").write([st_line_id],{"bank_reconcile_id":rec_id})
            get_model("account.move.line").write(acc_line_ids,{"bank_reconcile_id":rec_id})

Migration.register()
