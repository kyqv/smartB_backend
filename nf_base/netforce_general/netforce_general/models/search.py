from netforce.model import Model, fields, models


class Search(Model):
    _name = "search"

    def search_all(self,q,search_models=None,context={}):
        results=[]
        for name,m in models.items():
            if not m._content_search:
                continue
            res=m.content_search(q,limit=100)
            for r in res:
                results.append({
                    "model": name,
                    "id": r["id"],
                    "fields": r["fields"],
                    "create_time": r["create_time"],
                })
        results.sort(key=lambda r:r["create_time"],reverse=True)
        return results

Search.register()
