from netforce.model import Model, fields, get_model
from datetime import *
import time


class ShipPort(Model):
    _name = "ship.port"
    _string = "Shipping Port"
    _fields = {
        "name": fields.Char("Name", required=True),
        "country_id": fields.Many2One("country","Country"),
    }
    _order = "name"

ShipPort.register()
