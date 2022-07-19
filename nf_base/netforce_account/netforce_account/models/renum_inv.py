from netforce.model import Model, fields, get_model
from netforce import tasks

class RenumInv(Model):
    _name = "renum.inv"
    _transient = True
    _fields = {
        "date_from": fields.Date("From Date",required=True),
        "date_to": fields.Date("To Date",required=True),
        "state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Waiting Approval"), ("waiting_payment", "Waiting Payment"), ("paid", "Paid"), ("voided", "Voided")], "Status"),
        "prefix": fields.Char("Current Prefix",required=True),
        "num_from": fields.Integer("From Number"),
        "num_to": fields.Integer("To Number"),
        "prefix_new": fields.Char("New Prefix",required=True),
        "padding": fields.Integer("Padding"),
        "start_num": fields.Integer("Starting Number",required=True),
        "pay_methods": fields.Many2Many("payment.method","Payment Methods"),
        "min_amount": fields.Decimal("Min Amount"),
    }
    _defaults={
        "padding": 4,
    }

    def renum_inv(self,ids,context={}):
        obj=self.browse(ids[0])
        date_from=obj.date_from
        date_to=obj.date_to
        padding=obj.padding or 0
        count=obj.start_num
        if count is None:
            raise Exception("Missing start number")
        job_id=context.get("job_id")
        if obj.pay_methods:
            method_ids=[x.id for x in obj.pay_methods]
        else:
            method_ids=None
        cond=[["type","=","out"],["date",">=",date_from],["date","<=",date_to]]
        # TODO: check SO->inv copy pay method
        #if method_ids:
        #    cond.append(["pay_method_id","in",method_ids])
        if obj.min_amount:
            cond.append(["amount_total",">=",obj.min_amount])
        if obj.state:
            cond.append(["state","=",obj.state])
        inv_ids=get_model("account.invoice").search(cond,order="date,id")
        n=0
        for i,inv in enumerate(get_model("account.invoice").browse(inv_ids)):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(inv_ids),"Renumbering invoice %s of %s."%(i+1,len(inv_ids)))
            num=inv.number or ""
            if not num.startswith(obj.prefix):
                continue
            if method_ids: # XXX: remove this
                order=inv.related_id
                if order._model!="sale.order":
                    continue
                if order.pay_method_id.id not in method_ids:
                    continue
            if not num[len(obj.prefix):].isdigit():
                raise Exception("Invalid number: %s"%num)
            print("old_num",num)
            old_count=int(num[len(obj.prefix):])
            print("old_count",old_count)
            if obj.num_from and old_count<obj.num_from:
                continue
            if obj.num_to and old_count>obj.num_to:
                continue
            new_num=obj.prefix_new+"%.*d"%(padding,count)
            print("new_num",new_num)
            inv.write({"number":new_num})
            if inv.move_id:
                inv.move_id.write({"number":new_num})
            count+=1
            n+=1
        if not n:
            raise Exception("No invoices found")
        return {
            "alert": "%d invoices renumbered"%n,
        }

RenumInv.register()
