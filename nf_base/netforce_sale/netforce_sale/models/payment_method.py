from netforce.model import Model,fields,get_model
from netforce import database
from netforce.logger import audit_log

class PaymentMethod(Model):
    _inherit="payment.method"

    def payment_received(self,context={}):
        res=super().payment_received(context=context)
        if res:
            return res
        transaction_no=context.get("transaction_no")
        audit_log("Payment received: transaction_no=%s"%transaction_no)
        pay_type=context.get("type")
        res=get_model("sale.order").search([["transaction_no","=",transaction_no]])
        if not res:
            print("Sales order not found for transaction_no=%s"%transaction_no)
            return
        sale_id=res[0]
        print("Found sales order %d for transaction_no=%s"%(sale_id,transaction_no))
        sale=get_model("sale.order").browse(sale_id)
        if not sale.is_paid:
            method=sale.pay_method_id
            if not method:
                raise Exception("Missing sales order payment method")
            if method.type!=pay_type:
                raise Exception("Received sales order payment with wrong method (pmt: %s, sale: %s)"%(pay_type,method.type))
            audit_log("Creating payment for sales order %s: transaction_no=%s"%(sale.number,transaction_no))
            sale.payment_received(context=context)
        settings=get_model("ecom2.settings").browse(1) # XXX: change this
        if settings.ecom_return_url:
            url=settings.ecom_return_url+str(sale_id)
        else:
            url="/ui#name=sale&mode=form&active_id=%d"%sale_id
        return {
            "next_url": url,
        }

    def payment_pending(self,context={}):
        res=super().payment_pending(context=context)
        if res:
            return res
        transaction_no=context.get("transaction_no")
        res=get_model("sale.order").search([["transaction_no","=",transaction_no]])
        if not res:
            return
        sale_id=res[0]
        settings=get_model("ecom2.settings").browse(1) # XXX: change this
        if settings.ecom_return_url:
            url=settings.ecom_return_url+str(sale_id)
        else:
            url="/ui#name=sale&mode=form&active_id=%d"%sale_id
        return {
            "next_url": url,
        }

    def payment_error(self,context={}):
        res=super().payment_error(context=context)
        if res:
            return res
        transaction_no=context.get("transaction_no")
        res=get_model("sale.order").search([["transaction_no","=",transaction_no]])
        if not res:
            return
        sale_id=res[0]
        settings=get_model("ecom2.settings").browse(1)
        if settings.ecom_return_url:
            url=settings.ecom_return_url+str(sale_id)
        else:
            url="/ui#name=sale&mode=form&active_id=%d"%sale_id
        return {
            "next_url": url,
        }

PaymentMethod.register()
