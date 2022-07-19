from netforce.model import Model, fields
from netforce import static
from netforce import ipc
import time


class Tooltip(Model):
    _name = "help.tooltip"
    _string = "Tooltip"
    _fields = {
        "code": fields.Char("Tooltip Code", search=True, required=True),
        "title": fields.Char("Title", search=True),
        "description": fields.Char("Description", search=True),
        "placement": fields.Selection([["top","Top"],["right","Right"],["bottom","Bottom"],["left","Left"]],"Placement", search=True),
    }
    _order = "code"

    def create(self, *a, **kw):
        new_id = super().create(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")
        return new_id

    def write(self, *a, **kw):
        res = super().write(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def delete(self, *a, **kw):
        res = super().delete(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def tooltips_to_json(self,context={}):
        tooltips={}
        for obj in self.search_browse([]):
            vals={
                "code": obj.code,
                "title": obj.title,
                "description": obj.description,
                "placement": obj.placement,
            }
            tooltips[obj.code]=vals
        return tooltips

Tooltip.register()
