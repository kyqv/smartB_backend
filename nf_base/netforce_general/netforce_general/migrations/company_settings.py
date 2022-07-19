from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="general.company_settings"
    _version="1.109.0"

    def migrate(self):
        db=get_connection()
        res1=db.get("SELECT * FROM company WHERE id=1")
        res2=db.get("SELECT * FROM settings WHERE id=1")
        if res1 and not res2:
            fnames=[
                "id",
                "name",
                "legal_name",
                "company_type_id",
                "currency_id",
                "account_receivable_id",
                "tax_receivable_id",
                "account_payable_id",
                "tax_payable_id",
                "year_end_day",
                "year_end_month",
                "lock_date",
                "nf_email",
                "currency_gain_id",
                "currency_loss_id",
                "unpaid_claim_id",
                "retained_earnings_account_id",
                "logo",
                "package",
                "version",
                "tax_no",
                "date_format",
                "use_buddhist_date",
                "phone",
                "fax",
                "website",
                "root_url",
                "sale_journal_id",
                "purchase_journal_id",
                "pay_in_journal_id",
                "pay_out_journal_id",
                "general_journal_id",
            ]
            q="INSERT INTO settings ("+",".join([f for f in fnames])+")"
            q+=" SELECT "+",".join([f for f in fnames])
            q+=" FROM company WHERE id=1"
            print("q",q)
            db.execute(q)

Migration.register()
