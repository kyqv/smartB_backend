from netforce.model import Model, fields
from netforce import ipc


class ViewLayout(Model):
    _name = "view.layout"
    _string = "Layout"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "inherit": fields.Char("Inherit", search=True),
        "model_id": fields.Many2One("model", "Model", search=True),
        "type": fields.Selection([["list", "List"], ["form", "Form"], ["search","Search"], ["menu", "Menu"], ["board", "Dashboard"], ["page", "Page"], ["grid", "Grid"], ["calendar", "Calendar"], ["gantt", "Gantt"], ["inherit", "Inherit"]], "Type", search=True),
        "layout": fields.Text("Layout", search=True),
        "priority": fields.Integer("Priority"),
        "module_id": fields.Many2One("module", "Module"),
    }
    _order = "name"

    def layouts_to_json(self):
        data = {}
        for obj in self.search_browse([]):
            vals = {
                "name": obj.name,
                "type": obj.type,
                "layout": obj.layout,
                "priority": obj.priority,
            }
            if obj.model_id:
                vals["model"] = obj.model_id.name
            if obj.inherit:
                vals["inherit"] = obj.inherit
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

ViewLayout.register()
