from netforce.model import Model, fields
from netforce import database
import json


class History(Model):
    _name = "record.history"
    _string = "Record History"
    _fields = {
        "time": fields.DateTime("Date/Time",required=True,search=True),
        "model": fields.Char("Model",required=True,search=True),
        "record_id": fields.Integer("Record ID",search=True),
        "user_id": fields.Many2One("base.user","User",search=True),
        "field_values": fields.One2Many("field.value","history_id","Field Values"),
        "num_fields": fields.Integer("Fields Changed",function="get_num_fields"),
    }
    _order="id desc"

    def name_get(self,ids,context={}):
        res=[]
        for obj in self.browse(ids):
            name="#%s"%obj.id
            res.append((obj.id,name))
        return res

    def get_num_fields(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.field_values)
        return vals

History.register()
