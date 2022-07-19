import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class Report(Model):
    _name="report.pnd1"
    _transient=True
    _fields={
        "month": fields.Date("Month"),
        "doc_date": fields.Date("Document Date"),
        "show_doc_date": fields.Boolean("Show Doc.Date"),
        "name_pay": fields.Char("Name"),
        "position": fields.Char("Position"),
        "show_name": fields.Boolean("Show name and position"),
    }
    _defaults={
        "month": lambda *a: time.strftime("%Y-%m-%d"),
        "doc_date": lambda *a: time.strftime("%Y-%m-%d"),
        'show_doc_date': False,
        'show_name': False,
    }

    def get_payslip_line(self,month):
        if not month:
            month=time.strftime("%Y-%m-%d")
        last_day=utils.get_last_day(month)
        date_from=month[0:8]+"01"
        date_to=month[0:8]+str(last_day)
        payslip_line=get_model("hr.payslip").search_browse([["date_from",">=",date_from],["date_to","<=",date_to]])

        if len(payslip_line) < 1:
            raise Exception("No data available")

        return payslip_line

    def print_cover(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "report_pnd1_cover_pdf",
                "context": {
                    "month": obj.month,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
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
                "name": "report_pnd1_attach_pdf",
                "context": {
                    "month": obj.month,
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
                "name": "report_pnd1_xls",
                "context": {
                    "month": obj.month,
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
        doc_date=context.get("doc_date")
        show_doc_date=to_boolean(context.get("show_doc_date"))
        name_pay = context.get("name_pay")
        position = context.get("position")
        show_name = to_boolean(context.get("show_name"))
        date2thai=utils.date2thai
        wht_items=[
            ('01', '40 (1) in general cases'),
            ('03', '40 (1) (2) termination of employment'),
            ('04', '40 (2) resident of Thailand'),
            ('05', '40 (2) non-resident of Thailand'),
            ]

        lines=[]
        slips = self.get_payslip_line(month)
        no = 1
        total_base = 0
        total_tax = 0
        for slip in sorted(slips, key=lambda x: x.employee_id.code):
            emp=slip.employee_id
            emp_title = emp.title
            #emp_title = emp_title.title()
            emp_name=' '.join(s for s in [(emp_title and emp_title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            name_th=emp.name_th or ''
            name_last_th = emp.name_last_th or ''
            if name_th or name_last_th:
                name_th= ' '.join(s for s in [(emp.name_th or ''),(emp.name_last_th or '')])
            amount_all = slip.amount_wage+slip.amount_allow_all
            for line_slip in slip.lines:
                if line_slip.payitem_id.type in ("wage","allow"):
                    if line_slip.payitem_id.include_pnd1 == True:
                        continue
                    else:
                        amount_all -= line_slip.rate
            if not emp.tax_no:
                raise Exception("Missing tax payer ID no. for employee %s %s"%(emp.first_name,emp.last_name))
            line={
                "no": no,
                "line_name": name_th or emp_name,
                "line_pin": emp.tax_no,
                "line_date": slip.due_date and date2thai(slip.due_date,format='%(d)s/%(m)s/%(BY)s') or '',
                "line_base": amount_all,
                "line_tax": slip.amount_tax,
                "line_wht_item": wht_items[0][0],
                "line_cond": "1",
            }
            total_base += amount_all
            total_tax += slip.amount_tax
            # only who have income
            if line['line_base'] > 0:
                lines.append(line)
            no += 1
        document_date=['','','']
        if doc_date and show_doc_date:
            document_date=date2thai(doc_date,'%(d)s,%(Tm)s,%(BY)s').split(',')
        if show_name and name_pay:
            name_of_pay = name_pay
        else:
            name_of_pay = ""
        if show_name and  position:
            positions = position
        else:
            positions = ""
        month_year = dict(zip(['d','m','y'],utils.date2thai(month,'%(d)s,%(Tm)s,%(BY)s').split(',')))
        settings=get_model("hr.payroll.settings").browse(1)
        tax_id = get_model("settings").browse(1)
        data={
            "pin": tax_id.tax_no,
            "period": int(month[5:7]),
            'company': settings.company,
            "year": month_year['y'],
            "document_date": document_date,
            "name_pay": name_of_pay,
            "position": positions,
            "total_base": total_base,
            "total_tax": total_tax,
            'depart_room_number': settings.depart_room_number or '',
            'depart_stage': settings.depart_stage or '',
            'depart_village': settings.depart_village or '',
            'depart_name': settings.depart_name or '',
            'depart_number': settings.depart_number or '',
            'depart_sub_number': settings.depart_sub_number or '',
            'depart_soi': settings.depart_soi or '',
            'depart_road': settings.depart_road or '',
            'depart_district': settings.depart_district or '',
            'depart_sub_district': settings.depart_sub_district or '',
            'depart_province': settings.depart_province or '',
            'depart_zip': settings.depart_zip or '',
            'depart_tel': settings.depart_tel or '',
            'depart_phone': settings.depart_phone or '',
            "lines": lines,
            'norecord': False if lines else True,
        }

        return data

Report.register()
