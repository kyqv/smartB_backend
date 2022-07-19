from netforce.model import Model, fields, get_model


class Invoice(Model):
    _inherit = "account.invoice"

    def post(self,ids,**kw):
        for obj in self.browse(ids):
            proj=obj.related_id
            if not proj or proj._model!="project" or not proj.track_id:
                continue
            for line in obj.lines:
                if line.track_id:
                    continue
                if line.track_distrib_id:
                    continue
                line.write({"track_id":proj.track_id.id})
        return super().post(ids,**kw)

Invoice.register()
