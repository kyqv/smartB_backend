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


class LandedCostAlloc(Model):
    _name = "landed.cost.alloc"
    _fields = {
        "landed_id": fields.Many2One("landed.cost","Landed Cost",required=True,on_delete="cascade"),
        "move_id": fields.Many2One("stock.move","Stock Movement",required=True),
        "date": fields.DateTime("Date",function="_get_related",function_context={"path":"move_id.date"}),
        "picking_id": fields.Many2One("stock.picking","Goods Receipt",function="_get_related",function_context={"path":"move_id.picking_id"}),
        "contact_id": fields.Many2One("contact","Contact",function="_get_related",function_context={"path":"move_id.picking_id.contact_id"}),
        "product_id": fields.Many2One("product","Product",function="_get_related",function_context={"path":"move_id.product_id"}),
        "qty": fields.Decimal("Qty",function="_get_related",function_context={"path":"move_id.qty"}),
        "uom_id": fields.Many2One("uom","UoM",function="_get_related",function_context={"path":"move_id.uom_id"}),
        "cost_price": fields.Decimal("Base Cost Price",function="_get_related",function_context={"path":"move_id.cost_price"}),
        "cost_amount": fields.Decimal("Base Cost Amount",function="_get_related",function_context={"path":"move_id.cost_amount"}),
        "location_from_id": fields.Many2One("stock.location","From Location",function="_get_related",function_context={"path":"move_id.location_from_id"}),
        "location_to_id": fields.Many2One("stock.location","To Location",function="_get_related",function_context={"path":"move_id.location_to_id"}),
        "track_id": fields.Many2One("account.track.categ","Track",function="_get_related",function_context={"path":"move_id.track_id"}),
        "qty_stock_gr": fields.Decimal("Qty In Stock GR",function="_get_qty_stock",function_multi=True),
        "qty_stock_lc": fields.Decimal("Qty In Stock LC",function="_get_qty_stock",function_multi=True),
        "est_ship": fields.Decimal("Est. Shipping"),
        "est_duty": fields.Decimal("Est. Duty"),
        "act_ship": fields.Decimal("Act. Shipping"),
        "act_duty": fields.Decimal("Act. Duty"),
        "amount": fields.Decimal("Total Alloc. Cost",function="_get_total",function_multi=True),
        "percent": fields.Decimal("Cost Percent",function="_get_total",function_multi=True),
    }

    def _get_qty_stock(self,ids,context={}):
        gr_keys={}
        lc_keys={}
        for obj in self.browse(ids):
            move=obj.move_id
            pick_id=move.picking_id.id
            lc_id=obj.landed_id.id
            k=(move.product_id.id,move.lot_id.id,move.location_to_id.id,move.container_to_id.id)
            gr_keys.setdefault(pick_id,[]).append(k)
            lc_keys.setdefault(lc_id,[]).append(k)
        gr_bals={}
        for pick_id,keys in gr_keys.items():
            pick=get_model("stock.picking").browse(pick_id)
            gr_bals[pick_id]=get_model("stock.balance").compute_key_balances(keys,context={"date_to": pick.date})
        lc_bals={}
        for lc_id,keys in lc_keys.items():
            lc=get_model("landed.cost").browse(lc_id)
            lc_bals[lc_id]=get_model("stock.balance").compute_key_balances(keys,context={"date_to": lc.date})
        print("gr_bals",gr_bals)
        print("lc_bals",lc_bals)
        vals={}
        for obj in self.browse(ids):
            move=obj.move_id
            pick_id=move.picking_id.id
            lc_id=obj.landed_id.id
            k=(move.product_id.id,move.lot_id.id,move.location_to_id.id,move.container_to_id.id)
            qty_gr=gr_bals[pick_id][k][0]
            qty_lc=lc_bals[lc_id][k][0]
            vals[obj.id]={
                "qty_stock_gr": qty_gr,
                "qty_stock_lc": qty_lc,
            }
        return vals

    def _get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            amt+=obj.est_ship or 0
            amt+=obj.est_duty or 0
            amt+=obj.act_ship or 0
            amt+=obj.act_duty or 0
            vals[obj.id]={
                "amount": amt,
                "percent": amt*100/obj.cost_amount if obj.cost_amount else None,
            }
        return vals

LandedCostAlloc.register()
