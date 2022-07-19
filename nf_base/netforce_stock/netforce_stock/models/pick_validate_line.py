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


class PickValidateLine(Model):
    _name = "pick.validate.line"
    _string="Item Validation"
    _fields = {
        "validate_id": fields.Many2One("pick.validate", "Picking Validation", on_delete="cascade"),
        "move_id": fields.Many2One("stock.move","Stock Move"),
        "product_id": fields.Many2One("product", "Product", required=True, readonly=True, on_delete="cascade"),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "container_id": fields.Many2One("stock.container", "Container"),
        "lot": fields.Char("Lot / Serial Number"),
        "qty": fields.Decimal("Qty", required=True, scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "qty2": fields.Decimal("Gross Weight", scale=6),
        "container_to_id": fields.Many2One("stock.container", "To Container"),
        "pick_id": fields.Many2One("stock.picking","Stock Picking"),
        "lot_no": fields.Char("Lot / Serial Number"),
        "container_no": fields.Char("Container Number"),
        "packaging_id": fields.Many2One("stock.packaging", "Packaging"),
        "container_type_id": fields.Many2One("stock.container.type", "Container Type"),
        "net_weight": fields.Decimal("Net Weight", function="get_net_weight"),
    }

    def default_get(self,field_names=None, context={}, **kw):
        move_id=context.get("move_id")
        if not move_id:
            return {}
        move=get_model("stock.move").browse(move_id)
        return {
            "move_id": [move.id,move.name_get()[0][1]],
            "product_id": [move.product_id.id,move.product_id.name_get()[0][1]], # XXX: simplify this
            "lot_id": [move.lot_id.id,move.lot_id.name_get()[0][1]] if move.lot_id else None,
            "qty": move.qty,
            "uom_id": [move.uom_id.id,move.uom_id.name_get()[0][1]],
            "qty2": move.qty2,
            "pick_id": [move.picking_id.id,move.picking_id.name_get()[0][1]],
        }

    def validate(self,ids,context={}):
        print("validate")

    def create(self,vals,context={},**kw):
        create_lot=context.get("create_lot")
        lot_no=context.get("lot_no")
        print("XXX lot_no='%s'"%lot_no)
        if create_lot or lot_no:
            lot_id=None
            if lot_no:
                res=get_model("stock.lot").search(["or",["number","=",lot_no],["url","=",lot_no]])
                if res:
                    lot_id=res[0]
            if not lot_id:
                prod_id=vals["product_id"]
                prod=get_model("product").browse(prod_id)
                if prod.prevent_new_lot:
                    raise Exception("Not allowed to create new lots for product '%s'"%prod.name)
                lot_vals={
                    "number": lot_no,
                    "product_id": prod_id,
                }
                lot_id=get_model("stock.lot").create(lot_vals)
            vals["lot_id"]=lot_id
        cont_no=context.get("container_no")
        if cont_no:
            cont_vals={}
            cont_vals["number"]=cont_no
            res=get_model("stock.container").search([["number","=",cont_vals["number"]]])
            if res:
                cont_id=res[0]
            else:
                cont_id=get_model("stock.container").create(cont_vals)
            vals["container_id"]=cont_id
        prod_id=context.get("product_id") or vals.get("product_id")
        if prod_id:
            prod=get_model("product").browse(prod_id)
            if prod.pos_packaging_id:
                vals["packaging_id"]=prod.pos_packaging_id.id
            if prod.pos_container_type_id:
                vals["container_type_id"]=prod.pos_container_type_id.id
            #if prod.require_lot and not vals.get("lot_id"): # XXX: talaypu
            #    raise Exception("Missing lot for product %s"%prod.code)
        new_id=super().create(vals,context=context,**kw)
        obj=self.browse(new_id)
        if obj.product_id.require_unique_lot and obj.lot_id:
            obj.lot_id.check_unique_lots_validate()
        return new_id

    def add_line(self,vals,context={},**kw):
        cont_id=None
        contents=None
        cont_no=context.get("container_no")
        if cont_no:
            res=get_model("stock.container").search([["number","=",cont_no]])
            if res:
                cont_id=res[0]
                cont=get_model("stock.container").browse(cont_id)
                contents=cont.contents
        prod_id=vals.get("product_id")
        prod=get_model("product").browse(prod_id) if prod_id else None
        if contents:
            for cont_vals in contents:
                vals={
                    "pick_id": vals["pick_id"],
                    "move_id": vals["move_id"],
                    "product_id": cont_vals["product_id"],
                    "lot_id": cont_vals["lot_id"],
                    "container_id": cont_id,
                    "qty": cont_vals["qty"],
                    "uom_id": cont_vals["uom_id"],
                }
                cont_prod_id=cont_vals["product_id"]
                cont_prod=get_model("product").browse(cont_prod_id)
                if not prod_id:
                    prod_id=cont_prod_id
                    prod=cont_prod
                if cont_prod_id!=prod_id:
                    raise Exception("Invalid product: product='%s', container product='%s'"%(prod.name,cont_prod.name))
                new_id=super().create(vals,context=context,**kw)
        else:
            new_id=self.create(vals,context=context,**kw)
        return {
            "pick_validate_line_id": new_id,
            "product_id": prod_id,
        }

    def get_net_weight(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            w=None
            if obj.qty2:
                w=obj.qty2-(obj.packaging_id.packaging_weight or 0)*obj.qty-(obj.container_type_id.weight or 0)
            vals[obj.id]=w
        return vals

PickValidateLine.register()
