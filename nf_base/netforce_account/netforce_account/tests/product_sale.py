from netforce.test import TestCase
from netforce.model import get_model
from datetime import *
import time

class Test(TestCase):
    _name="product.sale"
    _description="Product sale invoice and payment"

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
                "description": "Test product",
                "qty": 1,
                "unit_price": 1000,
                "account_id": get_model("account.account").search([["name","=","Sales Income"]])[0],
                "tax_id": get_model("account.tax.rate").search([["name","=","Sales Goods"]])[0],
                "amount": 1000,
            })],
        }
        inv_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"invoice"})
        get_model("account.invoice").post([inv_id])
        inv=get_model("account.invoice").browse(inv_id)
        self.assertEqual(inv.state,"waiting_payment")
        self.assertIsNotNone(inv.tax_no)
        move=inv.move_id
        self.assertEqual(move.lines[0].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[0].debit,1070)
        self.assertEqual(move.lines[0].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[1].account_id.name,"Output Vat")
        self.assertEqual(move.lines[1].credit,70)
        self.assertEqual(move.lines[1].partner_id.id,vals["partner_id"])
        self.assertEqual(move.lines[1].tax_comp_id.name,"Output VAT")
        self.assertEqual(move.lines[1].tax_base,1000)
        self.assertEqual(move.lines[1].tax_no,inv.tax_no)
        self.assertEqual(move.lines[2].account_id.name,"Sales Income")
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
        move=pmt.move_id
        self.assertEqual(move.lines[0].account_id.name,"Saving Account -Kbank")
        self.assertEqual(move.lines[0].debit,1070)
        self.assertEqual(move.lines[1].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[1].credit,1070)
        self.assertEqual(move.lines[1].partner_id.id,vals["partner_id"])

Test.register()
