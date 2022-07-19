# copyright (c) 2012-2015 Netforce Co. Ltd.
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
from netforce.access import get_active_company, get_active_user, set_active_user
from netforce import database
from netforce import access
from datetime import *
import time
import json
from pprint import *

class Picking(Model):
    _name = "stock.picking"
    _string = "Stock Picking"
    _audit_log = True
    _name_field = "number"
    _key = ["company_id", "type", "number"]
    _multi_company = True
    _content_search=True
    _fields = {
        "type": fields.Selection([["in", "Goods Receipt"], ["internal", "Goods Transfer"], ["out", "Goods Issue"]], "Type", required=True),
        "journal_id": fields.Many2One("stock.journal", "Journal", required=True, search=True),
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Ref", search=True, index=True),
        "contact_id": fields.Many2One("contact", "Contact", search=True),
        "contact_person_id": fields.Many2One("contact", "Contact Person", condition=[["type", "=", "person"]], search=True),
        "date": fields.DateTime("Date", required=True, search=True),
        "date_done": fields.DateTime("Completed Date", search=True),
        "state": fields.Selection([("draft", "Draft"), ("pending", "Planned"), ("approved", "Approved"), ("qc_checked","QC Checked"), ("done", "Completed"), ("voided", "Voided"), ("rejected","Rejected")], "Status", required=True),
        "lines": fields.One2Many("stock.move", "picking_id", "Lines"),
        "expand_lines": fields.One2Many("stock.move", "expand_picking_id", "Expanded Stock Movements"),
        "move_id": fields.Many2One("account.move", "Journal Entry"),
        #"product_id": fields.Many2One("product", "Product", store=False, function_search="search_product"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["project","Project"], ["job", "Service Order"], ["product.claim", "Claim Bill"], ["product.borrow", "Borrow Request"], ["stock.picking", "Picking"], ["production.order","Production Order"]], "Related To"),
        "currency_id": fields.Many2One("currency", "Currency", required=True),
        "addresses": fields.One2Many("address", "related_id", "Addresses"),
        "ship_address_id": fields.Many2One("address", "Shipping Address"),
        "qty_total": fields.Decimal("Total Quantity", function="get_qty_total"),
        "qty_validated": fields.Decimal("Validated Quantity", function="get_qty_validated"),
        "cost_total": fields.Decimal("Total Cost", function="get_cost_total"),
        "container_id": fields.Many2One("stock.container", "Container"),
        "company_id": fields.Many2One("company", "Company"),
        "gross_weight": fields.Decimal("Gross Weight"),
        "pending_by_id": fields.Many2One("base.user", "Pending By", readonly=True),
        "done_by_id": fields.Many2One("base.user", "Completed By", readonly=True),
        "done_approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method",search=True),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "ship_cost": fields.Decimal("Shipping Cost"),
        "ship_pay_by": fields.Selection([["company", "Company"], ["customer", "Customer"], ["supplier", "Supplier"]], "Shipping Paid By"),
        "landed_costs": fields.Many2Many("landed.cost","Landed Costs",function="get_landed_costs"),
        "messenger_id": fields.Many2One("messenger","Messenger"),
        "avail_messengers": fields.Many2Many("messenger","Available Messengers"),
        "currency_rate": fields.Decimal("Currency Rate"),
        "product_id": fields.Many2One("product","Product",store=False,function_search="search_product2",search=True), #XXX ICC
        "sequence": fields.Decimal("Sequence",function="_get_related",function_context={"path":"ship_address_id.sequence"}),
        "delivery_slot_id": fields.Many2One("delivery.slot","Delivery Slot"),
        "ship_state": fields.Selection([["wait_pick","Waiting Pickup"],["in_transit","In Transit"],["delivered","Delivered"],["error","Can not deliver"]],"Shipping Status"),
        "from_coords": fields.Char("Source Coordinates",function="get_from_coords"),
        "to_coords": fields.Char("Destination Coordinates",function="get_to_coords"),
        #"delivery_id": fields.Many2One("nd.order","Delivery Order"),
        #"route_id": fields.Many2One("nd.route","Delivery Route",function="_get_related",function_context={"path":"delivery_id.route_id"}),
        "ship_tracking": fields.Char("Shipping Tracking",function="get_route_text",function_multi=True,store=True), # for PLR sync
        "ship_route": fields.Char("Shipping Route",function="get_route_text",function_multi=True,store=True), # for PLR sync
        "validate_lines": fields.One2Many("pick.validate.line","pick_id","Validations"),
        "employee_id": fields.Many2One("hr.employee","Employee"),
        "qc_results": fields.One2Many("qc.result","pick_id","QC Results"),
        "total_qty": fields.Decimal("Total Qty",function="get_total_qty"),
        "total_lot_weight": fields.Decimal("Total Lot Weight",function="get_total_lot_weight"),
        "total_net_weight": fields.Decimal("Total Net Weight",function="get_total_weight",function_multi=True),
        "total_gross_weight": fields.Decimal("Total Gross Weight",function="get_total_weight",function_multi=True),
        "packaging_id": fields.Many2One("stock.packaging", "Packaging"),
        "pallet_id": fields.Many2One("stock.pallet", "Pallet"),
        "num_pallets": fields.Integer("Number Of Pallets"),
        "transform_lines": fields.One2Many("stock.transform.line","picking_id","Transform Lines"),
        "transforms": fields.Many2Many("stock.transform","Product Transforms",function="get_transforms"),
        "gradings": fields.One2Many("stock.grade.line","picking_id","Gradings"),
        "other_info": fields.Text("Other Info"),
        "from_contact_id": fields.Many2One("contact", "From Contact"),
        "from_address_id": fields.Many2One("address", "From Address"),
        "to_contact_id": fields.Many2One("contact", "To Contact"),
        "to_address_id": fields.Many2One("address", "To Address"),
        "total_sale_amount": fields.Decimal("Total Sales Amount",function="get_total_sale_amount"),
        "location_to_id": fields.Many2One("stock.location","To Location",function="get_location"),
        "invoice_id": fields.Many2One("account.invoice", "Invoice"),
        "truck_loaded_weight": fields.Decimal("Truck Loaded Weight"),
        "truck_empty_weight": fields.Decimal("Truck Empty Weight"),
        "truck_net_weight": fields.Decimal("Truck Net Weight"),
        "lines_mixed": fields.Json("Lines (Mixed)",function="get_lines_mixed"),
        "first_line_id": fields.Many2One("stock.move","First Line",function="get_first_line"),
        "sale_id": fields.Many2One("sale.order","Sales Order",function="get_sale"),
        "search_container_id": fields.Many2One("stock.container", "Container", store=False, function_search="search_container"),
        "location_from_id": fields.Many2One("stock.location", "From Location"),
        "location_to_id": fields.Many2One("stock.location", "To Location"),
        "pickings": fields.One2Many("stock.picking", "related_id", "Stock Pickings"), #Chin 2020-11-26
    }
    _order = "date desc,number desc"

    _sql_constraints = [
        ("key_uniq", "unique (company_id, type, number)", "The number of each company and type must be unique!")
    ]

    def _get_journal(self, context={}):
        pick_type = context.get("pick_type")
        settings = get_model("settings").browse(1)
        if pick_type == "in":
            journal_id = settings.pick_in_journal_id.id
        elif pick_type == "out":
            journal_id = settings.pick_out_journal_id.id
        elif pick_type == "internal":
            journal_id = settings.pick_internal_journal_id.id
        else:
            journal_id = None
        return journal_id

    def _get_number(self, context={}):
        pick_type = context.get("pick_type")
        journal_id = context.get("journal_id")
        seq_id = None
        if journal_id:
            journal = get_model("stock.journal").browse(journal_id)
            seq_id = journal.sequence_id.id
        if not seq_id and pick_type:
            seq_type = "pick_" + pick_type
            seq_id = get_model("sequence").find_sequence(seq_type,context=context)
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id,context=context)
            user_id = get_active_user()
            set_active_user(1)
            res = self.search([["number", "=", num]])
            set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id,context=context)

    def _get_type(self, context={}):
        return context.get("pick_type")

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    _defaults = {
        "state": "draft",
        "journal_id": _get_journal,
        "number": _get_number,
        "type": _get_type,
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "currency_id": _get_currency,
        "company_id": lambda *a: get_active_company(),
    }

    def delete(self, ids, **kw):
        move_ids = []
        #account_move_ids = []
        for obj in self.browse(ids):
            if obj.state=="done":
                raise Exception("Invalid status")
            for line in obj.lines:
                move_ids.append(line.id)
                #if line.move_id:
                #    account_move_ids.append(line.move_id.id)
        if move_ids:
            get_model("stock.move").delete(move_ids)  # to update stored functions
        #if account_move_ids: # XXX: already in stock.move
        #    account_move_ids=list(set(account_move_ids))
        #    get_model("account.move").delete(account_move_ids,force=True)
        super().delete(ids, **kw)

    def copy_to_cust_invoice(self, ids, context):
        id = ids[0]
        return {
            "name": "cust_invoice_new",
            "from_pick_out_id": id,
        }

    def pending(self, ids, context={}):
        user_id = get_active_user()
        for obj in self.browse(ids):
            for move in obj.lines:
                prod=move.product_id
                if prod.type not in ("stock","consumable","bundle"):
                    raise Exception("Invalid product type")
                move.write({"state": "pending", "date": obj.date})
                if obj.related_id and not move.related_id:
                    move.write({"related_id":"%s,%d"%(obj.related_id._model,obj.related_id.id)})
            obj.write({"state": "pending", "pending_by_id": user_id})
            obj.check_stock()

    def check_stock(self,ids,context={}):
        print("stock_picking.check_stock",ids)
        settings=get_model("settings").browse(1)
        obj=self.browse(ids)[0]
        for move in obj.lines:
            prod=move.product_id
            if prod.check_lot_neg_stock and move.lot_id:
                qty_virt=get_model("stock.balance").get_qty_virt(move.location_from_id.id,prod.id,move.lot_id.id) # XXX: improve speed
                print("loc_id=%s prod_id=%s lot_id=%s => qty_virt=%s"%(move.location_from_id.id,prod.id,move.lot_id.id,qty_virt))
                if qty_virt<0:
                    raise Exception("Lot %s is out of stock (product %s at location %s)"%(move.lot_id.number,prod.code,move.location_from_id.name))
            if prod.check_neg_stock or settings.check_neg_stock:
                qty_phys=get_model("stock.balance").get_qty_phys(move.location_from_id.id,prod.id) # XXX: improve speed
                print("loc_id=%s prod_id=%s => qty_phys=%s"%(move.location_from_id.id,prod.id,qty_phys))
                if qty_phys<0:
                    raise Exception("Product %s is out of stock at location %s"%(prod.code,move.location_from_id.name))

    def approve(self, ids, context={}):
        settings=get_model("settings").browse(1)
        for obj in self.browse(ids):
            if obj.type=="in":
                if settings.approve_pick_in and not access.check_permission_other("approve_pick_in"):
                    raise Exception("User does not have permission to approve goods receipts (approve_pick_in).")
            elif obj.type=="out":
                if settings.approve_pick_out and not access.check_permission_other("approve_pick_out"):
                    raise Exception("User does not have permission to approve goods issues (approve_pick_out).")
            elif obj.type=="internal":
                if settings.approve_pick_internal and not access.check_permission_other("approve_pick_internal"):
                    raise Exception("User does not have permission to approve goods transfers (approve_pick_internal).")
            for move in obj.lines:
                prod=move.product_id
                if prod.type not in ("stock","consumable","bundle"):
                    raise Exception("Invalid product type")
                move.write({"state": "approved", "date": obj.date, "contact_id":obj.contact_id.id})
            obj.write({"state": "approved"})
        self.trigger(ids,"approve_%s" % obj.type)

    def void(self, ids, context={}):
        for obj in self.browse(ids):
            for move in obj.lines:
                move.write({"state": "voided"})
            obj.write({"state": "voided"})

    def to_draft(self,ids,context={}):
        for obj in self.browse(ids):
            move_ids=[]
            for move in obj.lines:
                move_ids.append(move.id)
            get_model("stock.move").to_draft(move_ids)
            obj.write({"state":"draft"})
            obj.qc_results.delete()
            obj.expand_lines.delete()

    def to_planned(self,ids,context={}):
        for obj in self.browse(ids):
            obj.to_draft()
            obj.pending()

    def qc_check(self,ids,context={}):
        settings=get_model("settings").browse(1)
        for obj in self.browse(ids):
            if settings.require_qc_in and obj.type=="in" and not obj.qc_results:
                raise Exception("Missing QC results")
            if settings.require_qc_out and obj.type=="out" and not obj.qc_results:
                raise Exception("Missing QC results")
            obj.write({"state":"qc_checked"})

    def reject(self,ids,context={}):
        settings=get_model("settings").browse(1)
        for obj in self.browse(ids):
            if not obj.qc_results:
                raise Exception("Missing QC results")
            for move in obj.lines:
                move.write({"state": "voided"})
            obj.write({"state":"rejected"})
        self.trigger(ids,"reject_%s" % obj.type)

    def set_done(self,ids,context={}):
        settings = get_model("settings").browse(1)
        user_id=get_active_user()
        for obj in self.browse(ids):
            if obj.type=="in":
                if settings.approve_pick_in and not access.check_permission_other("approve_pick_in"):
                    raise Exception("User does not have permission to approve goods receipts (approve_pick_in).")
            elif obj.type=="out":
                if settings.approve_pick_out and not access.check_permission_other("approve_pick_out"):
                    raise Exception("User does not have permission to approve goods issues (approve_pick_out).")
            elif obj.type=="internal":
                if settings.approve_pick_internal and not access.check_permission_other("approve_pick_internal"):
                    raise Exception("User does not have permission to approve goods transfers (approve_pick_internal).")
            journal=obj.journal_id
            if journal.require_sale:
                if not obj.related_id or obj.related_id._model!="sale.order":
                    raise Exception("Missing sales order")
            obj.expand_bundles()
            if settings.require_qc_in and obj.type=="in" and not obj.qc_results:
                raise Exception("Missing QC results")
            if settings.require_qc_out and obj.type=="out" and not obj.qc_results:
                raise Exception("Missing QC results")
            move_ids=[]
            for line in obj.lines:
                move_ids.append(line.id)
            for line in obj.expand_lines:
                move_ids.append(line.id)
            desc=obj.number
            if obj.date_done:
                t=obj.date_done
            else:
                t=time.strftime("%Y-%m-%d %H:%M:%S")
            get_model("stock.move").write(move_ids,vals={"date":t,"journal_id":obj.journal_id.id,"ref":obj.number,"contact_id":obj.contact_id.id},context=context)
            get_model("stock.move").set_done(move_ids,context=context)
            obj.write({"state":"done","done_by_id":user_id,"date_done":t},context=context)
            obj.set_currency_rate()
            if not context.get("no_check_stock"):
                obj.check_stock()
            obj.set_purchase_fg_cost_price()
            if settings.pick_out_create_invoice:
                obj.copy_to_invoice()
        self.check_order_qtys(ids)
        self.trigger(ids,"done")

    def set_done_fast(self,ids,context={}):
        settings = get_model("settings").browse(1)
        user_id=get_active_user()
        db=database.get_connection()
        for obj in self.browse(ids):
            if obj.type=="in":
                if settings.approve_pick_in and not access.check_permission_other("approve_pick_in"):
                    raise Exception("User does not have permission to approve goods receipts (approve_pick_in).")
            elif obj.type=="out":
                if settings.approve_pick_out and not access.check_permission_other("approve_pick_out"):
                    raise Exception("User does not have permission to approve goods issues (approve_pick_out).")
            elif obj.type=="internal":
                if settings.approve_pick_internal and not access.check_permission_other("approve_pick_internal"):
                    raise Exception("User does not have permission to approve goods transfers (approve_pick_internal).")
            journal=obj.journal_id
            if journal.require_sale:
                if not obj.related_id or obj.related_id._model!="sale.order":
                    raise Exception("Missing sales order")
            if settings.require_qc_in and obj.type=="in" and not obj.qc_results:
                raise Exception("Missing QC results")
            if settings.require_qc_out and obj.type=="out" and not obj.qc_results:
                raise Exception("Missing QC results")
            move_ids=[]
            for line in obj.lines:
                move_ids.append(line.id)
            desc=obj.number
            db.execute("UPDATE stock_move SET date=%s, journal_id=%s, ref=%s, contact_id=%s WHERE id IN %s",obj.date,obj.journal_id.id,obj.number,obj.contact_id.id,tuple(move_ids))
            get_model("stock.move").set_done_fast(move_ids,context=context)
            db.execute("UPDATE stock_picking SET state='done', done_by_id=%s WHERE id=%s",user_id,obj.id)
        self.trigger(ids,"done")

    def check_order_qtys(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.related_id:
            return
        model = obj.related_id._model
        if model == "sale.order":
            obj.related_id.check_delivered_qtys()
        elif model == "purchase.order":
            obj.related_id.check_received_qtys()

    def onchange_contact(self, context={}):
        settings = get_model("settings").browse(1)
        data = context["data"]
        contact_id = data["contact_id"]
        contact = get_model("contact").browse(contact_id)
        data["ship_address_id"] = contact.get_address(pref_type="shipping")
        if data["type"] == "in":
            data["journal_id"] = contact.pick_in_journal_id.id or settings.pick_in_journal_id.id
        elif data["type"] == "out":
            data["journal_id"] = contact.pick_out_journal_id.id or settings.pick_out_journal_id.id
        elif data["type"] == "internal":
            data["journal_id"] = contact.pick_internal_journal_id.id or settings.pick_internal_journal_id.id
        self.onchange_journal(context=context)
        return data

    def onchange_journal(self, context={}):
        data = context["data"]
        journal_id = data["journal_id"]
        if not journal_id:
            return
        journal = get_model("stock.journal").browse(journal_id)
        ctx = {
            "pick_type": data["type"],
            "journal_id": data["journal_id"],
        }
        data["number"] = self._get_number(ctx)
        for line in data["lines"]:
            if journal.location_from_id:
                line["location_from_id"] = journal.location_from_id.id
            if journal.location_to_id:
                line["location_to_id"] = journal.location_to_id.id
        return data

    def onchange_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        line["qty"] = 1
        if prod.uom_id is not None:
            line["uom_id"] = prod.uom_id.id
        if data["type"] == "in":
            if prod.purchase_price is not None:
                line["cost_price_cur"] = prod.purchase_price
        elif data["type"] == "internal":
            line["sale_price"]=prod.sale_price
            line["sale_amount"]=(line.get("qty") or 1)*(prod.sale_price or 0)
        journal_id=data.get("journal_id")
        if journal_id:
            journal=get_model("stock.journal").browse(journal_id)
            if journal.location_from_id:
                line["location_from_id"]=journal.location_from_id.id
            if journal.location_to_id:
                line["location_to_id"]=journal.location_to_id.id
        if data.get("location_from_id"):
            line["location_from_id"]=data["location_from_id"]
        if data.get("location_to_id"):
            line["location_to_id"]=data["location_to_id"]
        self.update_cost_price(context=context)
        return data

    def copy_to_invoice(self, ids, context={}):
        id = ids[0]
        first_obj = self.browse(id)
        number = get_model("account.invoice")._get_number(context={"type": first_obj.type, "inv_type": "invoice"})
        if first_obj.type in ("out","internal"):
            if not first_obj.contact_id:
                raise Exception("Please select a customer for this goods issue first")
            contact=first_obj.contact_id
            inv_vals = {
                "type": "out",
                "inv_type": "invoice",
                "number": number,
                "contact_id": first_obj.contact_id.id,
                "date": first_obj.date[:10],
                "lines": [],
            }
            if contact.sale_pay_term_id:
                inv_vals["pay_term_id"]=contact.sale_pay_term_id.id
            rel=first_obj.related_id
            if rel:
                inv_vals["related_id"]="%s,%s"%(rel._model,rel.id)
                if rel._model=="sale.order":
                    inv_vals["seller_id"]=first_obj.related_id.seller_id.id
                    inv_vals["currency_id"]=first_obj.related_id.currency_id.id #Chin 2020-12-08
            inv_vals["memo"]=first_obj.number
            refs=[]
            move_ids=[]
            for obj in self.browse(ids):
                if obj.contact_id.id!=inv_vals["contact_id"]:
                    raise Exception("Invalid contact in picking %s"%obj.number)
                for line in obj.lines:
                    if line.invoice_id:
                        raise Exception("Invoice already created for product %s"%line.product_id.code)
                    prod = line.product_id
                    line_vals = {
                        "product_id": prod.id,
                        "description": prod.name or "/",
                        "qty": line.qty,
                        "uom_id": line.uom_id.id,
                        "qty2": line.qty2,
                        "uom2_id": line.uom2_id.id,
                        "track_id": line.track_id.id,
                        "packaging_id": line.packaging_id.id if line.packaging_id else None, # Chin 2020-12-21
                        "notes": line.notes,
                    }
                    if obj.type=="out":
                        acc_id=prod.sale_account_id.id
                        if not acc_id and prod.categ_id:
                            acc_id=prod.categ_id.sale_account_id.id
                        line_vals["account_id"]=acc_id
                    elif obj.type=="in":
                        acc_id=prod.purchase_account_id.id
                        if not acc_id and prod.categ_id:
                            acc_id=prod.categ_id.purchase_account_id.id
                        line_vals["account_id"]=acc_id
                    so_line=None
                    if obj.related_id and obj.related_id._model == "sale.order":
                        so_line_id = obj.related_id.find_sale_line(prod.id)
                        if so_line_id:
                            so_line = get_model("sale.order.line").browse(so_line_id)
                    if so_line:
                        sale=so_line.order_id
                        refs.append(sale.number)
                        line_vals["description"] = so_line.description or line_vals["description"] #Chin 2020-11-12
                        line_vals["unit_price"] = so_line.unit_price or 0
                        line_vals["tax_id"] = so_line.tax_id.id
                        line_vals["related_id"]="sale.order,%s"%sale.id
                        line_vals["discount"] = so_line.discount
                        line_vals["discount_amount"] = so_line.discount_amount
                    else:
                        line_vals["unit_price"] = prod.sale_price or 0
                        line_vals["tax_id"] = prod.sale_tax_id.id
                    line_vals["amount"] = line_vals["unit_price"] * line_vals["qty"]
                    inv_vals["lines"].append(("create", line_vals))
                    move_ids.append(line.id)
            refs=list(set(refs))
            inv_vals["ref"]=", ".join(refs)
            inv_id = get_model("account.invoice").create(inv_vals, context={"type": "out", "inv_type": "invoice"})
            inv=get_model("account.invoice").browse(inv_id)
            inv.set_pay_term()
            for obj in self.browse(ids):
                obj.write({"invoice_id": inv_id})
                obj.expand_bundles()
                for line in obj.lines:
                    line.write({"invoice_id": inv_id})
            return {
                "next": {
                    "name": "view_invoice",
                    "active_id": inv_id,
                },
                "flash": "Customer invoice copied from goods issue",
            }
        elif first_obj.type == "in":
            if not first_obj.contact_id:
                raise Exception("Please select a supplier for this goods receipt first")
            inv_vals = {
                "type": "in",
                "inv_type": "invoice",
                "number": number,
                "contact_id": first_obj.contact_id.id,
                "currency_id": first_obj.currency_id.id,
                "currency_rate": first_obj.currency_rate,
                "lines": [],
            }
            refs=[]
            move_ids=[]
            for obj in self.browse(ids):
                if obj.contact_id.id!=inv_vals["contact_id"]:
                    raise Exception("Invalid contact in picking %s"%obj.number)
                refs.append(obj.number)
                for line in obj.lines:
                    if line.invoice_id:
                        raise Exception("Invoice already created for product %s"%line.product_id.code)
                    prod = line.product_id
                    price=line.cost_price_cur or 0
                    acc_id=prod.purchase_account_id.id
                    if not acc_id and prod.categ_id:
                        acc_id=prod.categ_id.purchase_account_id.id
                    tax_id=prod.purchase_tax_id.id
                    if not tax_id and prod.categ_id:
                        tax_id=prod.categ_id.purchase_tax_id.id
                    line_vals = {
                        "product_id": line.product_id.id,
                        "description": prod.description or prod.name or "/",
                        "qty": line.qty,
                        "uom_id": line.uom_id.id,
                        "unit_price": price,
                        "account_id": acc_id,
                        "tax_id": tax_id,
                        "amount": line.qty * price,
                    }
                    inv_vals["lines"].append(("create", line_vals))
                    move_ids.append(line.id)
            refs=list(set(refs))
            inv_vals["ref"]=", ".join(refs)
            inv_id = get_model("account.invoice").create(inv_vals, context=context)
            move_ids = get_model("stock.move").search([["picking_id", "=", obj.id]])
            for obj in self.browse(ids):
                obj.write({"invoice_id": inv_id})
                obj.expand_bundles()
                for line in obj.lines:
                    line.write({"invoice_id": inv_id})
            return {
                "next": {
                    "name": "view_invoice",
                    "active_id": inv_id,
                },
                "flash": "Supplier invoice copied from goods receipt",
            }
        else:
            raise Exception("Invalid picking type")

    def copy(self, ids, from_location=None, to_location=None, state=None, type=None, context={}):
        print("picking.copy",ids)
        obj = self.browse(ids[0])
        if from_location:
            res=get_model("stock.location").search([["code","=",from_location]])
            if not res:
                raise Exception("Location code not found: %s"%from_location)
            from_loc_id=res[0]
        else:
            from_loc_id=None
        if to_location:
            res=get_model("stock.location").search([["code","=",to_location]])
            if not res:
                raise Exception("Location code not found: %s"%to_location)
            to_loc_id=res[0]
        else:
            to_loc_id=None
        vals = {
            "type": type and type or obj.type,
            "contact_id": obj.contact_id.id,
            "ref": obj.ref,
            "lines": [],
            "location_from_id": obj.location_from_id.id,
            "location_to_id": obj.location_to_id.id,
        }
        if obj.related_id:
            vals["related_id"] = "%s,%d" % (obj.related_id._model, obj.related_id.id)
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "location_from_id": from_loc_id and from_loc_id or line.location_from_id.id,
                "location_to_id": to_loc_id and to_loc_id or line.location_to_id.id,
                "lot_id": line.lot_id.id,
            }
            if line.related_id:
                line_vals["related_id"] = "%s,%d" % (line.related_id._model, line.related_id.id)
            if obj.type == "in":
                line_vals["cost_price_cur"] = line.cost_price_cur
                line_vals["cost_price"] = line.cost_price
                line_vals["cost_amount"] = line.cost_amount
            vals["lines"].append(("create", line_vals))
        from pprint import pprint
        pprint(vals)
        new_id = self.create(vals, {"pick_type": vals["type"]})
        if state in ("planned","approved"):
            self.pending([new_id])
        if state=="approved":
            self.approve([new_id])
        new_obj = self.browse(new_id)
        if obj.type == "in":
            return {
                "next": {
                    "name": "pick_in",
                    "mode": "form",
                    "active_id": new_id,
                },
                "flash": "Goods receipt %s copied to %s" % (obj.number, new_obj.number),
            }
        elif obj.type == "internal":
            return {
                "next": {
                    "name": "pick_internal",
                    "mode": "form",
                    "active_id": new_id,
                },
                "flash": "Goods transfer %s copied to %s" % (obj.number, new_obj.number),
            }
        elif obj.type == "out":
            return {
                "next": {
                    "name": "pick_out",
                    "mode": "form",
                    "active_id": new_id,
                },
                "flash": "Goods issue %s copied to %s" % (obj.number, new_obj.number),
            }

    def wkf_copy(self, context={}, **kw): # XXX
        print("#"*80)
        print("picking.wkf_copy")
        trigger_ids=context.get("trigger_ids")
        if not trigger_ids:
            raise Exception("Missing trigger ids")
        print("trigger_ids",trigger_ids)
        self.copy(trigger_ids,context=context,**kw)

    def copy_to_receipt(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "type": "in",
            "contact_id": obj.contact_id.id,
            "ref": obj.ref,
            "lines": [],
        }
        if obj.related_id:
            vals["related_id"] = "%s,%d" % (obj.related_id._model, obj.related_id.id)
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "location_from_id": line.location_to_id.id,
                "location_to_id": line.location_from_id.id,
            }
            if obj.type == "in":
                line_vals["unit_price"] = line.unit_price
            vals["lines"].append(("create", line_vals))
        from pprint import pprint
        pprint(vals)
        new_id = self.create(vals, {"pick_type": "in"})
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "pick_in",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Goods receipt %s copied to %s" % (obj.number, new_obj.number),
        }

    def view_picking(self, ids, context={}):
        obj = self.browse(ids[0])
        if obj.type == "out":
            action = "pick_out"
        elif obj.type == "in":
            action = "pick_in"
        elif obj.type == "internal":
            action = "pick_internal"
        return {
            "next": {
                "name": action,
                "mode": "form",
                "active_id": obj.id,
            }
        }

    def search_product(self, clause, context={}):
        op = clause[1]
        val = clause[2]
        return ["lines.product_id.name", op, val]

    def search_product2(self, clause, context={}): #XXX ICC
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        picking_ids = []
        for line in get_model("stock.move").search_browse([["product_id","in",product_ids]]):
            picking_ids.append(line.picking_id.id)
        cond = [["id","in",picking_ids]]
        return cond

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        if "date" in vals:
            date = vals["date"]
            move_ids = get_model("stock.move").search([["picking_id", "in", ids]])
            get_model("stock.move").write(move_ids, {"date": date})

    def get_qty_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.qty for line in obj.lines])
            res[obj.id] = qty or 0
        return res

    def get_qty_validated(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.validate_qty or 0 for line in obj.lines])
            res[obj.id] = qty or 0
        return res

    def get_cost_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            amt = sum([line.cost_amount for line in obj.lines])
            res[obj.id] = amt or 0
        return res

    def add_container(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "add_container",
                "defaults": {
                    "picking_id": obj.id,
                }
            }
        }

    def onchange_container(self, context={}):
        data = context["data"]
        cont_id = data.get("container_id")
        if not cont_id:
            return
        cont = get_model("stock.container").browse(cont_id)
        contents = cont.get_contents()
        lines = []
        for (prod_id, lot_id, loc_id), (qty, amt, qty2) in contents.items():
            prod = get_model("product").browse(prod_id)
            line_vals = {
                "product_id": prod_id,
                "qty": qty,
                "uom_id": prod.uom_id.id,
                "qty2": qty2,
                "location_from_id": loc_id,
                "location_to_id": None,
                "lot_id": lot_id,
                "container_from_id": cont_id,
            }
            if data["type"] == "internal":
                line_vals["container_to_id"] = cont_id
            lines.append(line_vals)
        data["lines"] = lines
        return data

    def approve_done(self, ids, context={}):
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"done_approved_by_id": user_id})

    def view_journal_entry(self,ids,context={}):
        obj=self.browse(ids)[0]
        move_id=None
        for line in obj.lines:
            if line.move_id:
                if move_id is None:
                    move_id=line.move_id.id
                else:
                    if line.move_id.id!=move_id:
                        raise Exception("Stock movements have different journal entries")
        if not move_id:
            raise Exception("Journal entry not found")
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": move_id,
            }
        }

    def copy_to_landed(self, ids, context={}):
        vals={
            "cost_allocs": [],
        }
        for obj in self.browse(ids):
            for line in obj.lines:
                prod=line.product_id
                alloc_vals={
                    "move_id": line.id,
                    "est_ship": line.qty*(line.cost_price_cur or 0)*(prod.purchase_ship_percent or 0)/100,
                    "est_duty": line.qty*(line.cost_price_cur or 0)*(prod.purchase_duty_percent or 0)/100,
                }
                vals["cost_allocs"].append(("create",alloc_vals))
        landed_id=get_model("landed.cost").create(vals)
        return {
            "next": {
                "name": "landed_cost",
                "mode": "form",
                "active_id": landed_id,
            },
            "flash": "Landed costs copied from goods receipt",
        }

    def get_landed_costs(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            landed_ids=[]
            for move in obj.lines:
                for alloc in move.alloc_costs:
                    landed_ids.append(alloc.landed_id.id)
            landed_ids=list(set(landed_ids))
            vals[obj.id]=landed_ids
        return vals

    def assign_lots(self,ids,context={}):
        print("assign_lots",ids)
        obj=self.browse(ids[0])
        delete_ids=[]
        for line in obj.lines:
            prod=line.product_id
            if prod.lot_id:
                continue
            lot_avail_qtys={}
            for bal in get_model("stock.balance").search_browse([["product_id","=",prod.id],["location_id","=",line.location_from_id.id]]):
                lot_id=bal.lot_id.id
                lot_avail_qtys.setdefault(lot_id,0)
                lot_avail_qtys[lot_id]+=bal.qty_virt
            print("lot_avail_qtys",lot_avail_qtys)
            if not lot_avail_qtys:
                continue
            lot_ids=lot_avail_qtys.keys()
            lots=[lot for lot in get_model("stock.lot").browse(lot_ids)]
            if prod.lot_select=="fifo":
                lots.sort(key=lambda l: l.received_date)
            elif prod.lot_select=="fefo":
                lots.sort(key=lambda l: l.expiry_date)
            elif prod.lot_select=="qty":
                lots.sort(key=lambda l: -lot_avail_qtys[l.id])
            remain_qty=line.qty
            lot_use_qtys={}
            for lot in lots:
                if prod.min_life_remain_percent:
                    if not lot.life_remain_percent or lot.life_remain_percent<prod.min_life_remain_percent:
                        continue
                avail_qty=lot_avail_qtys[lot.id]
                use_qty=min(avail_qty,remain_qty) # XXX: uom
                lot_use_qtys[lot.id]=use_qty
                remain_qty-=use_qty
                if remain_qty<=0:
                    break
            if prod.max_lots_per_sale and len(lot_use_qtys)>prod.max_lots_per_sale:
                lot_use_qtys={}
                remain_qty=line.qty
            print("lot_use_qtys",lot_use_qtys)
            if remain_qty:
                line.write({"qty":remain_qty})
            else:
                delete_ids.append(line.id)
            for lot_id,use_qty in lot_use_qtys.items():
                vals={
                    "picking_id": line.picking_id.id,
                    "product_id": line.product_id.id,
                    "qty": use_qty,
                    "uom_id": line.uom_id.id,
                    "location_from_id": line.location_from_id.id,
                    "location_to_id": line.location_to_id.id,
                    "lot_id": lot_id,
                    "track_id": line.track_id.id,
                }
                rel=line.related_id
                if rel:
                    vals["related_id"]="%s,%s"%(rel._model,rel.id)
                get_model("stock.move").create(vals)
        if delete_ids:
            get_model("stock.move").delete(delete_ids)

    def wkf_check_location(self,ids,from_location=None,to_location=None,context={}):
        print("#"*80)
        print("picking.check_location",ids,from_location,to_location)
        obj=self.browse(ids[0])
        if from_location:
            res=get_model("stock.location").search([["code","=",from_location]])
            if not res:
                raise Exception("Location code not found: %s"%from_location)
            from_loc_id=res[0]
        else:
            from_loc_id=None
        if to_location:
            res=get_model("stock.location").search([["code","=",to_location]])
            if not res:
                raise Exception("Location code not found: %s"%to_location)
            to_loc_id=res[0]
        else:
            to_loc_id=None
        for line in obj.lines:
            if from_loc_id and line.location_from_id.id!=from_loc_id:
                return []
            if to_loc_id and line.location_to_id.id!=to_loc_id:
                return []
        return ids

    def set_currency_rate(self,ids,context={}):
        obj=self.browse(ids[0])
        settings=get_model("settings").browse(1)
        if obj.currency_rate:
            currency_rate = obj.currency_rate
        else:
            if not obj.currency_id:
                raise Exception("Missing picking currency")
            if obj.currency_id.id == settings.currency_id.id:
                currency_rate = 1
            else:
                rate_from = obj.currency_id.get_rate(date=obj.date)
                if not rate_from:
                    raise Exception("Missing currency rate for %s" % obj.currency_id.code)
                if not settings.currency_id:
                    raise Exception("Missing company currency")
                rate_to = settings.currency_id.get_rate(date=obj.date)
                if not rate_to:
                    raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                currency_rate = rate_from / rate_to
        obj.write({"currency_rate":currency_rate})

    def update_cost_price(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        cost_price_cur=line.get("cost_price_cur") or 0
        qty=line["qty"] or 0
        currency_id=data.get("currency_id")
        if not currency_id:
            return data
        currency=get_model("currency").browse(currency_id)
        currency_rate=data["currency_rate"]
        date=data["date"]
        settings=get_model("settings").browse(1)
        if not currency_rate:
            if currency_id == settings.currency_id.id:
                currency_rate = 1
            else:
                rate_from = currency.get_rate(date=date)
                if not rate_from:
                    raise Exception("Missing currency rate for %s" % currency.code)
                rate_to = settings.currency_id.get_rate(date=date)
                if not rate_to:
                    raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                currency_rate = rate_from / rate_to
        cost_price=get_model("currency").convert(cost_price_cur,currency_id,settings.currency_id.id,rate=currency_rate)
        cost_amount=cost_price*qty
        line["cost_price"]=cost_price
        line["cost_amount"]=cost_amount
        return data

    def get_from_coords(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            coords=None
            for line in obj.lines:
                loc=line.location_from_id
                addr=loc.address_id
                if addr and addr.coordinates:
                    coords=addr.coordinates
                    break
            vals[obj.id]=coords
        return vals

    def get_to_coords(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            addr=obj.ship_address_id
            if addr and addr.coordinates:
                coords=addr.coordinates
            else:
                coords=None
            vals[obj.id]=coords
        return vals
    """
    def copy_to_delivery(self,ids,context={}):
        print("Picking.copy_to_delivery",ids)
        n=0
        for obj in self.browse(ids):
            if obj.type!="out":
                raise Exception("Invalid picking type")
            if not obj.contact_id:
                raise Exception("Missing contact in goods issue %s"%obj.number)
            if not obj.ship_address_id:
                raise Exception("Missing shipping address in goods issue %s"%obj.number)
            vals={
                "customer_id": obj.contact_id.id,
                "delivery_date": obj.date[:10],
                "ship_address_id": obj.ship_address_id.id,
                "lines": [],
            }
            slot=obj.delivery_slot_id
            if slot:
                vals["time_from"]=slot.time_from
                vals["time_to"]=slot.time_to
            if not obj.lines:
                raise Exception("Goods issue %s is empty"%obj.number)
            for line in obj.lines:
                line_vals={
                    "product_id": line.product_id.id,
                    "qty": line.qty,
                }
                vals["lines"].append(("create",line_vals))
            new_id=get_model("nd.order").create(vals)
            obj.write({"delivery_id":new_id})
            n+=1
        return {
            "flash": "%d delivery orders created"%n,
        }

    def get_route_text(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]={
                "ship_route": obj.route_id.name_get()[0][1] if obj.route_id else None,
                "ship_tracking": obj.delivery_id.name_get()[0][1] if obj.delivery_id else None,
            }
        return vals
    """
    def do_validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.validate_lines:
            raise Exception("Nothing received yet")
        settings=get_model("settings").browse(1)
        orig_move_ids=[]
        validate_move_ids=[]
        if obj.validate_lines:
            for vline in obj.validate_lines:
                move = vline.move_id
                if not move:
                    continue # XXX
                    #raise Exception("Missing move_id in pick validate line %s"%vline.id)
                orig_move_ids.append(move.id)
                vals={
                    "qty": vline.qty,
                    "qty2": vline.qty2,
                    "lot_id": vline.lot_id.id,
                    "container_id": vline.container_id.id,
                }
                validate_move_ids.append(move._copy(vals=vals)[0])
        for move in obj.lines:
            if move.id in orig_move_ids:
                continue
            if move.id in validate_move_ids:
                continue
            orig_move_ids.append(move.id)
            vals={
                "qty": 0,
                "qty2": 0,
                "lot_id": None,
                "container_id": None,
            }
            move._copy(vals=vals)
        orig_move_ids=list(set(orig_move_ids))
        get_model("stock.move").delete(orig_move_ids)
        message = "Picking %s validated" % obj.number
        obj.set_done()
        if obj.type == "in":
            action = "pick_in"
        elif obj.type == "out":
            action = "pick_out"
        elif obj.type == "internal":
            action = "pick_internal"
        return {
            "next": {
                "name": action,
                "mode": "form",
                "active_id": obj.id,
            },
            "flash": message,
        }

    def try_validate_all(self, date, journal_id, context):
        time_from=date+" 00:00:00"
        time_to=date+" 23:59:59"
        cond=[["date",">=",time_from],["date","<=",time_to],["state","=","approved"]]
        for obj in self.search_browse(cond):
            done=True
            for line in obj.lines: 
                if line.validate_qty<line.qty:
                    done=False
            if not done:
                continue
            obj.do_validate()

    def copy_to_return(self, ids, context={}):
        print("picking.copy_to_return",ids)
        settings=get_model("settings").browse(1)
        obj = self.browse(ids[0])
        journal_id=None
        if obj.type=="in":
            journal_id=settings.pick_out_return_journal_id.id
        if not journal_id:
            raise Exception("Missing stock journal")
        vals = {
            "type": obj.type=="in" and "out" or "in",
            "contact_id": obj.contact_id.id,
            "ref": obj.ref,
            "journal_id": journal_id,
            "lines": [],
        }
        if obj.related_id:
            vals["related_id"] = "%s,%d" % (obj.related_id._model, obj.related_id.id)
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "location_from_id": line.location_to_id.id,
                "location_to_id": line.location_from_id.id,
                "lot_id": line.lot_id.id,
                "cost_price_cur": line.cost_price_cur,
                "cost_price": line.cost_price,
                "cost_amount": line.cost_amount,
            }
            if line.related_id:
                line_vals["related_id"] = "%s,%d" % (line.related_id._model, line.related_id.id)
            vals["lines"].append(("create", line_vals))
        new_id = self.create(vals, {"pick_type": vals["type"]})
        self.pending([new_id])

    def set_purchase_fg_cost_price(self,ids,context={}):
        print("set_purchase_fg_cost_price")
        obj=self.browse(ids[0])
        if obj.type!="in":
            return
        fg_line=None
        for line in obj.lines:
            prod=line.product_id
            if prod.cost_method=="purchase_fg":
                fg_line=line
                break
        if not fg_line:
            return
        related=obj.related_id
        if not related or related._model!="purchase.order":
            return
        purch=related
        purch_cost=0
        for line in purch.lines:
            if line.product_id.id!=fg_line.product_id.id:
                continue
            purch_cost+=line.amount
        rm_cost=0
        for pick in purch.pickings:
            if not pick.ref or not pick.ref.startswith("RM-OUT"):
                continue
            for line in pick.lines:
                rm_cost+=line.cost_amount
        print("rm_cost",rm_cost)
        fg_cost=purch_cost+rm_cost
        fg_price=fg_cost/fg_line.qty
        fg_line.write({"cost_price":fg_price,"cost_amount":fg_cost})

    def get_total_qty(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total_qty=0
            for line in obj.lines:
                total_qty+=line.qty or 0
            vals[obj.id]=total_qty
        return vals

    def get_total_lot_weight(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total_weight=0
            for line in obj.lines:
                if line.lot_id:
                    total_weight+=line.lot_id.weight or 0
            vals[obj.id]=total_weight
        return vals

    def get_total_weight(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total_net_weight=0
            total_gross_weight=0
            for line in obj.lines:
                total_net_weight+=line.net_weight or 0
                total_gross_weight+=line.gross_weight or 0
            vals[obj.id]={
                "total_net_weight": total_net_weight,
                "total_gross_weight": total_gross_weight,
            }
        return vals

    def copy_to_transform(self,ids,context={}):
        vals={
            "lines": [],
        }
        for obj in self.browse(ids):
            for line in obj.lines:
                line_vals={
                    "type": "in",
                    "product_id": line.product_id.id,
                    "lot_id": line.lot_id.id,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "location_id": line.location_to_id.id,
                    "picking_id": obj.id,
                }
                vals["lines"].append(("create",line_vals))
        trans_id=get_model("stock.transform").create(vals)
        return {
            "next": {
                "name": "transform",
                "mode": "form",
                "active_id": trans_id,
            }
        }

    def get_transforms(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            trans_ids=[]
            for line in obj.transform_lines:
                trans_ids.append(line.transform_id.id)
            trans_ids=list(set(trans_ids))
            vals[obj.id]=trans_ids
        return vals

    def copy_to_grading(self,ids,context={}):
        loc_id=None
        for obj in self.browse(ids):
            for line in obj.lines:
                if not loc_id:
                    loc_id=line.location_to_id.id
                else:
                    if line.location_to_id.id!=loc_id:
                        raise Exception("Different locations")
        vals={
            "location_id": loc_id,
            "lines": [],
        }
        for obj in self.browse(ids):
            for line in obj.lines:
                prod=line.product_id
                line_vals={
                    "product_id": prod.id,
                    "qty": line.qty,
                    "lot_id": line.lot_id.id,
                    "uom_id": line.uom_id.id,
                    "product_gb_id": prod.product_gb_id.id,
                    "picking_id": obj.id,
                }
                vals["lines"].append(("create",line_vals))
        grade_id=get_model("stock.grade").create(vals)
        return {
            "next": {
                "name": "grade",
                "mode": "form",
                "active_id": grade_id,
            }
        }

    def expand_bundles(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            obj.expand_lines.delete()
            i=0
            for line in obj.lines:
                i+=1
                line.write({"sequence":i})
                prod=line.product_id
                if prod.type=="bundle":
                    if not prod.components:
                        raise Exception("No components for bundle product %s"%prod.code)
                    for comp in prod.components:
                        comp_prod=comp.component_id
                        qty=line.qty*comp.qty
                        related_id="%s,%s"%(line.related_id._model,line.related_id.id) if line.related_id else None
                        i+=1
                        line_vals = {
                            "date": line.date,
                            "ref": line.ref,
                            "journal_id": obj.journal_id.id,
                            "sequence": i,
                            "expand_picking_id": obj.id,
                            "expand_move_id": line.id,
                            "product_id": comp_prod.id,
                            "qty": qty,
                            "uom_id": comp_prod.uom_id.id,
                            "location_from_id": line.location_from_id.id,
                            "location_to_id": line.location_to_id.id,
                            "related_id": related_id,
                            "invoice_id": line.invoice_id.id,
                            "state": line.state,
                        }
                        get_model("stock.move").create(line_vals)
                        n+=1
        return {
            "alert": "%d components added"%n,
        }

    def remove_bundle_components(self,ids,context={}):
        del_move_ids=[]
        for obj in self.browse(ids):
            for line in obj.lines:
                prod=line.product_id
                if prod.type!="bundle":
                    del_move_ids.append(line.id)
        get_model("stock.move").delete(del_move_ids)

    def get_total_sale_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for line in obj.lines:
                amt+=line.sale_amount or 0
            vals[obj.id]=amt
        return vals

    def get_location(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            loc_id=None
            if obj.lines:
                loc_id=obj.lines[0].location_to_id.id
            vals[obj.id]=loc_id
        return vals

    def onchange_purchase(self, context):
        print("onchange_purchase")
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        purch_id = line.get("purchase_id")
        if not purch_id:
            return {}
        purch = get_model("purchase.order").browse(purch_id)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        prod_line=None
        for purch_line in purch.lines:
            if purch_line.product_id.id==prod.id:
                prod_line=purch_line
        print("product not found in PO")
        if not prod_line:
            return {}
        line["cost_price"]=prod_line.unit_price or 0
        line["cost_amount"]=line["cost_price"]*(line["qty"] or 0)
        return data

    def validate_barcode(self, ids, barcode, context={}):
        obj=self.browse(ids[0])
        res=get_model("product").search(["or",["code","=",barcode],["barcode","=",barcode]])
        if not res:
            raise Exception("Product not found with barcode: '%s'"%barcode)
        prod_id=res[0]
        prod=get_model("product").browse(prod_id)
        move_id=None
        for line in obj.lines:
            if line.product_id.id==prod_id:
                move_id=line.id
                break
        if not move_id:
            raise Exception("Product %s not found in picking %s"%(prod.name,obj.number))
        vals={
            "pick_id": obj.id,
            "move_id": move_id,
            "product_id": prod_id,
            "qty": 1,
            "uom_id": prod.uom_id.id,
        }
        line_id=get_model("pick.validate.line").create(vals)
        return {
            "validate_line_id": line_id,
        }

    def repost_journal_entry(self,ids,context={}):
        for obj in self.browse(ids):
            move_id=None
            for line in obj.lines:
                if line.move_id:
                    if move_id is None:
                        move_id=line.move_id.id
                    else:
                        if line.move_id.id!=move_id:
                            raise Exception("Stock movements have different journal entries")
            if move_id:
                move=get_model("account.move").browse(move_id)
                move.void()
                move.delete()
            obj.lines.post()

    def get_lines_mixed(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            data=[]
            i=0
            for line in obj.lines:
                i+=1
                data.append({
                    "prefix": "%d."%i,
                    "product_id": {
                        "code": line.product_id.code,
                        "name": line.product_id.name,
                        "description": line.product_id.description,
                    },
                    "qty": line.qty,
                    "uom_id": {
                        "name": line.uom_id.name, 
                    },
                    "lot_id": {
                        "number": line.lot_id.number,
                        "weight": line.lot_id.weight,
                    },
                    "notes": line.notes,
                })
                j=0
                for line2 in line.expand_lines:
                    j+=1
                    data.append({
                        "prefix": "%d.%d"%(i,j),
                        "product_id": {
                            "code": line2.product_id.code,
                            "name": line2.product_id.name,
                            "description": line2.product_id.description,
                        },
                        "qty": line2.qty,
                        "uom_id": {
                            "name": line2.uom_id.name, 
                        },
                        "lot_id": {
                            "number": line2.lot_id.number,
                            "weight": line2.lot_id.weight,
                        },
                        "notes": line2.notes,
                    })
            vals[obj.id]=data
        return vals

    def get_first_line(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=obj.lines[0].id if obj.lines else None
        return vals

    def get_sale(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.related_id and obj.related_id._model=="sale.order":
                sale_id=obj.related_id.id
            else:
                sale_id=None
            vals[obj.id]=sale_id
        return vals

    #Chin Update invoice_id in lines
    def update_invoice(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            inv_id = obj.invoice_id.id if obj.invoice_id else None
            for move in obj.lines:
                move.write({"invoice_id":inv_id})

    def search_container(self, clause, context={}):
        print("search_container",clause)
        val = clause[2]
        print("val",val)
        if not val:
            return []
        cond=["or",["container_id","=",val],["lines.container_id", "=", val]]
        print("cond",cond)
        return cond

    def update_locations(self, ids, context={}):
        obj=self.browse(ids[0])
        for line in obj.lines:
            line.write({"location_from_id": obj.location_from_id.id, "location_to_id": obj.location_to_id.id})

    def check_dup_lots(self,ids,context={}):
        obj=self.browse(ids[0])
        lots={}
        for line in obj.lines:
            lot_id=line.lot_id.id
            if not lot_id:
                continue
            if lot_id in lots:
                raise Exception("Duplicate lot in picking: %s %s"%(obj.number,line.lot_id.number))
            lots[lot_id]=line

    def transfer_containers(self,journal_id,container_ids,context={}):
        print("transfer_containers",journal_id,container_ids)
        journal=get_model("stock.journal").browse(journal_id)
        pick_vals={
            "journal_id": journal.id,
            "type": journal.type,
            "lines": [],
        }
        for cont in get_model("stock.container").browse(container_ids):
            for bal in cont.stock_balances:
                if bal.qty_phys<=0:
                    continue
                prod=bal.product_id
                line_vals={
                    "location_from_id": journal.location_from_id.id,
                    "location_to_id": journal.location_to_id.id,
                    "product_id": prod.id,
                    "qty": 1, # XXX
                    "uom_id": prod.uom_id.id,
                    "lot_id": bal.lot_id.id,
                    "container_id": cont.id,
                }
                pick_vals["lines"].append(("create",line_vals))
        print("pick_vals")
        pprint(pick_vals)
        t0=time.time()
        pick_id=self.create(pick_vals,context={"pick_type":pick_vals["type"],"journal_id":journal_id})
        t1=time.time()
        print("created picking in %s s"%(t1-t0))
        self.set_done([pick_id])
        t2=time.time()
        print("validated picking in %s s"%(t2-t1))
        pick=self.browse(pick_id)
        return {
            "picking_id": pick_id,
            "picking_number": pick.number,
        }

    def transfer_containers_fast_old(self,journal_id,container_ids,deactivate_lots=None,context={}):
        print("transfer_containers_fast",journal_id,container_ids,deactivate_lots)
        t0=time.time()
        db=database.get_connection()
        journal=get_model("stock.journal").browse(journal_id)
        pick_vals={
            "journal_id": journal.id,
            "type": journal.type,
            "lines": [],
        }
        pprint(pick_vals)
        pick_id=self.create(pick_vals,context={"pick_type":pick_vals["type"],"journal_id":journal_id})
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        for cont in get_model("stock.container").browse(container_ids):
            for bal in cont.stock_balances:
                if bal.qty_phys<=0:
                    continue
                prod=bal.product_id
                location_from_id=journal.location_from_id.id
                location_to_id=journal.location_to_id.id
                product_id=prod.id
                qty=1
                uom_id=prod.uom_id.id
                lot_id=bal.lot_id.id
                container_id=cont.id
                db.execute("INSERT INTO stock_move (picking_id,date,journal_id,location_from_id,location_to_id,product_id,qty,uom_id,lot_id,container_id,state) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')",pick_id,t,journal_id,location_from_id,location_to_id,product_id,qty,uom_id,lot_id,container_id)
        t1=time.time()
        print("created picking in %s s"%(t1-t0))
        self.set_done_fast([pick_id])
        t2=time.time()
        print("validated picking in %s s"%(t2-t1))
        pick=self.browse(pick_id)
        if deactivate_lots:
            self._deactivate_lots(pick_id)
        return {
            "picking_id": pick_id,
            "picking_number": pick.number,
        }

    def onchange_uom2(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        uom2_id = line.get("uom2_id")
        #if not uom2_id:
        #    return
        qty=line["qty"]
        uom_id=line["uom_id"]
        prod_id=line["product_id"]
        qty2=get_model("uom").convert(qty,uom_id,uom2_id,product_id=line["product_id"])
        line["qty2"]=qty2
        return data

    def validate_containers_fast(self,lines, journal_code, container_no, vals=None,context={}):
        print("validate_containers_fast",journal_code,container_no)
        t0=time.time()
        db=database.get_connection()
        res=get_model("stock.journal").search_browse([["code","=",journal_code]])
        if not res:
            raise Exception("No Journal with Code %s found" % journal_code)
        journal = res[0]
        container_id=get_model("stock.container").create({"number":container_no})
        print("lines ", lines)
        print("container id ", container_id)
        pick_vals={
            "journal_id": journal.id,
            "type": journal.type,
            "lines": [],
        }
        if vals:
            pick_vals.update(vals)
        pprint(pick_vals)
        pick_id=self.create(pick_vals,context={"pick_type":pick_vals["type"],"journal_id":pick_vals["journal_id"]})
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        for l in lines:
            journal_id=journal.id
            product_id=l["product_id"]
            location_from_id=journal.location_from_id.id
            location_to_id=journal.location_to_id.id
            qty=1
            uom_id=l["uom_id"]
            lot_id=l["lot_id"]
            container_id=container_id
            db.execute("INSERT INTO stock_move (picking_id,date,journal_id,location_from_id,location_to_id,product_id,qty,uom_id,lot_id,container_id,state) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')",pick_id,t,journal_id,location_from_id,location_to_id,product_id,qty,uom_id,lot_id,container_id)
            db.execute("UPDATE stock_lot SET product_id=%s WHERE id=%s",product_id,lot_id)
        t1=time.time()
        print("created picking in %s s"%(t1-t0))
        self.set_done_fast([pick_id])
        t2=time.time()
        print("validated picking in %s s"%(t2-t1))
        pick=self.browse(pick_id)
        if deactivate_lots:
            self._deactivate_lots(pick_id)
        return {
            "picking_id": pick_id,
            "picking_number": pick.number,
        }

    def validate_containers_fast_async(self, lines, journal_code, container_no, vals=None, deactivate_lots=None,context={}):
        user_id = access.get_active_user()
        company_id = access.get_active_company()
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "stock.picking",
            "method": "validate_containers_fast",
            "user_id": user_id,
            "company_id": company_id,
            "args": json.dumps({
                "journal_code": journal_code,
                "container_no": container_no,
                "lines": lines,
                "deactivate_lots": deactivate_lots,
            }),
        }
        get_model("bg.task").create(vals)

    def transfer_containers_fast_async(self, journal_id, container_ids, vals=None, deactivate_lots=None,context={}):
        user_id = access.get_active_user()
        company_id = access.get_active_company()
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "stock.picking",
            "method": "transfer_containers_fast",
            "user_id": user_id,
            "company_id": company_id,
            "args": json.dumps({
                "journal_id": journal_id,
                "container_ids": container_ids,
                "vals": vals,
                "deactivate_lots": deactivate_lots,
            }),
        }
        print("transfer_containers_fast_async => \n%s",vals)
        get_model("bg.task").create(vals)

    def _deactivate_lots(self,ids):
        for p in self.browse(ids):
            lot_ids=[l.lot_id.id for l in p.lines]
            get_model("stock.lot").write(lot_ids,{"state":"inactive"})

    def transfer_containers_fast(self,journal_id,container_ids,vals=None,deactivate_lots=None,context={}):
        print("transfer_containers_fast",journal_id,container_ids)
        t0=time.time()
        db=database.get_connection()
        journal=get_model("stock.journal").browse(journal_id)
        pick_vals={
            "journal_id": journal.id,
            "type": journal.type,
            "lines": [],
        }
        if vals:
            pick_vals.update(vals)
        pprint(pick_vals)
        pick_id=self.create(pick_vals,context={"pick_type":pick_vals["type"],"journal_id":journal_id})
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        for cont in get_model("stock.container").browse(container_ids):
            for bal in cont.stock_balances:
                if bal.qty_phys<=0:
                    continue
                prod=bal.product_id
                location_from_id=journal.location_from_id.id
                location_to_id=journal.location_to_id.id
                product_id=prod.id
                qty=1
                uom_id=prod.uom_id.id
                lot_id=bal.lot_id.id
                container_id=cont.id
                db.execute("INSERT INTO stock_move (picking_id,date,journal_id,location_from_id,location_to_id,product_id,qty,uom_id,lot_id,container_id,state) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')",pick_id,t,journal_id,location_from_id,location_to_id,product_id,qty,uom_id,lot_id,container_id)
        t1=time.time()
        print("created picking in %s s"%(t1-t0))
        self.set_done_fast([pick_id])
        t2=time.time()
        print("validated picking in %s s"%(t2-t1))
        pick=self.browse(pick_id)
        if deactivate_lots: #XXX
            self._deactivate_lots([pick_id])
        return {
            "picking_id": pick_id,
            "picking_number": pick.number,
        }

Picking.register()
