import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class Report(Model):
    _name="report.wht50"
    _transient=True
    _fields={
        "year": fields.Date("Year"),
        "doc_date": fields.Date("Document Date"),
        "employee_id": fields.Many2One("hr.employee","Employee"),
        "show_doc_date": fields.Boolean("Show Doc.Date"),
    }
    _defaults={
        "year": lambda *a: time.strftime("%Y-%m-%d"),
        "doc_date": lambda *a: time.strftime("%Y-%m-%d"),
        'show_doc_date': False,
    }

    def print_wht50(self,ids,context={}):
        obj=self.browse(ids)[0]
        employee_id=obj.employee_id and obj.employee_id.id or None
        return {
            "next": {
                "name": "report_wht50_pdf",
                "context": {
                    "year": obj.year,
                    "doc_date": obj.doc_date,
                    "employee_id": employee_id,
                    "show_doc_date": obj.show_doc_date,
                }
            }
        }

    def get_data(self,context={}):
        to_boolean=utils.to_boolean
        date2thai=utils.date2thai
        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        year=context.get("year")
        doc_date=context.get("doc_date")
        show_doc_date=to_boolean(context.get("show_doc_date"))
        employee_id=context.get("employee_id")
        if not year:
            year=time.strftime("%Y-%m-%d")
        year=year[0:4]
        date_from=year+"-01-01"
        date_to=year+"-12-31"
        lines=[]
        emp_obj=None
        employee=get_model('hr.employee')
        if employee_id and employee_id!="None" and employee_id != 'null': # XXX
            emp_obj=employee.search_browse([['id','=',employee_id]])
        else:
            emp_obj=employee.search_browse([],order='id')
        document_date=['','','']
        if doc_date and show_doc_date:
            document_date=date2thai(doc_date,'%(d)s,%(Tm)s,%(BY)s').split(',')
        for emp in sorted(emp_obj, key=lambda x: x.code):
            emp_title = emp.title
            emp_title = emp_title.title()
            emp_name=' '.join(s for s in [(emp_title and emp_title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            name_th=emp.name_th or ''
            name_last_th = emp.name_last_th or ''
            if name_th or name_last_th:
                name_th= ' '.join(s for s in [(emp.name_th or ''),(emp.name_last_th or '')])
            line={
                'line_name': name_th or emp_name,
                'line_address': emp.report_address_txt,
                'line_pin': emp.tax_no,
                'line_base': 0,
                'line_tax': 0,
                'line_base_sum': 0,
                'line_tax_sum': 0,
                'line_sso_sum': 0,
                'line_prov_sum': 0,
                'line_tax_sum_word': '',
                'line_year': document_date[2],
                }
            for slip in get_model("hr.payslip").search_browse([['employee_id','=',emp.id],["date_from",">=",date_from],["date_to","<=",date_to]]):
                line["line_base"]+=slip.amount_wage+slip.amount_allow
                line["line_tax"]+=slip.amount_tax
                line["line_sso_sum"]+=slip.amount_social
                line["line_prov_sum"]+=slip.amount_provident

            line['line_base_sum']=line['line_base']
            line['line_tax_sum']=line['line_tax']
            line['line_tax_sum_word']=utils.num2word(line['line_tax_sum'])
            # only who have income
            #print("line",line)
            if line['line_base'] > 0:
                lines.append(line)

        settings=get_model("settings").browse(1)
        hr_settings=get_model("hr.payroll.settings").browse(1)
        data={
            "company_pin": settings.tax_no,
            "company_name": hr_settings.company or '',
            "company_address": hr_settings.get_address_text_thai() or '',
            "year": document_date[2],
            "document_date": document_date,
            'norecord': False if lines else True,
            "lines": lines,
        }

        return data

Report.register()
