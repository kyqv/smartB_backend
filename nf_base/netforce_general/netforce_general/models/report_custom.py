from netforce.model import Model, fields

class Report(Model):
    _name = "report.custom"
    _name_field = "Custom Report"
    _fields = {
        "name": fields.Char("Report Name", required=True),
        "code": fields.Char("Report Code"),
        "config": fields.Text("Configuration Data"),
    }

Report.register()
