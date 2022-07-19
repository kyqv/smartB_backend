import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class Report(Model):
    _name="report.provident"
    _transient=True
    _fields={
        "month": fields.Date("Month"),
        "doc_date": fields.Date("Document Date"),
        "show_doc_date": fields.Boolean("Show Doc.Date"),
    }
    _defaults={
        "month": lambda *a: time.strftime("%Y-%m-%d"),
        "doc_date": lambda *a: time.strftime("%Y-%m-%d"),
        'show_doc_date': False,
    }

    def get_payslip_line(self,month):
        if not month:
            month=time.strftime("%Y-%m-%d")
        last_day=utils.get_last_day(month)
        date_from=month[0:8]+"01"
        date_to=month[0:8]+str(last_day)
        payslip_line=get_model("hr.payslip").search_browse([["date_from",">=",date_from],["date_to","<=",date_to]])
        has_prov=0
        for slip in payslip_line:
            if slip.amount_provident >= 0:
                has_prov+=1

        print (payslip_line)
        print (has_prov)

        if len(payslip_line) < 1 or has_prov < 1:
            raise Exception("No data available")

        return payslip_line

    def print_provident(self,ids,context={}):
        obj=self.browse(ids)[0]
        payslip_line=self.get_payslip_line(obj.month)

        return {
            "next": {
                "name": "report_provident_pdf",
                "context": {
                    "month": obj.month,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                },
            }
        }

    def print_xls(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "report_provident_xls",
                "context": {
                    "month": obj.month,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                },
            }
        }

    def get_data(self,context={}):
        to_boolean=utils.to_boolean
        date2thai=utils.date2thai
        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        month=context.get("month")
        doc_date=context.get("doc_date")
        show_doc_date=to_boolean(context.get("show_doc_date"))
        lines=[]
        employee_amt_total = 0
        employer_amt_total = 0
        total_amt = 0
        no=1
        slips = self.get_payslip_line(month)
        for slip in sorted(slips, key=lambda x: x.employee_id.code):
            #if slip.amount_provident < -1:
                #continue
            emp=slip.employee_id
            #if not emp.prov_fund_no:
                #continue
            if not emp.prov_regis:
                continue
            emp_title = emp.title
            emp_title = emp_title.title()
            emp_name=' '.join(s for s in [(emp_title and emp_title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            line={
                'no': no,
                'tran_code': '',
                'employee_code': emp.code,
                'prov_code': emp.prov_fund_no,
                'employee_name': emp_name,
                'id_code': emp.id_no,
                'tax_id': emp.tax_no,
                'date_cal_year': '',
                'start_work_date': emp.hire_date and emp.hire_date.replace("-","/") or '',
                'open_ac_date': emp.prov_open_date and emp.prov_open_date.replace("-","/") or '',
                'salary': emp.salary,
                'num_of_restdays': 0,
                'employee_rate': emp.prov_rate_employee,
                'employee_amt': slip.amount_provident,
                'employer_rate': emp.prov_rate_employer,
                'employer_amt': slip.amount_provident,
                'total': slip.amount_provident + slip.amount_provident,
            }
            no+=1
            lines.append(line)
            employee_amt_total += line["employee_amt"]
            employer_amt_total += line["employer_amt"]
            total_amt += line["total"]
        #settings=get_model("settings").browse(1)
        document_date = ""
        setting=get_model("hr.payroll.settings").browse(1)
        if doc_date and show_doc_date:
            document_date=date2thai(doc_date,'%(d)s/%(m)s/%(BY)s')
        #document_date=utils.date2thai(time.strftime("%Y-%m-%d"),'%(d)s/%(m)s/%(BY)s')
        doc_month = dict(zip(['d','m','y'],utils.date2thai(month,'%(d)s,%(Tm)s,%(BY)s').split(',')))
        month_doc = doc_month['m']
        company_name=''
        settings=get_model("settings").browse(1)
        if len(settings.addresses)>0:
            addr=settings.addresses[0]
            company_name=addr.company
        data={
            'month': month_doc,
            'company_name': company_name or comp.name or '',
            'document_date': document_date,
            'fund_name': setting.prov_name,
            'employee_amt_total': employee_amt_total,
            'employer_amt_total': employer_amt_total,
            'total_amt': total_amt,
            'lines': lines,
            'norecord': False if lines else True,
        }
        return data

Report.register()
