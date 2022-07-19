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
from netforce.access import get_active_company
from netforce.utils import print_color


class Sequence(Model):
    _name = "sequence"
    _string = "Sequence"
    _audit_log = True
    _key=["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "type": fields.Selection([["cust_invoice", "Customer Invoice"], ["supp_invoice", "Supplier Invoice"], ["cust_credit", "Customer Credit Note"], ["supp_credit", "Supplier Credit Note"], ["cust_debit", "Customer Debit Note"], ["supp_debit", "Supplier Debit Note"], ["pay_in", "Incoming Payment"], ["pay_out", "Outgoing Payment"], ["transfer", "Transfer"], ["tax_no", "Tax No"], ["wht_no", "WHT No"], ["account_move", "Journal Entry"], ["bill_note","Billing Note"], ["pick_in", "Goods Receipt"], ["pick_internal", "Goods Transfer"], ["pick_out", "Goods Issue"], ["stock_count", "Stock Count"], ["stock_move", "Stock Movement"], ["stock_lot", "Lot / Serial Number"], ["stock_container", "Container"], ["waste","Product Waste"], ["stock_transform", "Product Transforms"], ["stock_grade", "Product Gradings"], ["landed_cost", "Landed Costs"], ["shipping_rates", "Shipping Rates"], ["delivery_order","Delivery Orders"], ["delivery_route","Delivery Routes"], ["sale_lead","Sales Lead"], ["sale_opport","Sales Opportunity"], ["sale_quot", "Sales Quotations"], ["sale_order", "Sales Order"], ["sale_return","Sales Return"],["ecom_sale_order", "Ecommerce Sales Order"], ["sale_forecast","Sales Forecast"], ["purchase_order", "Purchase Order"], ["purchase_return","Purchase Return"], ["purchase_request", "Purchase Request"], ["pos_closure", "POS Register Closure"], ["production", "Production Order"], ["bom", "Bill of Material"], ["production_plan","Production Plan"], ["service_item", "Service Item"], ["job", "Service Order"], ["task", "Task"], ["service_contract", "Service Contract"], ["issue", "Issue"], ["employee", "Employee"], ["payrun", "Payrun"], ["leave_request", "Leave Request"], ["expense", "Expense Claim"], ["fixed_asset", "Fixed Asset"], ["claim", "Product Claims"], ["borrow", "Product Borrowings"], ["contact", "Contact Number"], ["product", "Product"], ["ecom_cart","Cart Number"], ["other", "Other"]], "Type", required=True, search=True),
        "prefix": fields.Char("Prefix", search=True),
        "padding": fields.Integer("Number Padding"),
        "running": fields.One2Many("sequence.running", "sequence_id", "Running Numbers"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "company_id": fields.Many2One("company", "Company"),
        "model_id": fields.Many2One("model","Model"),
    }
    _order = "name,company_id"
    _defaults = {
        "padding": 4,
    }

    def get_prefix(self, template, context={}):
        date = context.get("date")
        if not date:
            date = time.strftime("%Y-%m-%d %H:%M:%S")
        vals = {
            "Y": date[0:4],
            "y": date[2:4],
            "m": date[5:7],
            "d": date[8:10],
            "H": date[11:13],
            "bY": str(int(date[0:4])+543),
            "by": str(int(date[0:4])+543)[2:],
            "contact_code": context.get("contact_code"),
            "categ_code": context.get("categ_code"),
            "parent_categ_code": context.get("parent_categ_code"),
        }
        if context.get("sequence_params"):
            vals.update(context["sequence_params"])
        prefix = template % vals
        return prefix

    def find_sequence(self, type=None, name=None, model=None, context={}):
        if type and name:
            cond = [["type", "=", type], ["name", "=", name]]
        elif type:
            cond = [["type", "=", type]]
        elif name:
            cond = [["name", "=", name]]
        elif model:
            cond = [["model_id.name", "=", model]]
        company_id=context.get("company_id")
        if not company_id:
            company_id = get_active_company()
        comp_cond = cond + [["company_id", "=", company_id]]
        res = self.search(comp_cond, order="id")
        if res:
            return res[0]
        res = self.search(cond, order="id")
        if res:
            return res[0]
        return None

    def get_next_number(self, sequence_id, prefix=None, context={}):
        seq = self.browse(sequence_id)
        if not prefix:
            prefix = self.get_prefix(seq.prefix, context) if seq.prefix else ""
        res = get_model("sequence.running").search([["sequence_id", "=", sequence_id], ["prefix", "=", prefix]])
        if res:
            run_id = res[0]
        else:
            vals = {
                "sequence_id": sequence_id,
                "prefix": prefix,
            }
            run_id = get_model("sequence.running").create(vals)
        run = get_model("sequence.running").browse([run_id])[0]
        num = run.next
        if seq.padding is None:
            res = "%s%d" % (prefix, num)
        elif seq.padding == 0:
            res = prefix
        else:
            res = "%s%.*d" % (prefix, seq.padding, num)
        if not res:
            raise Exception("Empty sequence number")
        return res

    def increment_number(self, sequence_id, prefix=None, context={}):
        seq = self.browse(sequence_id)
        if not prefix:
            prefix = self.get_prefix(seq.prefix, context) if seq.prefix else ""
        res = get_model("sequence.running").search([["sequence_id", "=", sequence_id], ["prefix", "=", prefix]])
        if not res:
            raise Exception("Sequence prefix not found: %s (sequence id: %s)"%(prefix,sequence_id))
        run_id = res[0]
        run = get_model("sequence.running").browse([run_id])[0]
        run.write({"next": run.next + 1})

    # XXX: deprecated
    def get_number(self, type=None, name=None, seq_id=None, context={}):
        print_color("WARNING: deprecated method called: sequence.get_number", "red")
        if type:
            res = self.search([["type", "=", type]])
            if not res:
                return None
            seq_id = res[0]
        elif name:
            res = self.search([["name", "=", name]])
            if not res:
                return None
            seq_id = res[0]
        if not seq_id:
            return None
        seq = self.browse([seq_id])[0]
        prefix = self.get_prefix(seq.prefix, context) if seq.prefix else ""
        res = get_model("sequence.running").search([["sequence_id", "=", seq_id], ["prefix", "=", prefix]])
        if res:
            run_id = res[0]
        else:
            vals = {
                "sequence_id": seq_id,
                "prefix": prefix,
            }
            run_id = get_model("sequence.running").create(vals)
        run = get_model("sequence.running").browse([run_id])[0]
        num = run.next
        if seq.padding is None:
            res = "%s%d" % (prefix, num)
        elif seq.padding == 0:
            res = prefix
        else:
            res = "%s%.*d" % (prefix, seq.padding, num)
        return res

    # XXX: deprecated
    def increment(self, type=None, name=None, seq_id=None, context={}):
        print_color("WARNING: deprecated method called: sequence.increment", "red")
        if type:
            res = self.search([["type", "=", type]])
            if not res:
                return None
            seq_id = res[0]
        elif name:
            res = self.search([["name", "=", name]])
            if not res:
                return None
            seq_id = res[0]
        if not seq_id:
            return None
        seq = self.browse([seq_id])[0]
        prefix = self.get_prefix(seq.prefix, context) if seq.prefix else ""
        res = get_model("sequence.running").search([["sequence_id", "=", seq_id], ["prefix", "=", prefix]])
        if not res:
            raise Exception("Sequence prefix not found")
        run_id = res[0]
        run = get_model("sequence.running").browse([run_id])[0]
        run.write({"next": run.next + 1})

Sequence.register()
