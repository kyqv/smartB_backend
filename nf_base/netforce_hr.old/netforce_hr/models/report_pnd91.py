import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class Report(Model):
    _name="report.pnd91"
    _transient=True
    _fields={
        "year": fields.Date("Year"),
        "employee_id": fields.Many2One("hr.employee","Employee"),
    }
    _defaults={
        "year": lambda *a: time.strftime("%Y-%m-%d"),
    }
    
    def get_default_lines(self):
        # copy data structure from thai payroll
        return {'A1': 0,
            'A10': 0,
            'A11': 0,
            'A12': 0,
            'A2': 0,
            'A3': 0,
            'A4': 0,
            'A5': 0,
            'A6': 30000,
            'A7': 0,
            'A8': 0,
            'A9': 0,
            'B1': 0,
            'B2': 0,
            'B3': 0,
            'B4a': 0,
            'B4b': 0,
            'B5': 0,
            'B6': 0,
            'C1': 30000,
            'C10': 0,
            'C11': 0,
            'C12': 0,
            'C13': 0,
            'C14': 30000,
            'C2': 0,
            'C3a': 0,
            'C3a_persons': 0,
            'C3b': 0,
            'C3b_persons': 0,
            'C4a': 0,
            'C4b': 0,
            'C4c': 0,
            'C4d': 0,
            'C5': 0,
            'C6': 0,
            'C7a': 0,
            'C7b': 0,
            'C8': 0,
            'C9': 0,
            'birthdate': '',
            'id': 0,
            'name': '',
            'pin': '',
            'spouse_birthdate': '',
            'spouse_name': '',
            'spouse_pin': '',
            }

    def print_pnd91_cover(self,ids,context={}):
        obj=self.browse(ids)[0]
        employee_id=obj.employee_id and int(obj.employee_id.id) or None
        return {
            "next": {
                "name": "report_pnd91_cover_pdf",
                "context": {
                    "year": obj.year,
                    "employee_id": employee_id,
                },
            }
        }

    def print_pnd91_attach(self,ids,context={}):
        obj=self.browse(ids)[0]
        employee_id=obj.employee_id and int(obj.employee_id.id) or None
        return {
            "next": {
                "name": "report_pnd91_attach_pdf",
                "context": {
                    "year": obj.year,
                    "employee_id": employee_id,
                },
            }
        }

    def get_data_cover(self,context={}):
        lines=[]
        emp_ids=[]
        employee=get_model('hr.employee')
        date2thai=utils.date2thai
        if context.get('employee_id')!='null':
           emp_ids=[int(context.get('employee_id'))]
        else:
            emp_ids=employee.search([])

        choice={"spouse_status": {"married": "01", "married_new": "02","divorced": "03", "deceased": "04"},
                "marital_status": {"single": "01", "married": "02", "divorced": "03", "widowed": "04"},
                }

        for emp in employee.browse(emp_ids):
            emp_name=" ".join(s for s in [(emp.title and emp.title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            emp_last = (emp.last_name or '')
            name_th=emp.name_th or ''
            name_last_th = emp.name_last_th or ''
            if name_th:
                emp_name=name_th
            if name_last_th:
                emp_last = name_last_th
            spouse_name=" ".join(s for s in [(emp.spouse_title and emp.spouse_title+'.' or ''),(emp.spouse_first_name or ''),(emp.spouse_last_name or '')])
            #address=emp.addresses and emp.addresses[0] or None
            line={
                'pin': emp.tax_no,
                'name': emp_name,
                'last_name': emp_last,
                'birthdate': emp.birth_date and date2thai(emp.birth_date,format='%(d)s/%(m)s/%(BY)s') or '',
                'spouse_pin': emp.spouse_tax_no,
                'spouse_name': spouse_name,
                'spouse_birthdate': emp.spouse_birth_date and date2thai(emp.spouse_birth_date,format='%(d)s/%(m)s/%(BY)s') or '',
                'spouse_status': choice['spouse_status'][emp.spouse_status] if emp.spouse_status else '',
                'person_tax_status': choice['marital_status'][emp.marital_status] if emp.marital_status else '',
                'depart_room_number': emp.depart_room_number or '',
                'depart_stage': emp.depart_stage or '',
                'depart_village': emp.depart_village or '',
                'depart_name': emp.depart_name or '',
                'depart_number': emp.depart_number or '',
                'depart_sub_number': emp.depart_sub_number or '',
                'depart_soi': emp.depart_soi or '',
                'depart_road': emp.depart_road or '',
                'depart_district': emp.depart_district or '',
                'depart_sub_district': emp.depart_sub_district or '',
                'depart_province': emp.depart_province or '',
                'depart_zip': emp.depart_zip or '',
                'depart_tel': emp.depart_tel or '',
                'depart_phone': emp.depart_phone or '',
            }
            lines.append(line)
        document_date=date2thai(time.strftime("%Y-%m-%d"),'%(d)s,%(Tm)s,%(BY)s').split(',')
        data={
            "document_date": document_date,
            "year": document_date[2],
            'norecord': False if lines else True,
            "lines": lines,
        }
        return data

    def get_data_attach(self,context={}):
        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        lines=[]
        emp_ids=[]
        date2thai=utils.date2thai
        employee=get_model('hr.employee')
        settings=get_model("settings").browse(1)
        if context.get('employee_id')!='null':
           emp_ids=[int(context.get('employee_id'))]
        else:
            emp_ids=employee.search([])
        emps = employee.browse(emp_ids)
        for emp in sorted(emps, key=lambda x: x.code):
            context['employee_id']=emp.id
            context['year_date'] = context.get('year')
            tax=get_model("hr.payitem").compute_thai_tax(context=context)
            line=self.get_default_lines()
            line['pin']=settings.tax_no
            line['C4a_pin']=emp.tax_profile_id.father_id_no
            line['C4b_pin']=emp.tax_profile_id.mother_id_no
            line['C4c_pin']=emp.tax_profile_id.spouse_father_id_no
            line['C4d_pin']=emp.tax_profile_id.spouse_mother_id_no
            # update tax 
            for k,v in tax.items():
                if k == 'C3a':
                    line['C3a_persons'] = emp.num_child1
                elif k == 'C3b':
                    line['C3b_persons'] = emp.num_child2
                line[k]=v
            lines.append(line)
        document_date=date2thai(time.strftime("%Y-%m-%d"),'%(d)s,%(Tm)s,%(BY)s').split(',')
        company_name=''
        if len(settings.addresses)>0:
            addr=settings.addresses[0]
            company_name=addr.company
        data={
            "company": company_name or comp.name or '',
            "pin": settings.tax_no,
            "document_date": document_date,
            'norecord': False if lines else True,
            "year": document_date[2],
            "lines": lines,
        }
        return data

Report.register()
