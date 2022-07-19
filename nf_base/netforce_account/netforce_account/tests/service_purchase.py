from netforce.test import TestCase
from netforce.model import get_model
from datetime import *
import time

class Test(TestCase):
    _name="service.sale"
    _description="Service purchase invoice and payment"

    def test_run(self):
        # create invoice
        vals={
            "type": "in",
            "inv_type": "invoice",
            "partner_id": get_model("partner").search([["name","=","ABC Food"]])[0],
            "date": time.strftime("%Y-%m-%d"),
            "due_date": (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"),
            "tax_type": "tax_ex",
            "lines": [("create",{
                "description": "Training",
                "qty": 1,
                "unit_price": 1000,
                "account_id": get_model("account.account").search([["name","=","Service Fee"]])[0],
                "tax_id": get_model("account.tax.rate").search([["name","=","Purchase Service - Company"]])[0],
                "amount": 1000,
            })],
        }
        inv_id=get_model("account.invoice").create(vals,context={"type":"in","inv_type":"invoice"})
        inv=get_model("account.invoice").browse(inv_id)
        inv.post()
        self.assertEqual(inv.state,"waiting_payment")
        move=inv.move_id
        self.assertEqual(move.lines[0].account_id.name,"Accounts Payable")
        self.assertEqual(move.lines[0].credit,1070)
        self.assertEqual(move.lines[0].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[1].account_id.name,"Suspend Input VAT")
        self.assertEqual(move.lines[1].debit,70)
        self.assertEqual(move.lines[1].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[1].tax_base,1000)
        self.assertIsNone(move.lines[1].tax_no)
        self.assertEqual(move.lines[2].account_id.name,"Service Fee")
        self.assertEqual(move.lines[2].debit,1000)

        # create payment
        vals={
            "partner_id": get_model("partner").search([["name","=","ABC Food"]])[0],
            "type": "out",
            "pay_type": "invoice",
            "date": time.strftime("%Y-%m-%d"),
            "account_id": get_model("account.account").search([["name","=","Saving Account -Kbank"]])[0],
            "lines": [("create",{
                "invoice_id": inv_id,
                "amount": 1070,
                "tax_no": "1234",
            })],
        }
        pmt_id=get_model("account.payment").create(vals,context={"type":"out"})
        get_model("account.payment").post([pmt_id])
        pmt=get_model("account.payment").browse(pmt_id)
        inv=get_model("account.invoice").browse(inv_id)
        self.assertEqual(pmt.state,"posted")
        self.assertEqual(inv.state,"paid")
        self.assertEqual(pmt.lines[0].tax_no,"1234")
        move=pmt.move_id
        self.assertEqual(move.lines[0].account_id.name,"Saving Account -Kbank")
        self.assertEqual(move.lines[0].credit,1040)
        self.assertEqual(move.lines[1].account_id.name,"Accounts Payable")
        self.assertEqual(move.lines[1].debit,1070)
        self.assertEqual(move.lines[1].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[2].account_id.name,"Suspend Input VAT")
        self.assertEqual(move.lines[2].credit,70)
        self.assertEqual(move.lines[2].partner_id.id,vals["partner_id"])
        self.assertIsNone(move.lines[2].tax_no)
        self.assertEqual(move.lines[3].account_id.name,"Input VAT")
        self.assertEqual(move.lines[3].debit,70)
        self.assertEqual(move.lines[3].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[3].tax_no,pmt.lines[0].tax_no)
        self.assertEqual(move.lines[4].account_id.name,"Accrued W/H Tax-Company (PND53)")
        self.assertEqual(move.lines[4].credit,30)

Test.register()
