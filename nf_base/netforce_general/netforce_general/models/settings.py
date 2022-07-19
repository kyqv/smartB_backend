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
from netforce import static
import datetime
from dateutil.relativedelta import relativedelta
from netforce import access

_days = [
    ["1", "1"],
    ["2", "2"],
    ["3", "3"],
    ["4", "4"],
    ["5", "5"],
    ["6", "6"],
    ["7", "7"],
    ["8", "8"],
    ["9", "9"],
    ["10", "10"],
    ["11", "11"],
    ["12", "12"],
    ["13", "13"],
    ["14", "14"],
    ["15", "15"],
    ["16", "16"],
    ["17", "17"],
    ["18", "18"],
    ["19", "19"],
    ["20", "20"],
    ["21", "21"],
    ["22", "22"],
    ["23", "23"],
    ["24", "24"],
    ["25", "25"],
    ["26", "26"],
    ["27", "27"],
    ["28", "28"],
    ["29", "29"],
    ["30", "30"],
    ["31", "31"],
]

_months = [
    ["1", "January"],
    ["2", "February"],
    ["3", "March"],
    ["4", "April"],
    ["5", "May"],
    ["6", "June"],
    ["7", "July"],
    ["8", "August"],
    ["9", "September"],
    ["10", "October"],
    ["11", "November"],
    ["12", "December"],
]


