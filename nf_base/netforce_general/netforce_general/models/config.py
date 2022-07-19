from netforce.model import Model, fields
from netforce import access
from netforce import ipc

class Config(Model):
    _name = "config"
    _string = "Config"
    _fields = {
        "type": fields.Char("Type",search=True),
        "name": fields.Char("Name",required=True,search=True),
        "label": fields.Char("Label",search=True),
        "value": fields.Text("Value",search=True),
        "user_id": fields.Many2One("base.user","User"),
    }
    _order="type,name"

    def save_config(self,type,name,value,label=None,context={}):
        user_id=access.get_active_user()
        res=self.search([["type","=",type],["name","=",name],["user_id","=",user_id]])
        if res:
            config_id=res[0]
            self.write([config_id],{"value":value,"label":label})
        else:
            vals={
                "type": type,
                "name": name,
                "value": value,
                "label": label,
                "user_id": user_id,
            }
            config_id=self.create(vals)
        ipc.send_signal("clear_ui_params_cache")
        return config_id

    def get_config(self,type,name,context={}):
        res=self.search([["type","=",type],["name","=",name]])
        if not res:
            return None
        obj_id=res[0]
        obj=self.browse(obj_id)
        return obj.value

    def config_to_json(self,user_id,context={}):
        configs={}
        for obj in self.search_browse([["user_id","=",user_id]]):
            configs["%s.%s"%(obj.type,obj.name)]=obj.value
        return configs

Config.register()
