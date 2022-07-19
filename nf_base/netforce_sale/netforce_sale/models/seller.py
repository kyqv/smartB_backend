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


class Seller(Model):
    _name = "seller"
    _string = "Seller"
    _fields = {
        "name": fields.Char("Name",required=True,search=True),
        "code": fields.Char("Code",search=True),
        "employee_id": fields.Many2One("hr.employee","Employee",search=True),
        "commissions": fields.One2Many("seller.commission","seller_id","Commissions"),
    }
    _order = "name"

    def calc_commission(self,ids,date_from=None,date_to=None,context={}):
        obj=self.browse(ids[0])
        cond=[["seller_id","=",obj.id],["state","in",["confirmed","done"]]]
        if date_from:
            cond.append(["date",">=",date_from])
        if date_to:
            cond.append(["date","<=",date_to])
        cust_totals={}
        for sale in get_model("sale.order").search_browse(cond):
            amt=sale.amount_total
            cust_id=sale.contact_id.id
            cust_totals.setdefault(cust_id,0)
            cust_totals[cust_id]+=amt
        com_total=0
        for cust_id,cust_total in cust_totals.items():
            found_com=None
            for com in obj.commissions:
                if com.customer_id and cust_id!=com.customer_id.id:
                    continue
                found_com=com
                break
            if found_com:
                amt_above=cust_total-(com.min_amount or 0)
                com_amt=amt_above*(com.commission_percent or 0)/100
                com_total+=com_amt
        return com_total

Seller.register()
