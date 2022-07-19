from netforce.model import Model, fields, get_model
from netforce import database
from netforce import access
import time

class Session(Model):
    _name = "visitor.session"
    _string = "Session"
    _name_field="id_no"
    _fields = {
        "id_no": fields.Char("Session ID",required=True),
        "visitor_id": fields.Many2One("visitor","Visitor",required=True),
        "create_time": fields.DateTime("Create Time",readonly=True),
        "actions": fields.One2Many("visitor.action","session_id","Actions"),
        "num_actions": fields.Integer("Num Actions",function="get_num_actions"),
    }
    _order="id desc"

    def get_num_actions(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.actions)
        return vals

Session.register()
