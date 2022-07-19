from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
import time
from netforce.access import get_active_user, get_active_company

class ExpenseClaim(Model):
    _name="expense.claim"
    _string="Expense Claim"
    _multi_company=True
    _name_field="number"
    _fields={
        "contact_id": fields.Many2One("contact","Supplier",search=True), # XXX: deprecated
        "number": fields.Char("Number",search=True,required=True),
        "name": fields.Char("Expense Claim Name"),
        "date_from": fields.Date("From Date",search=True),
        "date_to": fields.Date("To Date",search=True),
        "ref": fields.Char("Reference",search=True),
        "employee_id": fields.Many2One("hr.employee","Employee",required=True,search=True),
        "currency_id": fields.Many2One("currency","Currency",required=True),
        "tax_type": fields.Selection([["tax_ex","Tax Exclusive"],["tax_in","Tax Inclusive"],["no_tax","No Tax"]],"Tax Type",required=True),
        "related_id": fields.Reference([["project","Project"],["job","Service Order"]],"Related To"),
        "amount_total": fields.Decimal("Total Expense Amount",function="get_amount",function_multi=True),
        "state": fields.Selection([["draft","Draft"],["waiting_approval","Waiting Approval"],["approved","Approved"],["paid","Paid"],["declined","Declined"]],"Status",required=True,function="get_state",store=True),
        "documents": fields.One2Many("document","related_id","Documents"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "company_id": fields.Many2One("company","Company"),
        "move_id": fields.Many2One("account.move","Journal Entry"),
        "payment_lines": fields.One2Many("account.payment.line","expense_id","Payments"),
        "project_id": fields.Many2One("project","Project"),
        "cash_advance": fields.Decimal("Cash Advance"),
        "cash_remain": fields.Decimal("Cash Remaining",function="get_cash_remain"),
        "expenses": fields.One2Many("expense","claim_id","Expenses"),
        "description": fields.Text("Description"),
        "num_expenses": fields.Integer("Number Of Expenses",function="get_num_expenses"),
        "account_id": fields.Many2One("account.account","Account", search=True),
    }
    _order="id desc"

    def _get_number(self,context={}):
        seq_id=get_model("sequence").find_sequence(type="expense")
        if not seq_id:
            return None
        while 1:
            num=get_model("sequence").get_next_number(seq_id,context=context)
            res=self.search([["number","=",num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id,context=context)

    def _get_employee(self,context={}):
        user_id=get_active_user()
        res=get_model("hr.employee").search([["user_id","=",user_id]])
        if not res:
            return None
        return res[0]

    def _get_currency(self,context={}):
        settings=get_model("settings").browse(1)
        return settings.currency_id.id

    _defaults={
        "number": _get_number,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "employee_id": _get_employee,
        "currency_id": _get_currency,
        "tax_type": "tax_in",
        "state": "draft",
        "company_id": lambda *a: get_active_company(),
    }

    def get_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for exp in obj.expenses:
                amt+=exp.amount
            vals[obj.id]={
                "amount_total": amt,
            }
        return vals

    def get_num_expenses(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.expenses)
        return vals

    def update_amounts(self,context):
        data=context["data"]
        data["amount_subtotal"]=0
        data["amount_tax"]=0
        tax_type=data["tax_type"]
        for line in data["lines"]:
            if not line:
                continue
            amt=line.get("qty",0)*line.get("unit_price",0)
            line["amount"]=amt
            tax_id=line.get("tax_id")
            if tax_id:
                tax=get_model("account.tax.rate").compute_tax(tax_id,amt,tax_type=tax_type)
                data["amount_tax"]+=tax
            else:
                tax=0
            if tax_type=="tax_in":
                data["amount_subtotal"]+=amt-tax
            else:
                data["amount_subtotal"]+=amt
        data["amount_total"]=data["amount_subtotal"]+data["amount_tax"]
        return data

    def do_submit(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"waiting_approval"})

    def do_to_draft(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.move_id:
                obj.move_id.void()
                obj.move_id.delete()
            obj.write({"state":"draft"})

    def do_approve(self,ids,context={}):
        settings=get_model("settings").browse(1)
        for obj in self.browse(ids):
            if not obj.expenses:
                raise Exception("Expense claim is empty")
            journal_id=settings.purchase_journal_id.id
            if not journal_id:
                raise Exception("Purchases journal not found")
            desc="Expense claim %s"%obj.number
            move_vals={
                "journal_id": journal_id,
                "number": obj.number,
                "date": obj.date,
                "ref": obj.ref,
                "narration": desc,
                "related_id": "expense.claim,%s"%obj.id,
                "company_id": obj.company_id.id,
            }
            lines=[]
            taxes={}
            for exp in obj.expenses:
                cur_amt=get_model("currency").convert(exp.amount,obj.currency_id.id,settings.currency_id.id,date=obj.date,rate_type="buy")
                tax_id=exp.tax_id
                if tax_id and obj.tax_type!="no_tax":
                    base_amt=get_model("account.tax.rate").compute_base(tax_id,cur_amt,tax_type=obj.tax_type)
                    tax_comps=get_model("account.tax.rate").compute_taxes(tax_id,base_amt,when="invoice")
                    for comp_id,tax_amt in tax_comps.items():
                        tax_vals=taxes.setdefault(comp_id,{"tax_amt":0,"base_amt":0})
                        tax_vals["tax_amt"]+=tax_amt
                        tax_vals["base_amt"]+=base_amt
                else:
                    base_amt=cur_amt
                acc_id=exp.account_id.id
                if not acc_id:
                    raise Exception("Missing line account")
                line_vals={
                    "description": exp.description,
                    "account_id": acc_id,
                    "debit": base_amt,
                    "credit": 0,
                    "track_id": exp.track_id.id,
                    "track2_id": exp.track2_id.id,
                }
                lines.append(line_vals)
            for comp_id,tax_vals in taxes.items():
                comp=get_model("account.tax.component").browse(comp_id)
                acc_id=comp.account_id.id
                if not acc_id:
                    raise Exception("Missing account for tax component %s"%comp.name)
                line_vals={
                    "description": desc,
                    "account_id": acc_id,
                    "debit": tax_vals["tax_amt"],
                    "credit":  0,
                    "tax_comp_id": comp_id,
                    "tax_base": tax_vals["base_amt"],
                    "contact_id": obj.contact_id.id,
                }
                if comp.type=="vat":
                    line_vals["tax_no"]=obj.tax_no
                lines.append(line_vals)
            amt=0
            for line in lines:
                amt-=line["debit"]-line["credit"]
            if not obj.account_id:
                raise Exception("Missing payment account")
            line_vals={
                "description": desc,
                "account_id": obj.account_id.id,
                "debit": amt>0 and amt or 0,
                "credit": amt<0 and -amt or 0,
                "due_date": obj.due_date,
                "contact_id": obj.contact_id.id,
            }
            move_vals["lines"]=[("create",line_vals)]
            move_vals["lines"]+=[("create",vals) for vals in lines]
            move_id=get_model("account.move").create(move_vals)
            get_model("account.move").post([move_id])
            obj.write({"move_id":move_id,"state":"approved"})

    def do_decline(self,ids,context={}):
        claim_id=None
        for obj in self.browse(ids):
            obj.write({"state": "declined"})
            claim_id=obj.claim_id.id
        return {
            "next": {
                "name": "claim_edit",
                "active_id": claim_id,
            }
        }

    def onchange_account(self,context):
        data=context["data"]
        path=context["path"]
        line=get_data_path(data,path,parent=True)
        acc_id=line.get("account_id")
        if not acc_id:
            return {}
        acc=get_model("account.account").browse(acc_id)
        line["tax_id"]=acc.tax_id.id
        data=self.update_amounts(context)
        return data

    def view_journal_entry(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.move_id.id,
            }
        }

    def get_state(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            state=obj.state
            if state=="approved":
                if obj.amount_due==0:
                    state="paid"
            elif state=="paid":
                if obj.amount_due>0:
                    state="approved"
            vals[obj.id]=state
        return vals

    def get_cash_remain(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.cash_advance or 0)-obj.amount_total
        return vals

ExpenseClaim.register()
