from netforce.model import Model, fields, get_model


class EmailRule(Model):
    _name = "email.rule"
    _string = "Email Rule"
    _fields = {
        "sequence": fields.Integer("Sequence"),
        "mailbox_id": fields.Many2One("email.mailbox","Mailbox"),
        "from_addr": fields.Char("From Expression"),
        "to_addr": fields.Char("To Expression"),
        "subject": fields.Char("Subject Expression"),
        "body": fields.Text("Body Expression"),
        "action": fields.Selection([["spam","Mark as spam"],["copy_to_lead","Copy To Lead"],["convert_lead","Convert Lead"]],"Action"),
        "action_params": fields.Text("Action Params"),
    }
    _order = "sequence"

EmailRule.register()
