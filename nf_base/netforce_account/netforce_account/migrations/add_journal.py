from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.add_journal"
    _version="1.69.0"

    def migrate(self):
        res=get_model("account.journal").search([])
        if res:
            print("Journals already created")
            return
        vals={
            "name": "General",
            "type": "general",
        }
        gen_id=get_model("account.journal").create(vals)
        vals={
            "name": "Sales",
            "type": "sale",
        }
        sale_id=get_model("account.journal").create(vals)
        vals={
            "name": "Purchases",
            "type": "purchase",
        }
        purch_id=get_model("account.journal").create(vals)
        vals={
            "name": "Receipts",
            "type": "pay_in",
        }
        pay_in_id=get_model("account.journal").create(vals)
        vals={
            "name": "Disbursements",
            "type": "pay_out",
        }
        pay_out_id=get_model("account.journal").create(vals)
        vals={
            "general_journal_id": gen_id,
            "sale_journal_id": sale_id,
            "purchase_journal_id": purch_id,
            "pay_in_journal_id": pay_in_id,
            "pay_out_journal_id": pay_out_id,
        }
        get_model("company").write([1],vals)
        for move in get_model("account.move").search_browse([]):
            journal_id=gen_id
            if move.invoice_id:
                if move.invoice_id.type=="out":
                    journal_id=sale_id
                elif move.invoice_id.type=="in":
                    journal_id=purch_id
            elif move.payment_id:
                if move.payment_id.type=="in":
                    journal_id=pay_in_id
                elif move.payment_id.type=="out":
                    journal_id=pay_out_id
            move.write({"journal_id": journal_id})

Migration.register()
