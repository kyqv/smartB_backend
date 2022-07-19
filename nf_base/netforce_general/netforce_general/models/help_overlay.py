from netforce.model import Model, fields, get_model
from netforce import static
import time


class Overlay(Model):
    _name = "help.overlay"
    _string = "Overlay"
    _fields = {
        "code": fields.Char("Overlay Code", search=True, required=True),
    }
    _order = "code"

    def is_enabled(self,code,context={}):
        res=self.search([["code","=",code]])
        if not res:
            return
        val=get_model("config").get_config("help_overlay",code)
        return val!="disabled"

    def disable(self,code,context={}):
        get_model("config").save_config("help_overlay",code,"disabled")

Overlay.register()
