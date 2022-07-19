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
import time


class Claim(Model):
    _name = "product.claim"
    _string = "Claim Bill"
    _name_field = "number"
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "date_received": fields.Date("Received Date", required=True, search=True),
        "product_id": fields.Many2One("product", "Product", required=True, search=True),
        "qty": fields.Decimal("Qty", required=True),
        "contact_id": fields.Many2One("contact", "Contact", required=True, search=True),
        "project_id": fields.Many2One("project", "Project", search=True),
        "defect": fields.Text("Defect"),
        "note": fields.Text("Note"),
        "date_sent_sup": fields.Date("Date sent to supplier"),
        "date_received_sup": fields.Date("Date received from supplier"),
        "repair_details": fields.Text("Repair Details"),
        "state": fields.Selection([["draft", "Draft"], ["approved", "Approved"], ["done", "Completed"], ["voided", "Voided"]], "Status", required=True),
        "pickings": fields.One2Many("stock.picking", "related_id", "Pickings"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "warranty": fields.Boolean("Under Warranty"),
        "cause_damage": fields.Selection([["user", "Damaged by user"], ["quality", "Failure due to quality"], ["unidentified", "Unidentified"]], "Cause of damage"),
        "repair_process": fields.Selection([["repair_local", "Repair locally"], ["send_supplier", "Send back to supplier"], ["discard", "Discard"]], "Repair Process"),
        "action_token": fields.Selection([["replace_new", "Replaced by new one"], ["replace_used", "Replaced by used one"], ["replace_charge", "Replaced / charging to customer"], ["repair_charge", "Repaired / charging to customer"]], "Action token"),
        "serial_no": fields.Char("Serial No."),  # XXX deprecated
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "warranty_start": fields.Date("Warranty Start"),
        "warranty_end": fields.Date("Warranty End"),
        "repl_product_id": fields.Many2One("product", "Replacement Product"),
        "repl_qty": fields.Decimal("Replacement Qty"),
    }
    _order = "number"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence("claim")
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
        "date_received": lambda *a: time.strftime("%Y-%m-%d"),
        "state": "draft",
    }

    def approve(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "approved"})

    def set_done(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "done"})

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "voided"})

Claim.register()
