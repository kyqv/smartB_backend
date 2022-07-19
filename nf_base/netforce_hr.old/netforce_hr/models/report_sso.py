import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class Report(Model):
    _name="report.sso"
    _transient=True
    _fields={
        "month": fields.Date("Month"),
        "doc_date": fields.Date("Document Date"),
        "show_doc_date": fields.Boolean("Show Doc.Date"),
        "option": fields.Selection([["01","Detail of sending to the contribution"],["02","Disk"],["03","Internet"],["04","Others"]],"Cover Sending"),
        "name_pay": fields.Char("Name"),
        "position": fields.Char("Position"),
        "show_name": fields.Boolean("Show name and position"),
    }
    _defaults={
        "option": "01",
        "month": lambda *a: time.strftime("%Y-%m-%d"),
        "doc_date": lambda *a: time.strftime("%Y-%m-%d"),
        'show_doc_date': False,
        'show_name': False,
    }

    def get_payslip_line(self,month):
        if not month:
            month=time.strftime("%Y-%m-%d")
        last_date=utils.get_last_day(month)
        date_from=month[0:8]+"01"
        date_to=month[0:8]+str(last_date)
        #states=['state','in',['approved','paid','posted']]
        payslip_line=get_model("hr.payslip").search_browse([["date_from",">=",date_from],["date_to","<=",date_to]])

        if len(payslip_line) < 1:
            raise Exception("No data available")

        return payslip_line

    def print_cover(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "report_sso_cover_pdf",
                "context": {
                    "month": obj.month,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                    "option": obj.option,
                    "name_pay": obj.name_pay,
                    "position": obj.position,
                    "show_name": obj.show_name,
                },
            }
        }

    def print_attach(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "report_sso_attach_pdf",
                "context": {
                    "month": obj.month,
                    "option": obj.option,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                    "name_pay": obj.name_pay,
                    "position": obj.position,
                    "show_name": obj.show_name,
                },
            }
        }

    def print_xls(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "report_sso_xls",
                "context": {
                    "month": obj.month,
                    "option": obj.option,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                    "name_pay": obj.name_pay,
                    "position": obj.position,
                    "show_name": obj.show_name,
                },
            }
        }

    def get_data(self,context={}):
        to_boolean=utils.to_boolean
        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        month=context.get("month")
        option=context.get("option")
        doc_date=context.get("doc_date")
        show_doc_date=to_boolean(context.get("show_doc_date"))
        name_pay = context.get("name_pay")
        position = context.get("position")
        show_name = to_boolean(context.get("show_name"))
        lines=[]
        no = 1
        slips = self.get_payslip_line(month)
        for slip in sorted(slips, key=lambda x: x.employee_id.code):
            emp=slip.employee_id
            emp_name=' '.join(s for s in [(emp.title and emp.title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            name_th=emp.name_th or ''
            name_last_th = emp.name_last_th or ''
            if name_th or name_last_th:
                name_th= ' '.join(s for s in [(emp.name_th or ''),(emp.name_last_th or '')])
            amount_all = slip.amount_wage+slip.amount_allow_all
            for line_slip in slip.lines:
                if line_slip.payitem_id.type in ("wage","allow"):
                    if line_slip.payitem_id.include_sso == True:
                        continue
                    else:
                        amount_all -= (line_slip.rate*line_slip.qty)
            if not slip.amount_social:
                continue
            line={
                'no': no,
                "line_base": amount_all,
                'line_deduction': slip.amount_social,
                'line_name': name_th or emp_name,
                'line_pin': emp.tax_no,
            }
            lines.append(line)
            no += 1

        company_address=''
        company_zip=''
        company_phone=''
        company_fax=''
        setting=get_model('hr.payroll.settings').browse(1)
        if setting:
            company_sso=setting.social_number
            company_sso_perc=setting.social_rate
            company_zip=setting.depart_zip
            company_name=setting.company
            company_phone=setting.depart_tel
            company_fax=setting.depart_fax


        document_date={'d': '','m': '','y': ''}
        if doc_date and show_doc_date:
            document_date=dict(zip(['d','m','y'],utils.date2thai(doc_date,'%(d)s,%(Tm)s,%(BY)s').split(',')))
        if show_name and name_pay:
            name_of_pay = name_pay
        else:
            name_of_pay = ""
        if show_name and  position:
            positions = position
        else:
            positions = ""
        month_year = dict(zip(['d','m','y'],utils.date2thai(month,'%(d)s,%(Tm)s,%(BY)s').split(',')))
        period_month=month_year['m']
        period_year=month_year['y']
        document_date=[document_date['d'],document_date['m'],document_date['y']]

        sum_base=0
        sum_deduction=0
        sum_comp_contrib=0
        for line in lines:
            sum_base+=line['line_base'] 
            sum_deduction+=line['line_deduction'] 
            sum_comp_contrib+=line['line_deduction'] 
        sum_total=sum_deduction+sum_comp_contrib
        data={
            'period_month': period_month,
            'period_year': period_year,
            'company_address': setting.get_address_text_thai(),
            'company_fax': company_fax,
            'company_name': company_name,
            'company_phone': company_phone,
            'company_sso': company_sso,
            'company_sso_perc': company_sso_perc,
            'company_zip': company_zip,
            'document_date': document_date,
            "name_pay": name_of_pay,
            "position": positions,
            'norecord': False if lines else True,
            'sum_base': sum_base,
            'sum_deduction': sum_deduction,
            'sum_comp_contrib': sum_comp_contrib,
            'sum_total': sum_total,
            'sum_total_word': utils.num2word(sum_total),
            'send_to': option,
            "lines": lines,
        }
        return data


Report.register()
