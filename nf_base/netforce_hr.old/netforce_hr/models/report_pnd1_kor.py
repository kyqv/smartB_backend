import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class Report(Model):
    _name="report.pnd1.kor"
    _transient=True
    _fields={
        "year": fields.Date("Year"),
        "doc_date": fields.Date("Document Date"),
        "show_doc_date": fields.Boolean("Show Doc.Date"),
        "name_pay": fields.Char("Name"),
        "position": fields.Char("Position"),
        "show_name": fields.Boolean("Show name and position"),
    }
    _defaults={
        "year": lambda *a: time.strftime("%Y-%m-%d"),
        "doc_date": lambda *a: time.strftime("%Y-%m-%d"),
        'show_doc_date': False,
        'show_name': False,
    }

    def print_cover(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "report_pnd1_kor_cover_pdf",
                "context": {
                    "year": obj.year,
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
                "name": "report_pnd1_kor_attach_pdf",
                "context": {
                    "year": obj.year,
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
                "name": "report_pnd1_kor_xls",
                "context": {
                    "year": obj.year,
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
        date2thai=utils.date2thai
        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        year=context.get("year")
        doc_date=context.get("doc_date")
        show_doc_date=to_boolean(context.get("show_doc_date"))
        name_pay = context.get("name_pay")
        position = context.get("position")
        show_name = to_boolean(context.get("show_name"))
        if not year:
            year=time.strftime("%Y-%m-%d")
        year=year[0:4]
        date_from=year+"-01-01"
        date_to=year+"-12-31"
        lines=[]
        employee=get_model('hr.employee')
        no = 1
        total_base = 0
        total_tax = 0
        #states=['state','in',['approved','paid','posted']]
        emps = employee.search_browse([],order='id')
        for emp in sorted(emps, key=lambda x: x.code):
            emp_title = emp.title
            emp_title = emp_title.title()
            emp_name=' '.join(s for s in [(emp_title and emp_title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            name_th=emp.name_th or ''
            name_last_th = emp.name_last_th or ''
            if name_th or name_last_th:
                name_th= ' '.join(s for s in [(emp.name_th or ''),(emp.name_last_th or '')])
            line={
                'no': no,
                'line_name': name_th or emp_name,
                'line_base':0,
                'line_tax':0,
                'line_address': emp.report_address_txt,
                'line_cond': '1',
                'line_pin': emp.tax_no,
                'line_wht_item': '01',
                }
            for slip in get_model("hr.payslip").search_browse([['employee_id','=',emp.id],["date_from",">=",date_from],["date_to","<=",date_to]]):
                line["line_base"]+=slip.amount_wage+slip.amount_allow_all
                line["line_tax"]+=slip.amount_tax
            # only who have income
            total_base += line["line_base"]
            total_tax += line["line_tax"]
            if line['line_base'] > 0:
                lines.append(line)
            no += 1
        document_date=['','','']
        show_year=['','','']
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
        show_year = date2thai(date_from,'%(d)s,%(Tm)s,%(BY)s').split(',')
        tax_id = get_model("settings").browse(1)
        settings=get_model("hr.payroll.settings").browse(1)
        data={
            "pin": tax_id.tax_no,
            "company": settings.company,
            "year": show_year[2],
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
            'norecord': False,
            "lines": lines,
        }
        return data

Report.register()
