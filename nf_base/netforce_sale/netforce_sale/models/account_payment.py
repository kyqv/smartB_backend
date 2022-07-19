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

# just to trigger sales order 'paid' event...
class Payment(Model):
    _inherit="account.payment"

    def post(self,ids,context={}): 
        sale_ids=[]
        for obj in self.browse(ids):
            if obj.pay_type!="invoice":
                continue
            for line in obj.invoice_lines:
                inv=line.invoice_id
                rel=inv.related_id
                if rel and rel._model=="sale.order":
                    sale_ids.append(rel.id)
                for inv_line in inv.lines:
                    rel=inv_line.related_id
                    if rel and rel._model=="sale.order":
                        sale_ids.append(rel.id)
        sale_ids=list(set(sale_ids))
        unpaid_sale_ids=[]
        for sale in get_model("sale.order").browse(sale_ids):
            if not sale.is_paid:
                unpaid_sale_ids.append(sale.id)
        res=super().post(ids,context=context)
        paid_sale_ids=[]
        for sale in get_model("sale.order").browse(unpaid_sale_ids):
            if sale.is_paid:
                paid_sale_ids.append(sale.id)
        if paid_sale_ids:
            get_model("sale.order").trigger(paid_sale_ids,"paid")
        return res

Payment.register()
