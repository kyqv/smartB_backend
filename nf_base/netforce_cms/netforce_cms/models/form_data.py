from netforce.model import Model, fields, get_model
from netforce import access
import time

class FormData(Model):
    _name = "form.data"
    _string = "Form Submission"
    _fields = {
        "user_id": fields.Many2One("base.user","User"),
        "time": fields.DateTime("Time"),
        "type": fields.Char("Form Type"),
        "data": fields.Json("Data"),
    }
    _order="id desc"
    _defaults={
        "user_id": lambda *a: access.get_active_user(),
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    def submit(self,data,type=None,form_id=None,context={}):
        if form_id:
            form_id=int(form_id)
            obj=self.browse(form_id)
            vals={}
            if type:
                vals["type"]=type
            new_data=obj.data or {}
            new_data.update(data)
            vals["data"]=new_data
            obj.write(vals)
        else:
            vals={
                "data": data,
                "type": type,
            }
            form_id=self.create(vals)
        return {
            "form_id": form_id,
        }

    def get_form_data(self,form_id,context={}):
        form_id=int(form_id)
        obj=self.browse(form_id)
        return obj.data

    def get_value(self,form_id,context={}):
        if not form_id:
            return {}
        form_id=int(form_id)
        obj=self.browse(form_id)
        return obj.data

    def set_value(self,form_id,data,type=None,context={}):
        if form_id:
            form_id=int(form_id)
            obj=self.browse(form_id)
            vals={}
            if type:
                vals["type"]=type
            new_data=obj.data or {}
            new_data.update(data)
            vals["data"]=new_data
            obj.write(vals)
        else:
            vals={
                "data": data,
                "type": type,
            }
            form_id=self.create(vals)
        return form_id

FormData.register()
