from netforce.model import Model, fields

class Leave_type(Model):
    _name="hr.leave.type"
    _string="Leave Type"
    _key=["name"]
    
    _fields={
        "name": fields.Char("Name", search=True),
        "description": fields.Text("Description"),
        "comments":fields.One2Many("message","related_id","Comments"),
        "employees": fields.Many2Many("hr.employee","Employees"),
    }

Leave_type.register()
