from netforce.model import Model, fields, get_model

class PayItemProfileLine(Model):
    _name="hr.payitem.profile.line"
    _string="Pay Item Profile"
    _fields={
        "profile_id": fields.Many2One("hr.payitem.profile","Profile",required=True,on_delete="cascade"),
        "payitem_id": fields.Many2One("hr.payitem","Pay Item"),
    }
    _defaults={

    }

PayItemProfileLine.register()
