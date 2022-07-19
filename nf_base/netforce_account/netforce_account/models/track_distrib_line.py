from netforce.model import Model, fields, get_model

class TrackDistribLine(Model):
    _name = "track.distrib.line"
    _string="Tracking Distribution Line"
    _fields = {
        "distrib_id": fields.Many2One("track.distrib","Distribution",required=True,on_delete="cascade"),
        "track_id": fields.Many2One("account.track.categ","Tracking Category",required=True),
        "ratio": fields.Decimal("Ratio",required=True),
        "percent": fields.Decimal("Percent (%)",function="get_percent"),
    }

    def get_percent(self,ids,context={}):
        dist_ids=[]
        for obj in self.browse(ids):
            dist_ids.append(obj.distrib_id.id)
        dist_ids=list(set(dist_ids))
        vals={}
        for dist in get_model("track.distrib").browse(dist_ids):
            total=0
            for line in dist.lines:
                total+=line.ratio or 0
            for line in dist.lines:
                if line.id in ids:
                    vals[line.id]=(line.ratio or 0)*100/total if total else None
        return vals

TrackDistribLine.register()
