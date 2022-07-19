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
from netforce.access import get_active_user
from netforce.database import get_connection
from netforce import access
from netforce import utils
from netforce import database


class Contact(Model):
    _name = "contact"
    _string = "Contact"
    _audit_log = True
    _export_field = "name"
    _key = ["code"]
    #_key = ["name"]
    _content_search=True
    _fields = {
        "user_id": fields.Many2One("base.user", "User"),
        "type": fields.Selection([["person", "Individual"], ["org", "Organization"]], "Contact Type", required=True, search=True),
        "customer": fields.Boolean("Is Customer", search=True),
        "supplier": fields.Boolean("Is Supplier", search=True),
        "agent": fields.Boolean("Is Agent", search=True),
        "name": fields.Char("Name", required=True, search=True, translate=True, size=256),
        "code": fields.Char("Code", search=True, required=True),
        "phone": fields.Char("Phone", search=True),
        "fax": fields.Char("Fax"),
        "website": fields.Char("Website"),
        "industry": fields.Char("Industry"),  # XXX: deprecated
        "employees": fields.Char("Employees"),
        "revenue": fields.Char("Annual Revenue"),
        "description": fields.Text("Description"),
        "tax_no": fields.Char("Tax ID Number"),
        "id_card_no": fields.Char("ID Card Number"),
        "tax_branch_no" : fields.Char("Tax Branch ID"),
        "bank_account_no": fields.Char("Bank Account Number"),
        "bank_account_name": fields.Char("Bank Account Name"),
        "bank_account_details": fields.Char("Bank Account Details"),
        "active": fields.Boolean("Active"),
        "account_receivable_id": fields.Many2One("account.account", "Account Receivable", multi_company=True),
        "account_payable_id": fields.Many2One("account.account", "Account Payable", multi_company=True),
        "sale_tax_id": fields.Many2One("account.tax.rate", "Sales Tax"),
        "purchase_tax_id": fields.Many2One("account.tax.rate", "Purchase Tax"),
        "currency_id": fields.Many2One("currency", "Default Currency"),
        "payables_due": fields.Decimal("Payables Due"),
        "payables_overdue": fields.Decimal("Payables Overdue"),
        "receivables_due": fields.Decimal("Receivables Due"),
        "receivables_overdue": fields.Decimal("Receivables Overdue"),
        "payable_credit": fields.Decimal("Payable Credit", function="get_credit", function_multi=True),
        "receivable_credit": fields.Decimal("Receivable Credit", function="get_credit", function_multi=True),
        "payable_balance": fields.Decimal("Payable Balance", function="get_payable_balance"),
        "receivable_balance": fields.Decimal("Receivable Balance", function="get_receivable_balance"),
        "invoices": fields.One2Many("account.invoice", "contact_id", "Invoices"),
        "sale_price_list_id": fields.Many2One("price.list", "Sales Price List", condition=[["type", "=", "sale"]]),
        "purchase_price_list_id": fields.Many2One("price.list", "Purchasing Price List", condition=[["type", "=", "purchase"]]),
        #"purchase_currency_id": fields.Many2One("currency","Purchase Currency"),
        "categ_id": fields.Many2One("contact.categ", "Contact Category",search=True),
        "payment_terms": fields.Char("Payment Terms"), # XXX: deprecated
        "pay_term_id": fields.Many2One("payment.term","Payment Terms"), # XXX: deprecated
        "sale_pay_term_id": fields.Many2One("payment.term","Sales Payment Terms"),
        "purchase_pay_term_id": fields.Many2One("payment.term","Purchase Payment Terms"),
        "opports": fields.One2Many("sale.opportunity", "contact_id", "Open Opportunities", condition=[["state", "=", "open"]]),
        "addresses": fields.One2Many("address", "contact_id", "Addresses"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "bank_accounts": fields.One2Many("bank.account", "contact_id", "Bank Accounts"),
        "bank_account_id": fields.Many2One("bank.account","Default Bank Account",function="get_bank_account"),
        "last_name": fields.Char("Last Name"),
        "first_name": fields.Char("First Name"),
        "first_name2": fields.Char("First Name (2)"),
        "first_name3": fields.Char("First Name (3)"),
        "title": fields.Char("Title"),
        "position": fields.Char("Position"),
        "report_to_id": fields.Many2One("contact", "Reports To"),
        "mobile": fields.Char("Mobile",search=True),
        "email": fields.Char("Email", search=True),
        "home_phone": fields.Char("Home Phone"),
        "other_phone": fields.Char("Other Phone"),
        "assistant": fields.Char("Assistant"),
        "assistant_phone": fields.Char("Assistant Phone"),
        "birth_date": fields.Date("Birth Date"),
        "department": fields.Char("Department"),
        "job_templates": fields.Many2Many("job.template", "Job Template"),
        "projects": fields.One2Many("project", "contact_id", "Projects"),
        "documents": fields.One2Many("document", "contact_id", "Documents"),
        "assigned_to_id": fields.Many2One("base.user", "Assigned To"),
        "lead_source": fields.Char("Lead source"),
        "lead_source_id": fields.Many2One("lead.source","Lead Source"),
        "inquiry_type": fields.Char("Type of inquiry"),
        "relations": fields.One2Many("contact.relation", "from_contact_id", "Relations", function="_get_relations"),
        "contact_id": fields.Many2One("contact", "Parent"),  # XXX: not used any more, just there for migration
        "emails": fields.One2Many("email.message", "name_id", "Emails"),
        "default_address_id": fields.Many2One("address", "Default Address", function="get_default_address"),
        "quotations": fields.One2Many("sale.quot", "contact_id", "Quotations"),
        "sale_orders": fields.One2Many("sale.order", "contact_id", "Sales Orders"),
        "purchase_orders": fields.One2Many("purchase.order", "contact_id", "Purchase Orders"),
        "country_id": fields.Many2One("country", "Country", search=True),
        "region": fields.Char("Region"),  # XXX: deprecated
        "service_items": fields.One2Many("service.item", "contact_id", "Service Items", condition=[["parent_id", "=", None]]),
        "contracts": fields.One2Many("service.contract", "contact_id", "Contracts"),
        "branch": fields.Char("Branch"),
        "industry_id": fields.Many2One("industry", "Industry", search=True),
        "region_id": fields.Many2One("region", "Region", search=True),
        "commission_po_percent": fields.Decimal("Commission Purchase Percentage"),
        "business_area_id": fields.Many2One("business.area", "Business Area", search=True),
        "fleet_size_id": fields.Many2One("fleet.size", "Fleet Size", search=True),
        "groups": fields.Many2Many("contact.group", "Groups", search=True),
        "sale_journal_id": fields.Many2One("account.journal", "Sales Journal"),
        "purchase_journal_id": fields.Many2One("account.journal", "Purchase Journal"),
        "pay_in_journal_id": fields.Many2One("account.journal", "Receipts Journal"),
        "pay_out_journal_id": fields.Many2One("account.journal", "Disbursements Journal"),
        "pick_in_journal_id": fields.Many2One("stock.journal", "Goods Receipt Journal"),
        "pick_out_journal_id": fields.Many2One("stock.journal", "Goods Issue Journal"),
        "coupons": fields.One2Many("sale.coupon", "contact_id", "Coupons"),
        "companies": fields.Many2Many("company", "Companies"), # XXX: deprecated
        "company_id": fields.Many2One("company", "Company"),
        "request_product_groups": fields.Many2Many("product.group","Request Product Groups",reltable="m2m_contact_request_product_groups",relfield="contact_id",relfield_other="group_id"),
        "exclude_product_groups": fields.Many2Many("product.group","Exclude Product Groups",reltable="m2m_contact_exclude_product_groups",relfield="contact_id",relfield_other="group_id"),
        "picture": fields.File("Picture"),
        "users": fields.One2Many("base.user","contact_id","Users"),
        "ship_free": fields.Boolean("Free Shipping"),
        "contact_person_id": fields.Many2One("contact","Primary Contact Person",condition=[["type","=","person"]]),
        "org_id": fields.Many2One("contact","Organization",condition=[["type","=","org"]]),
        "contact_persons": fields.One2Many("contact","org_id","Contact Persons"),
        "sale_discount": fields.Decimal("Customer Discount (%)"),
        "min_life_remain_percent": fields.Integer("Min Shelf Life Remaining (%)"), # XXX: deprecated
        "min_shelf_life": fields.Selection([["50","50%"],["75","75%"]],"Min Shelf Life"),
        "max_lots_per_sale": fields.Integer("Max Lots Per Sale"),
        "commission_parent_id": fields.Many2One("contact","Commission Parent"),
        "commission_amount": fields.Decimal("Commission Amount",function="get_commission_amount"),
        "seller_contact_id": fields.Many2One("contact","Sales Person"),
        "gender": fields.Selection([["m","Male"],["f","Female"]],"Gender"),
        "refer_id": fields.Many2One("contact","Referred By"),
        "line_account": fields.Char("Line Account"),
        "facebook_account": fields.Char("Facebook Account"),
        "track_id": fields.Many2One("account.track.categ","Tracking"),
        "state": fields.Selection([["active","Active"],["inactive","Inactive"]],"Status",search=True),
        "sale_pay_term_days": fields.Integer("Sales Payment Term"),
        "sale_max_credit": fields.Decimal("Sales Max Credit"),
        "sale_pay_method_id": fields.Many2One("payment.method", "Sales Payment Method"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),
        "default_ship_address_id": fields.Many2One("address", "Default Shipping Address", function="get_default_ship_address"),
        "default_bill_address_id": fields.Many2One("address", "Default Billing Address", function="get_default_bill_address"),
        "folder_id": fields.Many2One("folder","Folder"),
        "contact_person_emails": fields.Char("Contact Person Emails",function="get_contact_person_emails"),
    }

    def _get_number(self, context={}):
        seq_id=context.get("sequence_id")
        if not seq_id:
            seq_id = get_model("sequence").find_sequence(type="contact")
            if not seq_id:
                return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = self.search([["code", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    _defaults = {
        "active": True,
        "type": "org",
        "code": _get_number,
        "state": "active",
        "company_id": lambda *a: access.get_active_company(),
    }
    _order = "create_time desc, name"
    #_constraints=["check_email"]

    def create(self, vals, **kw):
        if not vals.get("type"):
            if vals.get("name"):
                vals["type"] = "org"
            elif vals.get("last_name"):
                vals["type"] = "person"
        if vals.get("type") == "person":
            if vals.get("first_name") and vals.get("last_name"):
                vals["name"] = vals["first_name"] + " " + vals["last_name"]
            elif vals.get("last_name"):
                vals["name"] = vals.get("last_name")
        new_id = super().create(vals, **kw)
        return new_id

    def write(self, ids, vals, set_name=True, **kw):
        super().write(ids, vals, **kw)
        if set_name:
            for obj in self.browse(ids):
                if obj.type == "person":
                    if obj.first_name:
                        name = obj.first_name + " " + obj.last_name
                    else:
                        name = obj.last_name
                    if name:
                        obj.write({"name": name}, set_name=False)

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.code:
                name = "[%s] %s" % (obj.code, obj.name)
            else:
                name = obj.name
            vals.append((obj.id, name, obj.image))
        return vals

    def name_search(self, name, condition=None, context={}, limit=None, **kw):
        print("condition",condition)
        if condition:
            cond=condition
        else:
            cond=[]
        cond.append(["or",["code", "ilike", name],["name","ilike",name]])
        ids = self.search(cond, limit=limit)
        return self.name_get(ids, context=context)

    def get_credit(self, ids, context={}):
        print("contact.get_credit", ids)
        currency_id = context.get("currency_id")
        print("currency_id", currency_id)
        vals = {}
        for obj in self.browse(ids):
            ctx={
                "contact_id": obj.id,
            }
            r_credit = 0
            p_credit = 0
            for acc in get_model("account.account").search_browse([["type","=","cust_deposit"]],context=ctx):
                r_credit-=acc.balance
            for acc in get_model("account.account").search_browse([["type","=","sup_deposit"]],context=ctx):
                p_credit+=acc.balance
            for line in get_model("account.move.line").search_browse([["account_id.type","=","receivable"],["contact_id","=",obj.id],["credit",">=",0],["reconcile_id","=",None]]):
                r_credit+=line.credit # XXX
            for line in get_model("account.move.line").search_browse([["account_id.type","=","payable"],["contact_id","=",obj.id],["debit",">=",0],["reconcile_id","=",None]]):
                p_credit+=line.debit # XXX
            vals[obj.id] = {
                "receivable_credit": r_credit,
                "payable_credit": p_credit,
            }
        return vals

    def get_address_str(self, ids, context={}):
        obj = self.browse(ids[0])
        if not obj.addresses:
            return ""
        addr = obj.addresses[0]
        return addr.name_get()[0][1]

    def _get_relations(self, ids, context={}):
        cond = ["or", ["from_contact_id", "in", ids], ["to_contact_id", "in", ids]]
        rels = get_model("contact.relation").search_read(cond, ["from_contact_id", "to_contact_id"])
        vals = {}
        for rel in rels:
            from_id = rel["from_contact_id"][0]
            to_id = rel["to_contact_id"][0]
            vals.setdefault(from_id, []).append(rel["id"])
            vals.setdefault(to_id, []).append(rel["id"])
        return vals

    def get_payable_balance(self, ids, context={}):
        print("contact.get_payable_balance", ids)
        vals = {}
        for obj in self.browse(ids):
            bal=0
            for line in get_model("account.move.line").search_browse([["account_id.type","=","payable"],["contact_id","=",obj.id]]):
                bal+=line.credit-line.debit
            vals[obj.id]=bal
        return vals

    def get_receivable_balance(self, ids, context={}):
        print("contact.get_receivable_balance", ids)
        vals = {}
        for obj in self.browse(ids):
            bal=0
            for line in get_model("account.move.line").search_browse([["account_id.type","=","receivable"],["contact_id","=",obj.id]]):
                bal+=line.debit-line.credit
            vals[obj.id]=bal
        return vals

    def get_address(self, ids, pref_type=None, context={}):
        obj = self.browse(ids)[0]
        for addr in obj.addresses:
            if pref_type and addr.type != pref_type:
                continue
            return addr.id
        if obj.addresses:
            return obj.addresses[0].id
        return None

    def get_default_address(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            addr_id = None
            for addr in obj.addresses:
                if addr.type == "billing":
                    addr_id = addr.id
                    break
            if not addr_id and obj.addresses:
                addr_id = obj.addresses[0].id
            vals[obj.id] = addr_id
        print("XXX", vals)
        return vals

    def check_email(self,ids,context={}):
        for obj in self.browse(ids):
            if not obj.email:
                continue
            if not utils.check_email_syntax(obj.email):
                raise Exception("Invalid email for contact '%s'"%obj.name)

    def find_address(self,ids,addr_vals,context={}):
        obj=self.browse(ids[0])
        addr_id=None
        for addr in obj.addresses:
            if "address" in addr_vals and addr_vals["address"]!=addr.address:
                continue
            if "address2" in addr_vals and addr_vals["address2"]!=addr.address2:
                continue
            if "city" in addr_vals and addr_vals["city"]!=addr.city:
                continue
            if "postal_code" in addr_vals and addr_vals["postal_code"]!=addr.postal_code:
                continue
            if "country_id" in addr_vals and addr_vals["country_id"]!=addr.country_id.id:
                continue
            if "province_id" in addr_vals and addr_vals["province_id"]!=addr.province_id.id:
                continue
            if "district_id" in addr_vals and addr_vals["district_id"]!=addr.district_id.id:
                continue
            if "subdistrict_id" in addr_vals and addr_vals["subdistrict_id"]!=addr.subdistrict_id.id:
                continue
            if "phone" in addr_vals and addr_vals["phone"]!=addr.phone:
                continue
            if "first_name" in addr_vals and addr_vals["phone"]!=addr.first_name:
                continue
            if "last_name" in addr_vals and addr_vals["last_name"]!=addr.last_name:
                continue
            addr_id=addr.id
            break
        return addr_id

    def add_address(self,ids,addr_vals,context={}):
        addr_id=self.find_address(ids)
        if not addr_id:
            vals=addr_vals.copy()
            vals["contact_id"]=ids[0]
            addr_id=get_model("address").create(vals)
        return addr_id

    def onchange_categ(self,context={}):
        print("onchange_categ")
        data=context.get("data")
        categ_id=data["categ_id"]
        if not categ_id:
            return
        categ=get_model("contact.categ").browse(categ_id)
        seq=categ.sequence_id
        if not seq:
            return
        number=self._get_number(context={"sequence":seq.id})
        data["code"]=number
        return data

    def get_commission_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for line in get_model("sale.order.line").search_browse([["order_id.seller_contact_id","=",obj.id],["product_id","!=",None]]):
                prod=line.product_id
                amt+=(line.qty or 1)*(prod.commission_seller or 0)
            vals[obj.id]=amt
        return vals

    def create_track(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.code:
            raise Exception("Invalid code")
        res=get_model("account.track.categ").search([["code","=",obj.code]])
        if res:
            track_id=res[0]
        else:
            vals={
                "name": obj.name,
                "code": obj.code,
                "contact_id": obj.id,
            }
            track_id=get_model("account.track.categ").create(vals)
        obj.write({"track_id":track_id})
        return track_id

    def get_default_ship_address(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            addr_id = None
            for addr in obj.addresses:
                if addr.type == "shipping":
                    addr_id = addr.id
                    break
            vals[obj.id] = addr_id
        return vals

    def get_default_bill_address(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            addr_id = None
            for addr in obj.addresses:
                if addr.type == "billing":
                    addr_id = addr.id
                    break
            vals[obj.id] = addr_id
        return vals

    def get_last_name_options(self, context={}):
        print("get_last_name_options")
        data=context["data"]
        db=database.get_connection()
        res=db.query("SELECT last_name FROM contact WHERE last_name IS NOT NULL")
        names=[(r.last_name,None) for r in res]
        names=list(set(names))
        print("=> names",names)
        return names

    def get_first_name_options(self, context={}):
        print("get_first_name_options")
        data=context["data"]
        db=database.get_connection()
        res=db.query("SELECT first_name FROM contact WHERE first_name IS NOT NULL")
        names=[(r.first_name,None) for r in res]
        names=list(set(names))
        print("=> names",names)
        return names

    def arch_dup(self,context={}):
        names={}
        arch_ids=[]
        for cont in self.search_browse([],order="name"):
            if cont.name in names:
                arch_ids.append(cont.id)
            else:
                names[cont.name]=cont.id
        if arch_ids:
            self.write(arch_ids,{"active":False})

    def get_bank_account(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            acc_id=None
            if obj.bank_accounts:
                acc_id=obj.bank_accounts[0].id
            vals[obj.id]=acc_id
        return vals

    def name_get_cols(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.code:
                name = "%s --- %s" % (obj.code, obj.name)
            else:
                name = obj.name
            vals.append((obj.id, name, obj.image))
        return vals

    def name_search_cols(self, name, condition=None, context={}, limit=None, **kw):
        print("condition",condition)
        if condition:
            cond=condition
        else:
            cond=[]
        cond.append(["or",["code", "ilike", name],["name","ilike",name]])
        ids = self.search(cond, limit=limit)
        return self.name_get_cols(ids, context=context)

    def create_folder(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.folder_id:
            return obj.folder_id.id
        vals={
            "name": obj.name,
            "contact_id": obj.id,
        }
        folder_id=get_model("folder").create(vals)
        obj.write({"folder_id":folder_id})
        return folder_id

    def get_contact_person_emails(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            emails=[]
            for p in obj.contact_persons:
                 if p.email:
                    emails.append(p.email)
            vals[obj.id]=", ".join(emails)
        return vals
            
Contact.register()
