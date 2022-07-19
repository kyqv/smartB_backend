from netforce.model import Model, fields


class Settings(Model):
    _inherit = "settings"
    _fields = {
        "mfg_order_create_fg": fields.Boolean("Create FG Receipt When MO Completed"),
    }

Settings.register()
