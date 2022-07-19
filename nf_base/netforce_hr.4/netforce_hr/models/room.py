from netforce.model import Model, fields

class Room(Model):
    _name="room"
    _string="Room"
    _fields={
        "name": fields.Char("Name", search=True),
        "description": fields.Text("Description"),
        "comments":fields.One2Many("message","related_id","Comments")
    }

Room.register()
