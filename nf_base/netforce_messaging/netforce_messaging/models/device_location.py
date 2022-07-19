from netforce.model import Model, fields, get_model
from netforce import access
import time


class Location(Model):
    _name = "device.location"
    _string = "Device Location"
    _fields = {
        "time": fields.DateTime("Time", required=True, search=True),
        "device_id": fields.Many2One("device.token","Device",search=True),
        "coords": fields.Char("Coordinates",search=True),
    }
    _order = "time desc"
    _defaults={
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }

Location.register()