class Settings(Model):
    _name = "settings"
    _key = ["name"]
    _audit_log = True
    _fields = {
        "name": fields.Char("Display Name"),  # not used any more...
        "legal_name": fields.Char("Legal Name"),  # not used any more...
        "company_type_id": fields.Many2One("company.type", "Organization Type"),
        "currency_id": fields.Many2One("currency", "Default Currency", multi_company=True),
        "account_receivable_id": fields.Many2One("account.account", "Account Receivable", multi_company=True),
        "tax_receivable_id": fields.Many2One("account.tax.rate", "Account Receivable Tax"),
        "account_payable_id": fields.Many2One("account.account", "Account Payable", multi_company=True),
        "tax_payable_id": fields.Many2One("account.tax.rate", "Account Payable Tax"),
        "year_end_day": fields.Selection(_days, "Financial Year End (Day)"),
        "year_end_month": fields.Selection(_months, "Financial Year End (Month)"),
        "lock_date": fields.Date("Lock Date"),
        "nf_email": fields.Char("Email to Netforce"),  # XXX: deprecated
        "share_settings": fields.One2Many("share.access", "settings_id", "Sharing Settings"),
        "currency_gain_id": fields.Many2One("account.account", "Currency Gain Account", multi_company=True),
        "currency_loss_id": fields.Many2One("account.account", "Currency Loss Account", multi_company=True),
        "unpaid_claim_id": fields.Many2One("account.account", "Unpaid Expense Claims Account", multi_company=True),
        "retained_earnings_account_id": fields.Many2One("account.account", "Retained Earnings Account", multi_company=True),
        "logo": fields.File("Company Logo", multi_company=True),
        "package": fields.Char("Package", readonly=True),
        "version": fields.Char("Version"),
        "tax_no": fields.Char("Tax ID Number", multi_company=True),
        "branch_no": fields.Char("Branch Number", multi_company=True),
        "addresses": fields.One2Many("address","settings_id","Addresses",function="get_addresses"),
        "date_format": fields.Char("Date Format"),
        "use_buddhist_date": fields.Boolean("Use Buddhist Date"),
        "phone": fields.Char("Phone", multi_company=True),
        "fax": fields.Char("Fax", multi_company=True),
        "website": fields.Char("Website", multi_company=True),
        "root_url": fields.Char("Root URL"),
        "sale_journal_id": fields.Many2One("account.journal", "Sales Journal"),
        "purchase_journal_id": fields.Many2One("account.journal", "Purchase Journal"),
        "pay_in_journal_id": fields.Many2One("account.journal", "Receipts Journal"),
        "pay_out_journal_id": fields.Many2One("account.journal", "Disbursements Journal"),
        "general_journal_id": fields.Many2One("account.journal", "General Journal"),
        "default_address_id": fields.Many2One("address", "Default Address", function="get_default_address"),
        "ar_revenue_id": fields.Many2One("account.account", "Revenue Account", multi_company=True),
        # XXX: rename for report
        "input_report_id": fields.Many2One("account.account", "Input Vat Account", multi_company=True),
        # XXX: rename for report
        "output_report_id": fields.Many2One("account.account", "Output Vat Account", multi_company=True),
        # XXX: rename for report
        "wht3_report_id": fields.Many2One("account.account", "WHT3 Account", multi_company=True),
        # XXX: rename for report
        "wht53_report_id": fields.Many2One("account.account", "WHT53 Account", multi_company=True),
        "sale_copy_picking": fields.Boolean("Auto-copy sales orders to goods issue"),
        "sale_copy_reserve_picking": fields.Boolean("Auto-copy sales orders to reservation goods transfer"),
        "sale_copy_invoice": fields.Boolean("Auto-copy sales orders to customer invoice"),
        "sale_copy_production": fields.Boolean("Auto-copy sales orders to production",multi_company=True),
        "sale_split_service": fields.Boolean("Split Sales Orders (service/non-service)"),
        "rounding_account_id": fields.Many2One("account.account", "Rounding Account", multi_company=True),
        "production_waiting_suborder": fields.Boolean("Wait Sub-Order"),  # XXX: check this
        "anon_profile_id": fields.Many2One("profile", "Anonymous User Profile"),
        "pick_in_journal_id": fields.Many2One("stock.journal", "Goods Receipt Journal"),
        "pick_out_journal_id": fields.Many2One("stock.journal", "Goods Issue Journal"),
        "pick_internal_journal_id": fields.Many2One("stock.journal", "Goods Transfer Journal"),
        "pick_out_return_journal_id": fields.Many2One("stock.journal", "Return To Supplier Journal"),
        "stock_count_journal_id": fields.Many2One("stock.journal", "Stock Count Journal"),
        "landed_cost_journal_id": fields.Many2One("stock.journal", "Landed Cost Journal"),
        "transform_journal_id": fields.Many2One("stock.journal", "Transform Journal"),
        "waste_journal_id": fields.Many2One("stock.journal", "Product Waste Journal"),
        "production_journal_id": fields.Many2One("stock.journal", "Production Journal"),
        "product_borrow_journal_id": fields.Many2One("stock.journal","Borrow Request Journal"),
        "stock_cost_mode": fields.Selection([["periodic","Periodic"],["perpetual","Perpetual"]],"Inventory Costing Mode"),
        "landed_cost_variance_account_id": fields.Many2One("account.account","Landed Cost Variance Account",multi_company=True),
        "est_ship_account_id": fields.Many2One("account.account","Estimate Shipping Account",multi_company=True),
        "est_duty_account_id": fields.Many2One("account.account","Estimate Duty Account",multi_company=True),
        "act_ship_account_id": fields.Many2One("account.account","Actual Shipping Account",multi_company=True),
        "act_duty_account_id": fields.Many2One("account.account","Actual Duty Account",multi_company=True),
        "menu_icon": fields.File("Menu Icon"),
        "stock_cost_auto_compute": fields.Boolean("Auto Compute Cost"),
        "purchase_copy_picking": fields.Boolean("Auto-copy purchase orders to goods receipt"),
        "purchase_copy_invoice": fields.Boolean("Auto-copy purchase orders to supplier invoice"),
        "lot_expiry_journal_id": fields.Many2One("stock.journal", "Lot Expiry Journal"),
        "life_75_journal_id": fields.Many2One("stock.journal", "75% Life Journal"),
        "life_50_journal_id": fields.Many2One("stock.journal", "50% Life Journal"),
        "forecast_journal_id": fields.Many2One("stock.journal", "Forecast Journal"),
        "google_api_key": fields.Char("Google API Key"),
        "bank_reconcile_max_days": fields.Integer("Bank Reconcile Max Days"),
        "require_qc_in": fields.Boolean("Require QC for goods receipts"),
        "require_qc_out": fields.Boolean("Require QC for goods issues"),
        "commission_parent": fields.Decimal("Commission % To Seller Parent"),
        "commission_grand_parent": fields.Decimal("Commission % To Seller Grand Parent"),
        "commission_remain": fields.Decimal("Remaining Commission % To Seller",function="get_commission_remain"),
        "purchase_check_received_qty": fields.Decimal("Check Extra Received Qty %"),
        "purchase_min_approvals": fields.Integer("Purchase order minimum number of approvals"),
        "pr_require_supplier": fields.Boolean("Require Supplier In Purchase Requests"),
        "sale_check_delivered_qty": fields.Decimal("Check Extra Shipped Qty %"),
        "pick_out_create_invoice": fields.Boolean("Create invoice when goods issue is validated"),
        "approve_invoice": fields.Boolean("Approve Invoices"),
        "approve_payment": fields.Boolean("Approve Payments"),
        "approve_pick_in": fields.Boolean("Approve GR"),
        "approve_pick_internal": fields.Boolean("Approve GT"),
        "approve_pick_out": fields.Boolean("Approve GI"),
        "approve_quot": fields.Boolean("Approve Quotations"),
        "approve_sale": fields.Boolean("Approve Sales Orders"),
        "approve_sale_reserve": fields.Boolean("Approve Sales Reservations"),
        "approve_purchase": fields.Boolean("Approve Purchase Orders"),
        "approve_purchase_request": fields.Boolean("Approve Purchase Requests"),
        "approve_production": fields.Boolean("Approve Production Orders"),
        "check_neg_stock": fields.Boolean("Check Negative Stock"),
        "unique_barcode": fields.Boolean("Unique Barcodes"),
        "freight_charge_cust_id": fields.Many2One("account.account", "Freight Charge (Customer) Account", multi_company=True), # Chin
        "freight_charge_cust_track_id": fields.Many2One("account.track.categ", "Freight Charge (Customer) Track-1", condition=[["type", "=", "1"]]), #Chin
        "freight_charge_cust_track2_id": fields.Many2One("account.track.categ", "Freight Charge (Customer) Track-2", condition=[["type", "=", "2"]]), #Chin
        "freight_charge_supp_id": fields.Many2One("account.account", "Freight Charge (Supplier) Account", multi_company=True), # Chin
        "freight_charge_supp_track_id": fields.Many2One("account.track.categ", "Freight Charge (Supplier) Track-1", condition=[["type", "=", "1"]]), #Chin
        "freight_charge_supp_track2_id": fields.Many2One("account.track.categ", "Freight Charge (Supplier) Track-2", condition=[["type", "=", "2"]]), #Chin

        # for cycle stockcount
        "total_stockcount_per_year": fields.Integer("Total Stock-Count per Year"), #Max
        "cycle_stockcount_abc": fields.Boolean("Cycle Stock-Count by ABC Analysis"), #Max
        "cycle_stockcount_xyz": fields.Boolean("Cycle Stock-Count by XYZ Analysis"), #Max
        "a_by_percentage": fields.Integer("Category A by percentage"), #Max
        "b_by_percentage": fields.Integer("Category B by percentage"), #Max
        "c_by_percentage": fields.Integer("Category C by percentage",function="get_c_percentage"), #Max
        "x_by_percentage": fields.Integer("Category X by percentage"), #Max
        "y_by_percentage": fields.Integer("Category Y by percentage"), #Max
        "z_by_percentage": fields.Integer("Category Z by percentage",function="get_z_percentage"), #Max
        
        "x2z_ratio": fields.Integer("Stock-Count Frequency Ratio (X to Z)"), #Max
        "y2z_ratio": fields.Integer("Stock-Count Frequency Ratio (Y to Z)"), #Max
        "z_total_stockcount_per_year": fields.Integer("Total Stock-Count per Year (Z)"), #Max
        "y_total_stockcount_per_year": fields.Integer("Total Stock-Count per Year (Y)",function="get_y_total_stockcount"), #Max
        "x_total_stockcount_per_year": fields.Integer("Total Stock-Count per Year (X)",function="get_x_total_stockcount"), #Max
        "xyz_period": fields.Selection([["3","Last 3 Months"],["6","Last 6 Months"],["12","Last 12 Months"]],"Assign XYZ by past data"), #Max
    }
    _defaults = {
        "package": "free",
    }

    def get_address_str(self, ids, context={}):
        obj = self.browse(ids[0])
        if not obj.addresses:
            return ""
        addr = obj.addresses[0]
        return addr.name_get()[0][1]

    def write(self, ids, vals, **kw):
        res = super().write(ids, vals, **kw)
        if "date_format" in vals or "use_buddhist_date" in vals:
            static.clear_translations()  # XXX: rename this

    def get_fiscal_year_end(self, date=None):
        if date:
            d0 = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        else:
            d0 = datetime.date.today()
        settings = self.browse(1)
        if not settings.year_end_month or not settings.year_end_day:
            raise Exception("Missing fiscal year end")
        month = int(settings.year_end_month)
        day = int(settings.year_end_day)
        d = datetime.date(d0.year, month, day)
        if d < d0:
            d += relativedelta(years=1)
        return d.strftime("%Y-%m-%d")

    def get_fiscal_year_start(self, date=None):
        d1 = self.get_fiscal_year_end(date)
        d = datetime.datetime.strptime(d1, "%Y-%m-%d") - relativedelta(years=1) + datetime.timedelta(days=1)
        return d.strftime("%Y-%m-%d")

    def get_default_address(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = obj.addresses and obj.addresses[0].id or None
        return vals

    def get_addresses(self,ids,context={}):
        vals={}
        comp_id=access.get_active_company()
        for obj in self.browse(ids):
            res=get_model("address").search([["settings_id","=",obj.id],["or",["company_id","=",None],["company_id","child_of",comp_id]]])
            vals[obj.id]=res
        return vals

    def get_commission_remain(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=100-(obj.commission_parent or 0)-(obj.commission_grand_parent or 0)
        return vals

    def get_z_percentage(self,ids,context={}): 
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id]=100-(obj.x_by_percentage or 0)-(obj.y_by_percentage or 0)
        return vals

    def get_c_percentage(self,ids,context={}): 
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id]=100-(obj.a_by_percentage or 0)-(obj.b_by_percentage or 0)
        return vals

    def get_x_total_stockcount(self,ids,context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.z_total_stockcount_per_year or 0)*abs(obj.x2z_ratio or 0)
        return vals

    def get_y_total_stockcount(self,ids,context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.z_total_stockcount_per_year or 0)*abs(obj.y2z_ratio or 0)
        return vals

Settings.register()
