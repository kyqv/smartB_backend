from netforce.model import Model, fields, get_model

class TaxRate(Model):
    _name="hr.tax.rate"
    _fields={
        "settings_id": fields.Many2One("hr.payroll.settings","Settings"),
        "tax_year_id": fields.Many2One("hr.tax.year","Tax Year"),
        "sequence": fields.Integer("Step No."),
        "min_income": fields.Decimal("Min. Net Income"),
        "max_income": fields.Decimal("Max. Net Income"),
        "rate": fields.Decimal("Tax Rate"),
    }
    _order="sequence"

    def compute_tax(self,taxyear_id,income=0):
        #print('hr.tax.rate.compute_tax ', income)
        if not taxyear_id:
            print('no tax year id')
            return 0
        total_tax=0
        total_base=0
        dom=[['tax_year_id','=',taxyear_id]]
        for obj in self.search_browse(dom):
            if obj.min_income and income<obj.min_income:
                break
            base=min(income,obj.max_income)-total_base
            tax=base*(obj.rate or 0)/100
            total_tax+=tax
            total_base+=base
        return total_tax

TaxRate.register()
