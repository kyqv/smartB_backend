from netforce.test import TestCase
from netforce.model import get_model
from datetime import *
import time

class Test(TestCase):
    _name="service.sale.multi.pay"
    _description="Service sale payment for 2 invoices"

    def test_run(self):
        # create invoice #1
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
        inv1_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"invoice"})
        inv=get_model("account.invoice").browse(inv1_id)
        inv.post()
        self.assertEqual(inv.state,"waiting_payment")
        move=inv.move_id
        self.assertEqual(move.lines[0].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[0].debit,1070)
        self.assertEqual(move.lines[1].account_id.name,"Suspend Output Vat")
        self.assertEqual(move.lines[1].credit,70)
        self.assertEqual(move.lines[2].account_id.name,"Service Income")
        self.assertEqual(move.lines[2].credit,1000)

        # create invoice #2
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
                "unit_price": 2000,
                "account_id": get_model("account.account").search([["name","=","Service Income"]])[0],
                "tax_id": get_model("account.tax.rate").search([["name","=","Service Sales"]])[0],
                "amount": 2000,
            })],
        }
        inv2_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"invoice"})
        inv=get_model("account.invoice").browse(inv2_id)
        inv.post()
        self.assertEqual(inv.state,"waiting_payment")
        move=inv.move_id
        self.assertEqual(move.lines[0].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[0].debit,2140)
        self.assertEqual(move.lines[1].account_id.name,"Suspend Output Vat")
        self.assertEqual(move.lines[1].credit,140)
        self.assertEqual(move.lines[2].account_id.name,"Service Income")
        self.assertEqual(move.lines[2].credit,2000)

        # create payment for invoices #1 and #2
        vals={
            "partner_id": get_model("partner").search([["name","=","ABC Food"]])[0],
            "type": "in",
            "pay_type": "invoice",
            "date": time.strftime("%Y-%m-%d"),
            "account_id": get_model("account.account").search([["name","=","Saving Account -Kbank"]])[0],
            "lines": [
                ("create",{
                    "invoice_id": inv1_id,
                    "amount": 1070,
                }),
                ("create",{
                    "invoice_id": inv2_id,
                    "amount": 2140,
                }),
            ],
        }
        pmt_id=get_model("account.payment").create(vals,context={"type":"in"})
        pmt=get_model("account.payment").browse(pmt_id)
        pmt.post()
        inv1=get_model("account.invoice").browse(inv1_id)
        inv2=get_model("account.invoice").browse(inv2_id)
        self.assertEqual(pmt.state,"posted")
        self.assertEqual(inv1.state,"paid")
        self.assertEqual(inv2.state,"paid")
        move=pmt.move_id
        self.assertEqual(move.lines[0].account_id.name,"Saving Account -Kbank")
        self.assertEqual(move.lines[0].debit,3120)
        self.assertEqual(move.lines[1].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[1].credit,1070)
        self.assertEqual(move.lines[2].account_id.name,"Suspend Output Vat")
        self.assertEqual(move.lines[2].debit,70)
        self.assertEqual(move.lines[3].account_id.name,"Output Vat")
        self.assertEqual(move.lines[3].credit,70)
        self.assertEqual(move.lines[4].account_id.name,"Account receivables - Trade")
        self.assertEqual(move.lines[4].credit,2140)
        self.assertEqual(move.lines[5].account_id.name,"Suspend Output Vat")
        self.assertEqual(move.lines[5].debit,140)
        self.assertEqual(move.lines[6].account_id.name,"Output Vat")
        self.assertEqual(move.lines[6].credit,140)
        self.assertEqual(move.lines[7].account_id.name,"Withholding Income Tax")
        self.assertEqual(move.lines[7].debit,90)

Test.register()
