from netforce.model import Model, fields, get_model

class Account(Model):
    _name = "voice.account"
    _string = "Voice Account"
    _name_field = "name"
    _fields = {
        "name": fields.Char("Account Name", required=True, search=True),
        "type": fields.Selection([["nexmo","Nexmo"]], "Type", required=True),
        "sequence": fields.Integer("Sequence"),
    }

Account.register()
