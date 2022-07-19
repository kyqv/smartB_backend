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
from netforce import access
from netforce.access import get_active_company, get_active_user, set_active_user
from netforce.utils import get_data_path


class PurchaseRequest(Model):
    _name = "purchase.request"
    _string = "Purchase Request"
    _name_field="number"
    _audit_log = True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Ref", search=True),
        "date": fields.Date("Date", required=True, search=True),
        "date_required": fields.Date("Required Date"),
        "company_id": fields.Many2One("company", "Company"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "other_info": fields.Text("Other Info"),
        "employee_id": fields.Many2One("hr.employee", "Employee", search=True),
        "state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Waiting Approval"), ("waiting_po", "Waiting PO"), ("done", "Completed"), ("rejected","Rejected"), ("voided", "Voided")], "Status", required=True),
        "lines": fields.One2Many("purchase.request.line", "request_id", "Lines"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "request_by_id": fields.Many2One("base.user", "Request By", required=True, readonly=True),
        "approve_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "purchase_orders": fields.One2Many("purchase.order","purchase_request_id","Purchase Orders"),
        "department_id": fields.Many2One("hr.department", "Department", search=True),
        "approvals": fields.One2Many("approval","related_id","Approvals"),
    }
    _order = "date desc,number desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="purchase_request")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            user_id = get_active_user()
            set_active_user(1)
            res = self.search([["number", "=", num]])
            set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    def _get_employee(self, context={}):
        user_id = get_active_user()
        res = get_model("hr.employee").search([["user_id", "=", user_id]])
        if not res:
            return None
        return res[0]

    def _get_request_by_id(self, context={}):
        return get_active_user()

    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "number": _get_number,
        "employee_id": _get_employee,
        "company_id": lambda *a: get_active_company(),
        "request_by_id": _get_request_by_id,
    }

    def onchange_product(self, context={}):
        data = context.get('data')
        path = context.get('path')
        line = get_data_path(data, path, parent=True)
        prod = get_model('product').browse(line['product_id'])
        line['description'] = prod.description if prod.description else "-"
        line['uom_id'] = prod.uom_id.id
        line["supplier_id"]=prod.suppliers[0].supplier_id.id if prod.suppliers else None
        return data

    def btn_submit(self, ids, context={}):
        obj = self.browse(ids[0])
        settings=get_model("settings").browse(1)
        for line in obj.lines:
            if settings.pr_require_supplier and not line.supplier_id:
                raise Exception("Missing supplier for '%s'"%line.description)
        obj.write({"state": "waiting_approval"})
        obj.trigger("submit_approve")

    def btn_approve(self, ids, context={}):
        settings = get_model("settings").browse(1)
        if settings.approve_purchase_request and not access.check_permission_other("approve_purchase_request"):
            raise Exception("User does not have permission to approve purchase requests (approve_purchase_request).")
        user_id=access.get_active_user()
        obj = self.browse(ids[0])
        vals={
            "related_id": "purchase.request,%s"%obj.id,
            "user_id": user_id,
            "state": "approved",
            "date_approve": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        res=get_model("approval").search([["related_id","=",vals["related_id"]],["user_id","=",user_id],["state","=","approved"]])
        if res:
            raise Exception("Already approved by user")
        get_model("approval").create(vals)
        obj.write({"state": "waiting_po", "approve_by_id": get_active_user()})
        obj.trigger("approved")

    def btn_reject(self, ids, context={}):
        settings = get_model("settings").browse(1)
        if settings.approve_purchase_request and not access.check_permission_other("approve_purchase_request"):
            raise Exception("User does not have permission to  purchase requests (approve_purchase_request).")
        user_id=access.get_active_user()
        obj = self.browse(ids[0])
        vals={
            "related_id": "purchase.request,%s"%obj.id,
            "user_id": user_id,
            "state": "rejected",
        }
        get_model("approval").create(vals)
        obj.write({"state": "rejected"})
        obj.trigger("rejected")

    def btn_done(self, ids, context={}):
        obj = self.browse(ids)
        obj.write({"state": "done"})

    def btn_reopen(self, ids, context={}):
        obj = self.browse(ids)
        obj.write({"state": "waiting_po"})

    def btn_draft(self, ids, context={}):
        obj = self.browse(ids)
        obj.write({"state": "draft"})

    def btn_void(self, ids, context={}):
        obj = self.browse(ids)
        obj.write({"state": "voided"})

    def copy_to_purchase(self, ids, context={}):
        suppliers = {}
        for obj in self.browse(ids):
            for line in obj.lines:
                prod = line.product_id
                if not prod:
                    continue
                if line.purchase_order_id:
                    raise Exception("Purchase order already created for product %s"%prod.code)
                if line.supplier_id:
                    supplier_id=line.supplier_id.id
                else:
                    if not prod.suppliers:
                        raise Exception("Missing supplier for product '%s'" % prod.name)
                    supplier_id = prod.suppliers[0].supplier_id.id
                suppliers.setdefault(supplier_id, []).append((line.id,prod.id, line.qty, line.uom_id.id, line.description, line.department_id.id))
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
                "purchase_request_id": obj.id,
            }
            for line_id,prod_id, qty, uom_id, desc, department_id in lines:
                prod = get_model("product").browse(prod_id)
                line_vals = {
                    "product_id": prod_id,
                    "description": desc or "/",
                    "qty": qty,
                    "uom_id": uom_id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "department_id": department_id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            for line_id,prod_id, qty, uom_id, desc, department_id in lines:
                get_model("purchase.request.line").write([line_id],{"purchase_order_id":po_id})
            po_ids.append(po_id)
        po_objs = get_model("purchase.order").browse(po_ids)
        return {
            "flash": "Purchase orders created successfully: " + ", ".join([po.number for po in po_objs]),
        }

    def copy(self, ids, context):
        obj = self.browse(ids)[0]
        lines=[]
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "supplier_id": line.supplier_id.id,
            }
            lines.append(("create", line_vals))
        vals={
            "number": obj.number+" (copy)",
            "lines": lines,
            "state": "draft",
        }
        new_id = obj._copy(vals)[0]
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "purchase_request",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Purchase request %s copied to %s" % (obj.number, new_obj.number),
        }

PurchaseRequest.register()
