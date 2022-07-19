from netforce.model import Model, fields, get_model

class TrackDistrib(Model):
    _name = "track.distrib"
    _string = "Tracking Distribution"
    _fields = {
        "name": fields.Char("Name",function="get_name"),
        "lines": fields.One2Many("track.distrib.line","distrib_id","Lines"),
    }
    _order="id desc"
    _string = "Tracking Distribution"

    def get_name(self,ids,context={},**kw):
        vals={}
        for obj in self.browse(ids):
            name="\n".join(["- %s: %s%%"%(l.track_id.name,int(l.percent or 0)) for l in obj.lines])
            vals[obj.id]="PD-%.4d:\n"%obj.id+name
        return vals

    def name_search(self, name, condition=None, limit=None, context={}):
        cond=["or",["lines.track_id.code","ilike",name],["lines.track_id.name","ilike",name]]
        ids = self.search(cond)
        return self.name_get(ids, context=context)

TrackDistrib.register()
