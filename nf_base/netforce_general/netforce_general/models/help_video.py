from netforce.model import Model, fields
from netforce import static
from netforce import ipc
import time


class Video(Model):
    _name = "help.video"
    _string = "Video Tutorial"
    _fields = {
        "code": fields.Char("Video Code", required=True, search=True),
        "title": fields.Char("Title", required=True),
        "popup_title": fields.Char("Popup Title", required=True),
        "url": fields.Char("Youtube URL", search=True),
    }
    _order = "code"

    def create(self, *a, **kw):
        new_id = super().create(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")
        return new_id

    def write(self, *a, **kw):
        res = super().write(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def delete(self, *a, **kw):
        res = super().delete(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def videos_to_json(self,user_id,context={}):
        videos={}
        for obj in self.search_browse([]):
            vals={
                "code": obj.code,
                "title": obj.title,
                "popup_title": obj.popup_title,
                "url": obj.url,
            }
            videos.setdefault(obj.code,[]).append(vals)
        return videos

Video.register()
