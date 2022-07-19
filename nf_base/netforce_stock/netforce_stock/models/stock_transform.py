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
from netforce.utils import get_data_path
import time


class Transform(Model):
    _name = "stock.transform"
    _string = "Product Transform"
    _name_field = "number"
    _fields = {
        "date": fields.Date("Date", required=True, search=True),
        "number": fields.Char("Number", required=True, search=True),
        "location_id": fields.Many2One("stock.location", "Location", condition=[["type", "=", "internal"]], search=True), # XXX: deprecated
        "journal_id": fields.Many2One("stock.journal", "Journal", search=True),
        "from_product_id": fields.Many2One("product","From Product",search=True,condition=[["type","=","stock"]]),
        "from_lot_id": fields.Many2One("stock.lot","Lot / Serial No.",search=True),
        "from_qty": fields.Decimal("Qty"),
        "from_uom_id": fields.Many2One("uom","UoM"),
        "from_location_id": fields.Many2One("stock.location", "From Location", condition=[["type", "=", "internal"]], search=True),
        "to_product_id": fields.Many2One("product","To Product",search=True,condition=[["type","=","stock"]]),
        "to_lot_id": fields.Many2One("stock.lot","Lot / Serial No.",search=True),
        "to_qty": fields.Decimal("Qty"),
        "to_uom_id": fields.Many2One("uom","UoM"),
        "to_location_id": fields.Many2One("stock.location", "From Location", condition=[["type", "=", "internal"]], search=True),
        "user_id": fields.Many2One("base.user","User"),
        "state": fields.Selection([["draft", "Draft"], ["done", "Completed"], ["voided", "Voided"]], "Status", required=True, search=True),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "notes": fields.Text("Notes"),
        "lines": fields.One2Many("stock.transform.line", "transform_id", "Lines"),
        "lines_in": fields.One2Many("stock.transform.line", "transform_id", "From Products",condition=[["type","=","in"]]),
        "lines_out": fields.One2Many("stock.transform.line", "transform_id", "To Products",condition=[["type","=","out"]]),
        "lines_service": fields.One2Many("stock.transform.line", "transform_id", "Service",condition=[["type","=","service"]]),
        "qty_in": fields.Decimal("Total Input Qty",function="get_total_qty",function_multi=True),
        "qty_out": fields.Decimal("Total Ouput Qty",function="get_total_qty",function_multi=True),
        "qty_diff": fields.Decimal("Qty Difference",function="get_total_qty",function_multi=True),
        "related_id": fields.Reference([["purchase.order", "Purchase Order"],["stock.picking","Goods Receipt/Transfer/Issue"]], "Related To"),
        "picking_id": fields.Many2One("stock.picking","Goods Receipt",condition=[["type","=","in"]]),
        "sale_id": fields.Many2One("sale.order","Sales Order"),
        "purchase_orders": fields.One2Many("purchase.order", "related_id", "Purchase Orders"),
    }
    _order = "date desc,id desc"

    def _get_number(self, context={}):
        seq_id = None
        seq_id = get_model("sequence").find_sequence("stock_transform")
        if not seq_id:
            #return None
            raise Exception("Missing sequence for product transforms")
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "number": _get_number,
    }

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        settings = get_model("settings").browse(1)
        res = get_model("stock.location").search([["type", "=", "transform"]])
        if not res:
            raise Exception("Missing transform location")
        trans_loc_id = res[0]
        journal_id=obj.journal_id.id or settings.transform_journal_id.id
        if not journal_id:
            raise Exception("Missing transform journal")
        move_ids=[]
        for line in obj.lines:
            vals = {
                "journal_id": journal_id,
                "product_id": line.product_id.id,
                "lot_id": line.lot_id.id,
                "qty": line.qty,
                "qty2": line.qty2,
                "uom_id": line.uom_id.id,
                "related_id": "stock.transform,%s"%obj.id,
                "cost_price": line.cost_price,
            }
            if line.type=="in":
                vals.update({
                    "location_from_id": line.location_id.id,
                    "location_to_id": trans_loc_id,
                })
            elif line.type=="out":
                vals.update({
                    "location_from_id": trans_loc_id,
                    "location_to_id": line.location_id.id,
                })
            else:
                continue
            move_id = get_model("stock.move").create(vals)
            move_ids.append(move_id)
            line.write({"move_id":move_id})
        get_model("stock.move").set_done(move_ids)
        obj.write({"state": "done"})

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.stock_moves.delete()
        obj.write({"state": "voided"})

    def to_draft(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.stock_moves.delete()
        obj.write({"state": "draft"})

    def onchange_product(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        prod = get_model("product").browse(prod_id)
        line["uom_id"] = prod.uom_id.id
        line["qty"]=1
        line["location_id"] = prod.locations[0].location_id.id if prod.locations else None
        return data

    def onchange_product_service(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        prod = get_model("product").browse(prod_id)
        line["uom_id"] = prod.uom_id.id
        line["qty"]=1
        line["supplier_id"]=prod.suppliers[0].supplier_id.id if prod.suppliers else None
        line["cost_price"]=prod.purchase_price
        return data

    def delete(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.state=="done":
                raise Exception("Can not delete product transforms in this status")
        super().delete(ids,context=context)

    def get_total_qty(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            qty_in=0
            qty_out=0
            for line in obj.lines:
                if line.type=="in":
                    qty_in+=line.qty
                elif line.type=="out":
                    qty_out+=line.qty
            qty_diff=qty_out-qty_in
            vals[obj.id]={
                "qty_in": qty_in,
                "qty_out": qty_out,
                "qty_diff": qty_diff,
            }
        return vals

    def copy_to_purchase(self, ids, context={}):
        obj = self.browse(ids[0])
        suppliers = {}
        for line in obj.lines:
            if line.type!="service":
                continue
            supplier_id=line.supplier_id.id
            if not supplier_id:
                continue
            suppliers.setdefault(supplier_id, []).append(line)
        if not suppliers:
            raise Exception("No purchase orders to create")
        po_ids = []
        for supplier_id, lines in suppliers.items():
            contact=get_model("contact").browse(supplier_id)
            purch_vals = {
                "contact_id": supplier_id,
                "ref": obj.number,
                "lines": [],
                "pay_term_id": contact.sale_pay_term_id.id,
                "related_id": "stock.transform,%s"%obj.id,
            }
            for line in lines:
                prod=line.product_id
                line_vals = {
                    "product_id": prod.id,
                    "description": prod.name,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "unit_price": line.cost_price,
                    "tax_id": prod.purchase_tax_id.id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            po_ids.append(po_id)
        po_objs = get_model("purchase.order").browse(po_ids)
        return {
            "next": {
                "name": "purchase",
            },
            "flash": "Purchase order created successfully: " + ", ".join([po.number for po in po_objs]),
        }

    def update_cost(self,ids,context={}):
        prod_ids=[]
        for obj in self.browse(ids):
            for line in obj.lines_in:
                prod=line.product_id
                prod_ids.append(prod.id)
        prod_ids=list(set(prod_ids))
        get_model("stock.compute.cost").compute_cost([],context={"product_ids":prod_ids})
        for obj in self.browse(ids):
            total=0
            for line in obj.lines_in:
                cost_amt=(line.qty or 0)*(line.cost_price or 0)
                total+=cost_amt
            if obj.lines_out:
                line=obj.lines_out[0]
                cost_price=total/line.qty if line.qty else None
                if not line.move_id:
                    continue
                line.move_id.write({"cost_price":cost_price})

    def assign_lots(self,ids,match_qty2=False,context={}):
        print("assign_lots",ids)
        obj=self.browse(ids[0])
        delete_ids=[]
        for line in obj.lines_in:
            prod=line.product_id
            if line.lot_id:
                continue
            avail_qtys={}
            if not obj.location_id:
                raise Exception("Missing location")
            #for bal in get_model("stock.balance").search_browse([["product_id","=",prod.id],["lot_id","!=",None],["qty_phys",">",0]]):
            for bal in get_model("stock.balance").search_browse([["product_id","=",prod.id],["location_id","child_of",obj.location_id.id],["lot_id","!=",None],["qty_phys",">",0]]):
                if match_qty2 and bal.lot_id.weight:
                    bal_qty = bal.lot_id.weight
                elif match_qty2 and bal.qty2 > 0:
                    bal_qty = bal.qty2
                else:
                    if bal.lot_id.weight:
                        continue    #prevent using lot with weight
                    bal_qty = bal.qty_virt
                if bal_qty is None:
                    continue
                lot_id=bal.lot_id.id
                loc_id=bal.location_id.id
                avail_qtys.setdefault((lot_id,loc_id),0)
                avail_qtys[(lot_id,loc_id)]+=bal_qty
            print("avail_qtys",avail_qtys)
            if not avail_qtys:
                continue
            lots=[]
            for lot_id,loc_id in avail_qtys.keys():
                lot=get_model("stock.lot").browse(lot_id)
                loc=get_model("stock.location").browse(loc_id)
                lots.append((lot,loc))
            if prod.lot_select=="fifo":
                lots.sort(key=lambda l: l[0].received_date)
            elif prod.lot_select=="fefo":
                lots.sort(key=lambda l: l[0].expiry_date)
            elif prod.lot_select=="qty":
                lots.sort(key=lambda l: -avail_qtys[(l[0].id,l[1].id)])
            remain_qty=line.qty2 if match_qty2 else line.qty
            lot_use_qtys={}
            for lot,loc in lots:
                if prod.min_life_remain_percent:
                    if not lot.life_remain_percent or lot.life_remain_percent<prod.min_life_remain_percent:
                        continue
                avail_qty=avail_qtys[(lot.id,loc.id)]
                use_qty=min(avail_qty,remain_qty) # XXX: uom
                lot_use_qtys[(lot.id,loc.id)]=use_qty
                remain_qty-=use_qty
                if remain_qty<=0:
                    break
            if prod.max_lots_per_sale and len(lot_use_qtys)>prod.max_lots_per_sale:
                lot_use_qtys={}
                remain_qty=line.qty2 if match_qty2 else line.qty
            print("lot_use_qtys",lot_use_qtys)
            if remain_qty and remain_qty > 0:
                if match_qty2:
                    line.write({"qty2":remain_qty})
                else:
                    line.write({"qty":remain_qty})
            else:
                delete_ids.append(line.id)
            for (lot_id,loc_id),use_qty in lot_use_qtys.items():
                vals={
                    "transform_id": line.transform_id.id,
                    "type": "in",
                    "product_id": line.product_id.id,
                    "qty": 1 if match_qty2 else use_qty,
                    "qty2": use_qty if match_qty2 else None,
                    "uom_id": line.uom_id.id,
                    "lot_id": lot_id,
                    "location_id": loc_id,
                }
                get_model("stock.transform.line").create(vals)
        if delete_ids:
            get_model("stock.transform.line").delete(delete_ids)


    def assign_lots_qty2(self,ids,context={}):
        self.assign_lots(ids,match_qty2=True,context=context)
        self.assign_lots(ids,context=context)


Transform.register()
