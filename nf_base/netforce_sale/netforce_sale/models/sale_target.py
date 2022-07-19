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
from datetime import *
from dateutil.relativedelta import *
from netforce import database


class SaleTarget(Model):
    _name = "sale.target"
    _string = "Sales Target"
    _fields = {
        "user_id": fields.Many2One("base.user", "Salesman", search=True),
        "prod_categ_id": fields.Many2One("product.categ", "Product Category", search=True),
        "date_from": fields.Date("From Date", required=True),
        "date_to": fields.Date("To Date", required=True, search=True),
        "amount_target": fields.Decimal("Target Amount"),
        "amount_actual": fields.Decimal("Actual Amount", function="get_amount", function_multi=True),
        "amount_expected": fields.Decimal("Expected Amount", function="get_amount", function_multi=True),
        "qty_target": fields.Decimal("Target Qty"),
        "qty_actual": fields.Decimal("Actual Qty", function="get_amount", function_multi=True),
        "qty_expected": fields.Decimal("Expected Qty", function="get_amount", function_multi=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
    }
    _order = "date_from,user_id,prod_categ_id"
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_amount(self, ids, context={}):
        all_vals = {}
        db = database.get_connection()
        for obj in self.browse(ids):
            q = "SELECT SUM(opp.amount) AS amount,SUM(opp.qty) AS qty FROM sale_opportunity opp LEFT JOIN product prod ON prod.id=opp.product_id WHERE opp.state='won' AND opp.date_close>=%s AND opp.date_close<=%s"
            a = [obj.date_from, obj.date_to]
            if obj.user_id:
                q += " AND opp.user_id=%s"
                a.append(obj.user_id.id)
            if obj.prod_categ_id:
                q += " AND prod.categ_id=%s"
                a.append(obj.prod_categ_id.id)
            res_won = db.get(q, *a)

            q = "SELECT SUM(opp.amount*opp.probability/100) AS amount,SUM(opp.qty*opp.probability/100) AS qty FROM sale_opportunity opp LEFT JOIN product prod ON prod.id=opp.product_id WHERE opp.state='open' AND opp.date_close>=%s AND opp.date_close<=%s"
            a = [obj.date_from, obj.date_to]
            if obj.user_id:
                q += " AND opp.user_id=%s"
                a.append(obj.user_id.id)
            if obj.prod_categ_id:
                q += " AND prod.categ_id=%s"
                a.append(obj.prod_categ_id.id)
            res_open = db.get(q, *a)

            vals = {
                "amount_actual": res_won.amount or 0,
                "amount_expected": res_open.amount or 0,
                "qty_actual": res_won.qty or 0,
                "qty_expected": res_open.qty or 0,
            }
            all_vals[obj.id] = vals
        return all_vals

    def gen_targets(self,context={}):
        d0=datetime.today()+relativedelta(day=1)
        d1=datetime.today()+relativedelta(day=31)
        d=d0
        while d<d1:
            t=d.strftime("%Y-%m-%d")
            vals={
                "date_from": t,
                "date_to": t,
            }
            res=self.search([["date_from","=",t]])
            if not res:
                self.create(vals)
            d+=timedelta(days=1)

SaleTarget.register()
