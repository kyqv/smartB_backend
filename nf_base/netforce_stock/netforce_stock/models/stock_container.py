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
from netforce.database import get_connection
import re


def get_totals(date_from, date_to, product_id=None, lot_id=None, location_id=None, container_id=None):
    q = "SELECT product_id,lot_id,location_from_id,container_from_id,location_to_id,container_to_id,uom_id,SUM(qty) AS total_qty,SUM(unit_price*qty) AS total_amt,SUM(qty2) AS total_qty2 FROM stock_move WHERE state='done'"
    q_args = []
    if date_from:
        q += " AND date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND date<=%s"
        q_args.append(date_to + " 23:59:59")
    if product_id:
        q += " AND product_id=%s"
        q_args.append(product_id)
    if lot_id:
        q += " AND lot_id=%s"
        q_args.append(lot_id)
    if location_id:
        q += " AND (location_from_id=%s OR location_to_id=%s)"
        q_args += [location_id, location_id]
    if container_id:
        q += " AND (container_from_id=%s OR container_to_id=%s)"
        q_args += [container_id, container_id]
    q += " GROUP BY product_id,lot_id,location_from_id,container_from_id,location_to_id,container_to_id,uom_id"
    db = get_connection()
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        prod = get_model("product").browse(r.product_id)
        uom = get_model("uom").browse(r.uom_id)
        qty = r.total_qty * uom.ratio / prod.uom_id.ratio
        amt = r.total_amt or 0
        qty2 = r.total_qty2 or 0
        k = (r.product_id, r.lot_id, r.location_from_id, r.container_from_id, r.location_to_id, r.container_to_id)
        tot = totals.setdefault(k, [0, 0, 0])
        tot[0] += qty
        tot[1] += amt
        tot[2] += qty2
    return totals


class StockContainer(Model):
    _name = "stock.container"
    _string = "Container"
    _name_field = "number"
    _key = ["number"]
    _audit_log=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "description": fields.Text("Description", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "pickings": fields.One2Many("stock.picking", "container_id", "Pickings"), # XXX: deprecated
        "contents": fields.Json("Contents",function="get_contents"),
        "lot_numbers": fields.Text("Lot Numbers Range",function="get_lot_numbers"),
        "stock_moves": fields.One2Many("stock.move","container_id","Stock Moves"),
        "validate_lines": fields.One2Many("pick.validate.line","container_id","Validate Lines"),
        "stock_balances": fields.One2Many("stock.balance","container_id","Stock Balances"),
    }
    _order = "number desc"

    def _get_number(self, context={}):
        seq_id=context.get("sequence_id")
        if not seq_id:
            seq_id = get_model("sequence").find_sequence(type="stock_container")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults = {
        "number": _get_number,
    }

    # XXX: FIXME
    def get_contents(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            contents=[]
            for move in obj.stock_moves:
                if move.state!="done":
                    continue
                if move.location_from_id.type=="internal" and move.location_to_id.type!="internal":
                    contents.append({
                        "product_id": move.product_id.id,
                        "lot_id": move.lot_id.id,
                        "qty": move.qty,
                        "uom_id": move.uom_id.id,
                    })
            vals[obj.id]=contents
        return vals

    # XXX: FIXME
    def get_lot_numbers(self,ids,context={}):
        vals={}
        for obj in self.browse(ids,context=context):
            lot_nums=[]
            for bal in obj.stock_balances:
                if not bal.lot_id:
                    continue
                lot_nums.append(bal.lot_id.number)
            lot_nums=list(set(lot_nums))
            lot_nums.sort()
            lot_ranges=[]
            last_range=[]
            prev_n=None
            for lot_num in lot_nums:
                try:
                    n=int(re.sub(r"[^\d]+","",lot_num))
                except:
                    n=None
                if n is not None and prev_n is not None and n==prev_n+1:
                    last_range.append(lot_num)
                else:
                    if last_range:
                        if len(last_range)>2:
                            lot_ranges.append("%s-%s"%(last_range[0],last_range[-1]))
                        else:
                            lot_ranges+=last_range
                    last_range=[lot_num]
                prev_n=n
            if last_range:
                if len(last_range)>2:
                    lot_ranges.append("%s-%s"%(last_range[0],last_range[-1]))
                else:
                    lot_ranges+=last_range
            vals[obj.id]=", ".join(lot_ranges)
        return vals

StockContainer.register()
