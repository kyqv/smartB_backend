from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
import json

class Download(Controller):
    _path="/download"

    def get(self):
        print("#"*80)
        print("DOWNLOAD")
        model=self.get_argument("model")
        method=self.get_argument("method")
        active_id=int(self.get_argument("active_id"))
        dbname=self.get_argument("database",None)
        if dbname:
            database.set_active_db(dbname)
        # TODO: user,token
        with database.Transaction():
            access.set_active_user(1) # XXX
            m=get_model(model)
            f=getattr(m,method,None)
            if not f:
                raise Exception("Invalid method %s of %s"%(method,model))
            res=f([active_id])
            filename=res.get("filename","download.txt")
            content_type=res.get("content_type","text/plain")
            data=res.get("data")
            self.set_header("Content-Disposition","attachment; filename=%s"%filename)
            self.set_header("Content-Type","text/plain")
            self.write(data)

Download.register()
