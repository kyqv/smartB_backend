from netforce.model import Model, fields
from netforce import database

class Report(Model):
    _name = "report"
    _store=False

    def query(self,q,context={}):
        db=database.get_connection()
        res=db.query(q) # XXX: readonly + perms
        data=[]
        for r in res:
            data.append(dict(r))
        return data

Report.register()
