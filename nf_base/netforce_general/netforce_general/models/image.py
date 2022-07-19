from netforce.model import Model, fields
from netforce import access


class Image(Model):
    _name = "image"
    _string = "Image"
    _fields = {
        "image": fields.File("Image"),
        "related_id": fields.Reference([],"Related To"),
    }

Image.register()
