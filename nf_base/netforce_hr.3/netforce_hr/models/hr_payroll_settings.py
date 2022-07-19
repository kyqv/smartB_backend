from netforce.model import Model, fields, get_model

class Settings(Model):
    _name="hr.payroll.settings"

    _fields={
        "tax_rates": fields.One2Many("hr.tax.rate","settings_id","Tax Rates"),
        "social_rate": fields.Decimal("Rate (%)"),
        "social_min_wage": fields.Decimal("Min Wage Per Month"),
        "social_max_wage": fields.Decimal("Max Wage Per Month"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "social_number": fields.Char("SSO Identification No.",multi_company=True),
        "prov_name": fields.Char("Provident Fund Name",multi_company=True),
        "prov_no": fields.Char("Provident Fund No.",multi_company=True),
        "child_alw_limit": fields.Integer("Limit to Children"),
        "child_alw_limit": fields.Integer("Limit to Children"),
        'journal_id': fields.Many2One("account.journal","Journal",multi_company=True),
        'bank_account_id': fields.Many2One("account.account","Bank Account",multi_company=True),
        'payroll_payable_id': fields.Many2One("account.account","Payroll Payable Account",multi_company=True),
        ### report address
        'company': fields.Char("Company Name",multi_company=True),
        'depart_room_number': fields.Char("Room No.",multi_company=True),
        'depart_stage':fields.Char("Stage",multi_company=True),
        'depart_village': fields.Char("Village",multi_company=True),
        'depart_name': fields.Char("Department Name",multi_company=True),
        'depart_number': fields.Char("Department No.",multi_company=True),
        'depart_sub_number': fields.Char("Dpt Sub No.",multi_company=True),
        'depart_soi': fields.Char("Soi",multi_company=True),
        'depart_road': fields.Char("Road",multi_company=True),
        'depart_district': fields.Char("District",multi_company=True),
        'depart_sub_district': fields.Char("Sub District",multi_company=True),
        'depart_province': fields.Char("Province",multi_company=True),
        'depart_zip': fields.Char("Zip",multi_company=True),
        'depart_tel': fields.Char("Tel.",multi_company=True),
        'depart_fax': fields.Char("Fax.",multi_company=True),
        'report_address_txt': fields.Text("Address Report",function="_get_report_address"),
    }

    def get_address_text(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            lines=[]            
            if obj.depart_name:
                lines.append(obj.depart_name)
            if obj.depart_room_number:
                lines.append(obj.depart_room_number)
            if obj.depart_stage:
                lines.append(obj.depart_stage)
            if obj.depart_village:
                lines.append(obj.depart_village)
            if obj.depart_number:
                lines.append(obj.depart_number)
            if obj.depart_sub_number:
                lines.append(obj.depart_sub_number)
            if obj.depart_soi:
                lines.append(obj.depart_soi)
            if obj.depart_road:
                lines.append(obj.depart_road)
            if obj.depart_sub_district:
                lines.append(obj.depart_sub_district)
            if obj.depart_district:
                lines.append(obj.depart_district)
            if obj.depart_province:
                lines.append(obj.depart_province)
            if obj.depart_zip:
                lines.append(obj.depart_zip)
            s=" ".join(lines)
            vals[obj.id]=s
        return s

    def get_address_text_thai(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            lines=[]
            if obj.depart_name:
                lines.append(obj.depart_name)
            if obj.depart_room_number:
                lines.append("ห้องที่ "+obj.depart_room_number)
            if obj.depart_stage:
                lines.append("ชั้น "+obj.depart_stage)
            if obj.depart_village:
                lines.append("หมู่บ้าน "+obj.depart_village)
            if obj.depart_number:
                lines.append("เลขที่ "+obj.depart_number)
            if obj.depart_sub_number:
                lines.append("หมู่ที่ "+obj.depart_sub_number)
            if obj.depart_soi:
                lines.append("ซอย"+obj.depart_soi)
            if obj.depart_road:
                lines.append("ถนน"+obj.depart_road)
            if obj.depart_sub_district:
                lines.append(obj.depart_sub_district)
            if obj.depart_district:
                lines.append(obj.depart_district)
            if obj.depart_province:
                lines.append(obj.depart_province)
            #if obj.depart_zip:
                #lines.append(obj.depart_zip)
            s=" ".join(lines)
            vals[obj.id]=s
        return s

Settings.register()
