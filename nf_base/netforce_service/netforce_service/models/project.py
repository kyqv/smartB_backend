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


class Project(Model):
    _name = "project"
    _string = "Project"
    _audit_log = True
    _fields = {
        "name": fields.Char("Project Name", required=True, search=True),
        "number": fields.Char("Project Code", search=True),
        "contact_id": fields.Many2One("contact", "Customer", search=True),
        "start_date": fields.Date("Start Date"),
        "end_date": fields.Date("End Date (Expected)"),
        "end_date_actual": fields.Date("End Date (Actual)"),
        "product_id": fields.Many2One("product", "Product"),  # XXX: deprecated
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "state": fields.Selection([["in_progress", "In Progress"], ["done", "Completed"], ["canceled", "Canceled"]], "Status", required=True),
        "jobs": fields.One2Many("job", "project_id", "Jobs"),
        "tasks": fields.One2Many("task", "project_id", "Tasks"),
        "work_time": fields.One2Many("work.time", "job_id", "Work Time"),
        "claims": fields.One2Many("product.claim", "project_id", "Claim Bills"),
        "borrows": fields.One2Many("product.borrow", "project_id", "Borrow Requests"),
        "description": fields.Text("Description"),
        "issues": fields.One2Many("issue","project_id","Issues"),
        "resources": fields.Many2Many("service.resource","Resources"),
        "milestones": fields.One2Many("project.milestone","project_id","Milestones"),
        "sale_price": fields.Decimal("Sales Price"),
        "track_id": fields.Many2One("account.track.categ","Actual Cost Tracking Code"),
        "track_entries": fields.One2Many("account.track.entry",None,"Tracking Entries",function="get_track_entries",function_write="write_track_entries"),
        "cost_amount": fields.Decimal("Cost Amount", function="get_profit", function_multi=True),
        "profit_amount": fields.Decimal("Profit Amount", function="get_profit", function_multi=True),
        "margin_percent": fields.Decimal("Margin %", function="get_profit", function_multi=True),
        "sale_orders": fields.One2Many("sale.order","project_id","Sales Orders"),
        "sale_order_id": fields.Many2One("sale.order","Sales Order",function="get_sale_order"),
        "invoices": fields.One2Many("account.invoice","related_id","Invoices"),
        "amount_invoice": fields.Decimal("Invoiced Amount",function="get_amount_invoice",function_multi=True),
        "amount_paid": fields.Decimal("Paid Amount",function="get_amount_invoice",function_multi=True),
        "amount_unpaid": fields.Decimal("Unpaid Amount",function="get_amount_invoice",function_multi=True),
        "total_area": fields.Decimal("Total Area (sqm)"),
        "sale_price_area": fields.Decimal("Price Per Sqm",function="get_sale_price_area"),
        "sale_categ_id": fields.Many2One("sale.categ","Sales Category",search=True),
        "other_price": fields.Decimal("Other Price"),
    }
    _order = "start_date desc"

    _defaults = {
        "start_date": lambda *a: time.strftime("%Y-%m-%d"),
        "state": "in_progress",
    }

    def copy(self,ids,context={}):
        obj=self.browse(ids[0])
        vals={
            "name": obj.name,
            "number": obj.number,
            "contact_id": obj.contact_id.id,
            "start_date": obj.start_date,
            "end_date": obj.end_date,
            "description": description,
            "resources": [("set",[r.id for r in obj.resources])],
        }
        new_proj_id=self.create(vals,context=context)
        new_proj=self.browse(new_proj_id)
        track=obj.track_id
        if track:
            vals={
                "name": track.name, # XXX
                "type": track.type, 
                "code": track.code, # XXX
            }
            new_track_id=get_model("account.track.categ").create(vals)
            new_proj.write({"track_id":new_track_id})
            for subtrack in track.sub_tracks:
                vals={
                    "parent_id": new_track_id,
                    "name": subtrack.name, 
                    "type": subtrack.type, 
                    "code": subtrack.code, 
                }
                get_model("account.track.categ").create(vals)
        return {
            "next": {
                "name": "project",
                "mode": "form",
                "active_id": new_proj_id,
            },
            "flash": "New project copied from %s"%obj.name,
        }

    def get_track_entries(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if not obj.track_id:
                vals[obj.id]=[]
                continue
            res=get_model("account.track.entry").search([["track_id","child_of",obj.track_id.id]])
            vals[obj.id]=res
        return vals

    def get_profit(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_cost=obj.other_price or 0
            profit=None
            margin=None
            if obj.track_id:
                for line in obj.track_entries:
                    if line.amount<0:
                        total_cost+=-line.amount
                if obj.sale_price:
                    profit = obj.sale_price - total_cost
                    margin=profit*100/obj.sale_price
            vals[obj.id] = {
                "cost_amount": total_cost,
                "profit_amount": profit,
                "margin_percent": margin,
            }
        return vals

    def get_amount_invoice(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt_inv=0
            amt_paid=0
            for line in obj.track_entries:
                inv=line.related_id
                if inv._model!="account.invoice":
                    continue
                if inv.state in ("waiting_payment","paid"):
                    amt_inv-=line.amount
                    if inv.state=="paid":
                        amt_paid-=line.amount
            vals[obj.id]={
                "amount_invoice": amt_inv,
                "amount_paid": amt_paid,
                "amount_unpaid": amt_inv-amt_paid,
            }
        return vals

    def copy_to_cust_invoice(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.contact_id:
            raise Exception("Missing contact in project %s"%obj.name)
        vals={
            "type": "out",
            "inv_type": "invoice",
            "contact_id": obj.contact_id.id,
            "related_id": "project,%s"%obj.id,
        }
        inv_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"invoice"})
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv_id,
            },
        }

    def copy_to_sup_invoice(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.contact_id:
            raise Exception("Missing contact in project %s"%obj.name)
        vals={
            "type": "in",
            "inv_type": "invoice",
            "contact_id": obj.contact_id.id,
            "related_id": "project,%s"%obj.id,
        }
        inv_id=get_model("account.invoice").create(vals,context={"type":"in","inv_type":"invoice"})
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv_id,
            },
        }

    def get_sale_price_area(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.sale_price or 0)/obj.total_area if obj.total_area else None
        return vals

    def get_sale_order(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            sale_id=obj.sale_orders[0].id if obj.sale_orders else None
            vals[obj.id]=sale_id
        return vals

    def create_track(self,ids,context={}):
        obj=self.browse(ids[0])
        code=obj.number
        res=get_model("account.track.categ").search([["code","=",code]])
        if res:
            track_id=res[0]
        else:
            if not code:
                raise Exception("Missing project code")
            track_id=get_model("account.track.categ").create({
                "code": code,
                "name": obj.contact_id.name,
                "type": "1",
            })
        obj.write({"track_id":track_id})
        return {
            "next": {
                "name": "project",
                "mode": "form",
                "active_id": obj.id,
            },
            "flash": "Tracking code created",
        }

Project.register()
