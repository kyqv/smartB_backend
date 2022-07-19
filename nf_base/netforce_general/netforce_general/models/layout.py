from netforce.model import Model, fields


class Layout(Model):
    _name = "layout"
    _string = "Layout"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "layout": fields.Text("Layout"),
    }
    _order = "name"

    def get_layout(self,name,context={}):
        res=self.search([["name","=",name]])
        if not res:
            return {
                "layout": None,
            }
        obj_id=res[0]
        obj=self.browse(obj_id)
        return {
            "layout": obj.layout,
        }

    def set_layout(self,name,layout,context={}):
        res=self.search([["name","=",name]])
        if res:
            obj_id=res[0]
            self.write([obj_id],{"layout":layout})
        else:
            vals={
                "layout": layout,
                "name": name,
            }
            obj_id=self.create(vals)

Layout.register()
