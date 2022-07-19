import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company
from netforce.utils import get_data_path

class SsoRegist(Model):
    _name="sso.regist"
    _string="Sso Regist"
    _fields={
        "month": fields.Date("Month"),
        "doc_date": fields.Date("Document Date"),
        "show_doc_date": fields.Boolean("Show Doc.Date"),
        "lines": fields.One2Many("sso.regist.line","sso_regist_id","Lines"),
    }

    _defaults={
        "month": lambda *a: time.strftime("%Y-%m-%d"),
        "doc_date": lambda *a: time.strftime("%Y-%m-%d"),
        'show_doc_date': False,
    }

    def print_cover(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "sso_regist_cover_pdf",
                "context": {
                    'ref_id': obj.id,
                    "month": obj.month,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                },
            }
        }

    def print_attach(self,ids,context={}):
        obj=self.browse(ids)[0]
        return {
            "next": {
                "name": "sso_regist_pdf",
                "context": {
                    'ref_id': obj.id,
                    "month": obj.month,
                    "doc_date": obj.doc_date,
                    "show_doc_date": obj.show_doc_date,
                },
            }
        }

    #def create(self,vals,**kw):
        #print("create!!!!")
        #super().create(vals,**kw)

    def write(self,ids,vals,**kw):
        obj=self.browse(ids)[0]
        get_model('sso.regist.line').delete([line.id for line in obj.lines])
        super().write(ids,vals,**kw)

    def get_data(self,context={}):
        to_boolean=utils.to_boolean
        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        month=context.get("month")
        # option=context.get("option")
        doc_date=context.get("doc_date")
        show_doc_date=to_boolean(context.get("show_doc_date"))
        lines2=[]
        ref_id=int(context['ref_id'])
        no = 1
        obj=self.browse(ref_id)
        id_no={}
        for line in obj.lines:
            emp=line.employee_id
            print('--->', emp.first_name)
        # slips = self.get_payslip_line(month)
        # for slip in sorted(slips, key=lambda x: x.employee_id.code):
        #     emp=slip.employee_id
            emp_name=' '.join(s for s in [(emp.title and emp.title+'.' or ''),(emp.first_name or ''),(emp.last_name or '')])
            name_th=emp.name_th or ''
            name_last_th = emp.name_last_th or ''
            if name_th or name_last_th:
                name_th= ' '.join(s for s in [(emp.name_th or ''),(emp.name_last_th or '')])
            if not line.old_company:
                old_company = ""
            else:
                old_company = line.old_company

            if not line.other_old_company:
                other_old_company = ""
            else:
                other_old_company = line.other_old_company

            line={
                'no': no,
                'line_name': name_th or emp_name,
                'line_pin': line.id_no,
                'line_hire': line.hire_date,
                'old_company': old_company,
                'other_old_company': other_old_company,
            }
            #if not id_no.setdefault(emp.id_no,0):
                #import pdb;pdb.set_trace()
            lines2.append(line)
            no += 1
        #     amount_all = slip.amount_wage+slip.amount_allow_all
        #     for line_slip in slip.lines:
        #         if line_slip.payitem_id.type in ("wage","allow"):
        #             if line_slip.payitem_id.include_sso == True:
        #                 continue
        #             else:
        #                 amount_all -= line_slip.rate
        #     if not slip.amount_social:
        #         continue
        #java -jar netforce_report.jar 

        company_address=''
        company_zip=''
        company_phone=''
        company_fax=''
        setting=get_model('hr.payroll.settings').browse(1)
        if setting:
            company_sso=setting.social_number
            company_sso_perc=setting.social_rate
            company_number=setting.depart_number
            company_sub_number=setting.depart_sub_number
            company_soi=setting.depart_soi
            company_road=setting.depart_road
            company_sub_district=setting.depart_sub_district
            company_district=setting.depart_district
            company_province=setting.depart_province
            company_zip=setting.depart_zip
            company_name=setting.company
            company_phone=setting.depart_tel
            company_fax=setting.depart_fax



        document_date={'d': '','m': '','y': ''}
        if doc_date and show_doc_date:
            document_date=dict(zip(['d','m','y'],utils.date2thai(doc_date,'%(d)s,%(Tm)s,%(BY)s').split(',')))
        # if show_name and name_pay:
        #     name_of_pay = name_pay
        # else:
        #     name_of_pay = ""
        # if show_name and  position:
        #     positions = position
        # else:
        #     positions = ""
        month_year = dict(zip(['d','m','y'],utils.date2thai(month,'%(d)s,%(Tm)s,%(BY)s').split(',')))
        period_month=month_year['m']
        period_year=month_year['y']
        document_date=[document_date['d'],document_date['m'],document_date['y']]
        data={
            'period_month': period_month,
            'period_year': period_year,
            # 'company_address': setting.get_address_text_thai(),
            'company_fax': company_fax,
            'company_name': company_name,
            'company_phone': company_phone,
            'company_sso': company_sso,
            'company_sso_perc': company_sso_perc,
            'company_number': company_number,
            'company_sub_number': company_sub_number,
            'company_soi': company_soi,
            'company_road': company_road,
            'company_sub_district': company_sub_district,
            'company_district': company_district,
            'company_province': company_province,
            'company_zip': company_zip,
            'document_date': document_date,
            # "name_pay": name_of_pay,
            # "position": positions,
            # 'norecord': False if lines else True,
            # 'sum_base': sum_base,
            # 'sum_deduction': sum_deduction,
            # 'sum_comp_contrib': sum_comp_contrib,
            # 'sum_total': sum_total,
            # 'sum_total_word': utils.num2word(sum_total),
            # 'send_to': option,
            "lines": lines2,
        }
        return data

    def onchange_month(self,context={}):
        data=context['data']
        month = data['month'][5:7]
        year = data['month'][0:4]
        employee = get_model("hr.employee")
        emps = employee.search_browse([],order='id')
        lines=[]
        for emp in emps:
            print(emp.hire_date)
            emp_month = emp.hire_date[5:7]
            emp_year = emp.hire_date[0:4]
            if emp_year == year and emp_month == month:
                vals={
                    "employee_id": emp.id,
                    "id_no": emp.id_no,
                    "hire_date": emp.hire_date,
                }
                lines.append(vals)
        # from pprint import pprint     
        # pprint(lines)
        data['lines']=lines
        #for line in lines:
            ## print(emps.hire_date)
            ## emp_month = emps.hire_date[5:7]
            ## emp_year = emps.hire_date[0:4]
            ## if emp_year == year and emp_month == month:
                ## for line in lines:
                #line['employee_id'] = lists[""]
                #line['id_no'] = emps.id_no
                #line['hire_date'] = emps.hire_date
        #print(month)
        return data
    
    def onchange_employee(self,context={}):
        data=context['data']
        path=context["path"]
        line=get_data_path(data,path,parent=True)
        emp_id = line["employee_id"]
        emp = get_model("hr.employee").browse(emp_id)
        line["id_no"] = emp.id_no
        line["hire_date"] = emp.hire_date
        return data

SsoRegist.register()
