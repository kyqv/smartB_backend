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


class BarcodeValidateLine(Model):
    _name = "barcode.validate.line"
    _transient = True
    _fields = {
        "wizard_id": fields.Many2One("barcode.validate", "Wizard", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", required=True),
        "qty_planned": fields.Decimal("Planned Qty", required=True, readonly=True),
        "qty_actual": fields.Decimal("Validated Qty"),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "container_to_id": fields.Many2One("stock.container", "Container"),
        "location_from_id": fields.Many2One("stock.location", "From Location"),
        "location_to_id": fields.Many2One("stock.location", "To Location"),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["job", "Service Order"], ["product.claim", "Claim Bill"], ["product.borrow", "Borrow Request"], ["stock.picking", "Picking"]], "Related To"),
    }

BarcodeValidateLine.register()
