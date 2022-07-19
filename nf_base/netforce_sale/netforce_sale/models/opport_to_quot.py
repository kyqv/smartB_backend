from netforce.model import Model,fields,get_model

class OpportToQuot(Model):
    _name="opport.to.quot"
    _fields={
        "opport_id": fields.Many2One("sale.opportunity","Sales Opportunity"),
        "template_id": fields.Many2One("sale.quot","Quotation Template",condition=[["is_template","=",True]]),
    }
    _defaults={
        "opport_id": lambda self,ctx: ctx.get("refer_id"),
    }

    def create_quot(self,ids,context={}):
        obj=self.browse(ids[0])
        opport=obj.opport_id
        res=opport.copy_to_quotation(context={"template_id":obj.template_id.id})
        return res

OpportToQuot.register()
