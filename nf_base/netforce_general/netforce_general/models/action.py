from netforce.model import Model, fields
from netforce import ipc
import json


class Action(Model):
    _name = "action"
    _string = "Action"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "string": fields.Char("Title", search=True),
        "view": fields.Selection([["multi_view", "Multi"], ["board", "Dashboard"], ["list_view", "List"], ["form_view", "Form"], ["page", "Page"], ["print_wizard2","Print"], ["calendar", "Calendar"], ["gantt", "Gantt"]], "View", search=True),
        "view_layout_id": fields.Many2One("view.layout", "Layout"),
        "model_id": fields.Many2One("model", "Model"),
        "menu_id": fields.Many2One("view.layout", "Menu (old)", condition=[["type", "=", "menu"]]),
        "menu": fields.Char("Menu"),
        "options": fields.Text("Options"),
        "module_id": fields.Many2One("module", "Module"),
    }
    _order = "name"

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.string:
                name = "[%s] %s" % (obj.name, obj.string)
            else:
                name = "[%s]" % obj.name
            vals.append((obj.id, name))
        return vals

    def actions_to_json(self):
        data = {}
        for obj in self.search_browse([]):
            vals = {
                "name": obj.name,
            }
            if obj.string:
                vals["string"] = obj.string
            if obj.view:
                vals["view_cls"] = obj.view
            if obj.menu_id:
                vals["menu"] = obj.menu_id.name
            if obj.view_layout_id:
                vals["view_xml"] = obj.view_layout_id.name
            if obj.model_id:
                vals["model"] = obj.model_id.name
            if obj.options:
                try:
                    opts = json.loads(obj.options)
                    vals.update(opts)
                except Exception as e:
                    raise Exception("Failed to parse options of action '%s': %s" % (obj.name, e))
            data[obj.name] = vals
        return data

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

Action.register()
