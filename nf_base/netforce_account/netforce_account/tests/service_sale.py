from netforce.test import TestCase
from netforce.model import get_model
from datetime import *
import time

class Test(TestCase):
    _name="service.sale"
    _description="Service sale invoice and payment"

    def test_run(self):
        # create invoice
        vals={
            "type": "out",
            "inv_type": "invoice",
            "partner_id": get_model("partner").search([["name","=","ABC Food"]])[0],
            "date": time.strftime("%Y-%m-%d"),
            "due_date": (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"),
            "tax_type": "tax_ex",
            "lines": [("create",{
                "description": "Training",
                "qty": 1,
                "unit_price": 1000,
                "account_id": get_model("account.account").search([["name","=","Service Income"]])[0],
                "tax_id": get_model("account.tax.rate").search([["name","=","Service Sales"]])[0],
                "amount": 1000,
            })],
        }
        inv_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"invoice"})
        inv=get_model("account.invoice").browse(inv_id)
        inv.post()
        self.assertEqual(inv.state,"waiting_payment")
        move=inv.move_id
        self.assertEqual(move.lines[0].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[0].debit,1070)
        self.assertEqual(move.lines[0].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[1].account_id.name,"Suspend Output Vat")
        self.assertEqual(move.lines[1].credit,70)
        self.assertEqual(move.lines[1].tax_base,1000)
        self.assertIsNone(move.lines[1].tax_no)
        self.assertEqual(move.lines[1].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[2].account_id.name,"Service Income")
        self.assertEqual(move.lines[2].credit,1000)

        # create payment
        vals={
            "partner_id": get_model("partner").search([["name","=","ABC Food"]])[0],
            "type": "in",
            "pay_type": "invoice",
            "date": time.strftime("%Y-%m-%d"),
            "account_id": get_model("account.account").search([["name","=","Saving Account -Kbank"]])[0],
            "lines": [("create",{
                "invoice_id": inv_id,
                "amount": 1070,
            })],
        }
        pmt_id=get_model("account.payment").create(vals,context={"type":"in"})
        get_model("account.payment").post([pmt_id])
        pmt=get_model("account.payment").browse(pmt_id)
        inv=get_model("account.invoice").browse(inv_id)
        self.assertEqual(pmt.state,"posted")
        self.assertEqual(inv.state,"paid")
        self.assertIsNotNone(pmt.lines[0].tax_no)
        move=pmt.move_id
        self.assertEqual(move.lines[0].account_id.name,"Saving Account -Kbank")
        self.assertEqual(move.lines[0].debit,1040)
        self.assertEqual(move.lines[1].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[1].credit,1070)
        self.assertEqual(move.lines[1].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[2].account_id.name,"Suspend Output Vat")
        self.assertEqual(move.lines[2].debit,70)
        self.assertEqual(move.lines[2].tax_base,1000)
        self.assertEqual(move.lines[2].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[3].account_id.name,"Output Vat")
        self.assertEqual(move.lines[3].credit,70)
        self.assertEqual(move.lines[3].tax_base,1000)
        self.assertEqual(move.lines[3].tax_no,pmt.lines[0].tax_no)
        self.assertEqual(move.lines[3].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[4].account_id.name,"Withholding Income Tax")
        self.assertEqual(move.lines[4].debit,30)
        self.assertEqual(move.lines[4].tax_base,1000)
        self.assertIsNone(move.lines[4].tax_no)
        self.assertEqual(move.lines[4].partner_id.id,vals["partner_id"])

Test.register()
