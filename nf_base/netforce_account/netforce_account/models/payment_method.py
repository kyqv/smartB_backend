# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model
from netforce.logger import audit_log


class PaymentMethod(Model):
    _name = "payment.method"
    _string = "Payment Method"
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "code": fields.Char("Code", search=True),
        "sequence": fields.Integer("Sequence"),
        "type": fields.Selection([["cash","Cash"], ["bank", "Bank Transfer"], ["cheque","Cheque"], ["credit_card", "Credit Card"], ["paypal", "Paypal"],["scb_gateway","SCB Gateway"], ["paysbuy","Paysbuy"]], "Type", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "account_id": fields.Many2One("account.account","Account"),
        # TODO: remove all payment method specific fields
        "paypal_url": fields.Selection([["test", "Test URL"], ["production", "Production URL"]], "Server URL"),
        "paypal_user": fields.Char("Username", size=256),
        "paypal_password": fields.Char("Password", size=256),
        "paypal_signature": fields.Char("Signature", size=256),
        "paysbuy_id": fields.Char("Paysbuy ID"),
        "paysbuy_username": fields.Char("Username"),
        "paysbuy_securecode": fields.Char("Secure Code"),
        "paysbuy_resp_back_url": fields.Char("Response back URL"),
        "paysbuy_url": fields.Selection([["test", "Test URL"], ["production", "Production URL"]], "Server URL"),
        "scb_mid": fields.Char("Merchant ID"),
        "scb_terminal": fields.Char("Terminal ID"),
        "scb_url": fields.Selection([["test", "Test URL"], ["production", "Production URL"]], "Server URL"),
        "instructions": fields.Text("Payment Instructions"),
        "require_report": fields.Boolean("Require Report"),
    }
    _order = "sequence,name"

    def start_payment(self,ids,context={}):
        print("PaymentMethod.start_payment")

    def payment_received(self,context={}):
        transaction_no=context.get("transaction_no")
        amount=context.get("amount")
        currency_id=context.get("currency_id")
        pay_type=context.get("type")
        res=get_model("account.invoice").search([["transaction_no","=",transaction_no]])
        if not res:
            print("Invoice not found for transaction_no=%s"%transaction_no)
            return
        inv_id=res[0]
        print("Found invoice %d for transaction_no=%s"%(inv_id,transaction_no))
        inv=get_model("account.invoice").browse(inv_id)
        if currency_id and currency_id!=inv.currency_id.id:
            raise Exception("Received invoice payment in wrong currency (pmt: %s, inv: %s)"%(currency_id,inv.currency_id.id))
        method=inv.pay_method_id
        if not method:
            raise Exception("Missing invoice payment method")
        if method.type!=pay_type:
            raise Exception("Received invoice payment with wrong method (pmt: %s, inv: %s)"%(pay_type,method.type))
        audit_log("Payment received: transaction_no=%s"%transaction_no)
        res=get_model("account.payment").search([["transaction_no","=",transaction_no]])
        if res:
            audit_log("Payment already recorded: transaction_no=%s"%transaction_no)
            pmt_id=res[0]
        else:
            audit_log("Recording new payment: transaction_no=%s"%transaction_no)
            if not method.account_id:
                raise Exception("Missing account for payment method %s"%method.name)
            pmt_vals={
                "type": "in",
                "pay_type": "invoice",
                "contact_id": inv.contact_id.id,
                "account_id": method.account_id.id,
                "lines": [],
                "company_id": inv.company_id.id,
                "transaction_no": transaction_no,
            }
            line_vals={
                "invoice_id": inv_id,
                "amount": amount,
            }
            pmt_vals["lines"].append(("create",line_vals))
            pmt_id=get_model("account.payment").create(pmt_vals,context={"type": "in"})
            get_model("account.payment").post([pmt_id])
        return {
            "next_url": "/ui#name=payment&mode=form&active_id=%d"%pmt_id,
        }

    def payment_pending(self,context={}):
        transaction_no=context.get("transaction_no")
        res=get_model("account.invoice").search([["transaction_no","=",transaction_no]])
        if not res:
            return
        inv_id=res[0]
        return {
            "next_url": "/ui#name=view_invoice&active_id=%d"%inv_id,
        }

    def payment_error(self,context={}):
        transaction_no=context.get("transaction_no")
        res=get_model("account.invoice").search([["transaction_no","=",transaction_no]])
        if not res:
            return
        inv_id=res[0]
        return {
            "next_url": "/ui#name=view_invoice&active_id=%d"%inv_id,
        }

PaymentMethod.register()
