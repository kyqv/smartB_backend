from netforce.model import Model, fields
from netforce import database
import json


class ModelInst(Model):
    _name = "model.inst"
    _string = "Model Instance"
    _fields = {
        "model_id": fields.Many2One("model","Model",search=True),
        "model": fields.Char("Model"),
        "record_id": fields.Integer("Record ID",search=True),
        "field_values": fields.One2Many("field.value","inst_id","Field Values"),
        "field_values_str": fields.Text("Field Values",function="get_field_values_str"),
    }
    _order="id desc"

    def name_get(self,ids,context={}):
        res=[]
        for obj in self.browse(ids):
            name="#%s"%obj.id
            res.append((obj.id,name))
        return res

    def create(self,vals,context={}):
        model_id=vals["model_id"]
        db=database.get_connection()
        res=db.get("SELECT record_id FROM model_inst WHERE model_id=%s ORDER BY record_id desc LIMIT 1",model_id)
        last_record_id=res.record_id if res else None
        if last_record_id:
            record_id=last_record_id+1
        else:
            record_id=1
        vals["record_id"]=record_id
        return super().create(vals,context=context)

    def get_field_values_str(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            data={}
            for v in obj.field_values:
                data[v.field_id.name]=v.value
            vals[obj.id]=json.dumps(data)
        return vals

    def set_models(self,context={}):
        for obj in self.search_browse([]):
            if obj.model_id:
                obj.write({"model":obj.model_id.name})


ModelInst.register()
