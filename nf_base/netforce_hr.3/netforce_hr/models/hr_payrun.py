from netforce.model import Model, fields, get_model
from netforce import access
from netforce import utils
from netforce.access import get_active_company
from netforce.utils import get_file_path
from datetime import *
from dateutil.relativedelta import *
from calendar import monthrange


class PayRun(Model):
    _name="hr.payrun"
    _string="Pay Run"
    _name_field="number"
    _multi_company=True

    _fields={
        "number": fields.Char("Number",required=True,search=True),
        "date_from": fields.Date("From Date",required=True),
        "date_to": fields.Date("To Date",required=True),
        "date_pay": fields.Date("Pay Date",search=True),
        "num_employees": fields.Integer("Employees",function="get_total",function_multi=True),
        "amount_total": fields.Decimal("Total",function="get_total",function_multi=True),
        "payslips": fields.One2Many("hr.payslip","run_id","Payslips"),
        "company_id": fields.Many2One("company","Company"),
        "state": fields.Selection([["draft","Draft"],["approved","Approved"],['paid','Paid'],['posted','Posted']],"Status",required=True),
        "journal_entries": fields.One2Many("account.move","related_id","Journal Entries"),
        "payments": fields.One2Many("account.payment","related_id","Payments"),
    }

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="payrun",context=context)
        if not seq_id:
            return
        count=0
        while 1:
            count+=1
            if count>10:
                return None
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if not num:
                return None
            user_id = access.get_active_user()
            access.set_active_user(1)
            res = self.search([["number", "=", num]])
            access.set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)
    
    _defaults={
        "number": _get_number,
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "date_pay": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
        'state': 'draft',
    }

    _order="date_from desc"

    def get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            num_emp=0
            amt_tot=0
            for slip in obj.payslips:
                num_emp+=1
                amt_tot+=slip.amount_net
            vals[obj.id]={
                "num_employees": num_emp,
                "amount_total": amt_tot,
            }
        return vals

    def gen_payslips(self,ids,context={}):
        print("gen_payslips",ids)
        obj=self.browse(ids[0])
        if obj.state!="draft":
            raise Exception("Invalid status")
        for emp in get_model("hr.employee").search_browse([["work_status","=","working"]]):
            slip_vals={
                "run_id": obj.id,
                "employee_id": emp.id,
                "lines": [],
            }
            if emp.salary:
                res=get_model("hr.payitem").search([["type","=","salary"]])
                if not res:
                    raise Exception("Salary pay item not found")
                item_id=res[0] # XXX
                line_vals={
                    "payitem_id": item_id,
                    "amount": emp.salary,
                }
                slip_vals["lines"].append(("create",line_vals))
            if emp.sellers:
                amt=0
                for seller in emp.sellers:
                    amt+=seller.calc_commission(date_from=obj.date_from,date_to=obj.date_to)
                res=get_model("hr.payitem").search([["type","=","commission"]])
                if not res:
                    raise Exception("Commission pay item not found")
                item_id=res[0] # XXX
                line_vals={
                    "payitem_id": item_id,
                    "amount": amt,
                }
                slip_vals["lines"].append(("create",line_vals))
            res=emp.calc_overtime(date_from=obj.date_from,date_to=obj.date_to)
            for rate,qty in res.items(): 
                res=get_model("hr.payitem").search([["type","=","overtime"]])
                if not res:
                    raise Exception("Other expenses pay item not found")
                item_id=res[0] # XXX
                line_vals={
                    "payitem_id": item_id,
                    "qty": qty,
                    "rate": rate,
                    "amount": qty*rate,
                }
                slip_vals["lines"].append(("create",line_vals))
            get_model("hr.payslip").create(slip_vals)

    def approve(self,ids,context={}):
        obj=self.browse(ids[0])
        settings=get_model("hr.payroll.settings").browse(1)
        for slip in obj.payslips:
            emp=slip.employee_id
            name="%s %s"%(emp.first_name,emp.last_name)
            if not settings.journal_id:
                raise Exception("Missing payroll journal")
            move_vals={
                "journal_id": settings.journal_id.id,
                "date": obj.date_pay or obj.date_from,
                "lines": [],
                "narration": "Payroll %s - %s"%(obj.number,name),
                "related_id": "hr.payrun,%s"%obj.id,
            }
            if not settings.payroll_payable_id:
                raise Exception("Missing payroll payable account")
            line_vals={
                "description": move_vals["narration"],
                "debit": 0,
                "credit": slip.amount_net,
                "account_id": settings.payroll_payable_id.id,
                "due_date": obj.date_pay,
            }
            move_vals["lines"].append(("create",line_vals))
            for line in slip.lines:
                if not line.payitem_id.account_id:
                    raise Exception("Missing account in pay item '%s'"%line.payitem_id.name)
                amt=line.amount
                line_vals={
                    "description": line.payitem_id.name,
                    "debit": amt if amt>0 else 0,
                    "credit": -amt if amt<0 else 0,
                    "account_id": line.payitem_id.account_id.id,
                }
                move_vals["lines"].append(("create",line_vals))
            move_id=get_model("account.move").create(move_vals)
            get_model("account.move").post([move_id])
        obj.write({"state":"approved"})

    def to_draft(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.journal_entries.to_draft()
        obj.journal_entries.delete()
        obj.write({"state":"draft"})

    def copy_to_payment(self,ids,context={}):
        obj=self.browse(ids[0])
        settings=get_model("hr.payroll.settings").browse(1)
        pmt_vals={
            "type": "out",
            "pay_type": "direct",
            "memo": "Payroll %s"%obj.number,
            "related_id": "hr.payrun,%s"%obj.id,
            "lines": [],
        }
        if not settings.payroll_payable_id:
            raise Exception("Missing payroll payable account")
        line_vals={
            "type": "direct",
            "account_id": settings.payroll_payable_id.id,
            "amount": obj.amount_total,
        }
        pmt_vals["lines"].append(("create",line_vals))
        ctx={
            "type": "out",
            "pay_type": "direct",
        }
        pmt_id=get_model("account.payment").create(pmt_vals,context=ctx)
        return {
            "next": {
                "name": "payment",
                "mode": "form",
                "active_id": pmt_id,
            }
        }

PayRun.register()
