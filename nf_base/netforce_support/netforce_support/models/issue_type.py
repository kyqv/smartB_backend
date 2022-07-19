from netforce.model import Model,fields,get_model

class IssueType(Model):
    _name="issue.type"
    _string="Issue Type"
    _fields={
        "name": fields.Char("Name",required=True),
    }
    _order="name"

IssueType.register()
