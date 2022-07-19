from netforce.controller import WebSocketHandler
from netforce import tasks
import json
import tornado.ioloop
import datetime

class GetProgress(WebSocketHandler):
    _path="/get_progress"

    def check_origin(self,origin):
        return True

    def open(self):
        print("GetProgress.open")
        self.job_id=int(self.get_argument("job_id"))
        print("job_id=%s"%self.job_id)
        self.send_enabled=True
        loop=tornado.ioloop.IOLoop.instance()
        loop.add_timeout(datetime.timedelta(seconds=1),self.send_progress)

    def send_progress(self):
        if not self.send_enabled:
            return
        data=tasks.get_progress(self.job_id)
        print("send_progress",self.job_id)
        if data:
            msg=json.dumps(data)
            self.write_message(msg)
            if data.get("result") or data.get("error"):
                self.send_enabled=False
        if self.send_enabled:
            loop=tornado.ioloop.IOLoop.instance()
            loop.add_timeout(datetime.timedelta(seconds=1),self.send_progress)

    def on_close(self):
        print("GetProgress.on_close")
        self.send_enabled=False
        # TODO: clear tasks._progress memory

GetProgress.register()
