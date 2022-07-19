# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model, models, clear_js_cache
from netforce import ipc
from netforce import tasks
import os

def _clear_js_cache():
    pid = os.getpid()
    print("_clear_js_cache pid=%s" % pid)
    clear_js_cache()

ipc.set_signal_handler("clear_js_cache", _clear_js_cache)

class Model(Model):
    _name = "model"
    _string = "Model"
    _name_field = "string"
    _key = ["name"]
    _audit_log=True
    _fields = {
        "name": fields.Char("Model Code", required=True, search=True, index=True),
        "string": fields.Char("Model Label", required=True, search=True),
        "fields": fields.One2Many("field", "model_id", "Fields"),
        "custom": fields.Boolean("Custom Model"),
        "order": fields.Char("Order"),
        "name_field": fields.Char("Name Field"),
        "code_js": fields.Text("Code"),
        "code_trans": fields.Text("Code (Transpiled)"),
        "next_record_id": fields.Integer("Next Record ID"),
        "audit_log": fields.Boolean("Audit Log"),
        "state": fields.Selection([["draft","Draft"],["done","Completed"]],"Status"),
        "layouts": fields.One2Many("view.layout","model_id","Layouts"),
    }
    _order = "name"
    _defaults={
        "state": "draft",
    }

    def name_get(self, ids, context={}):
        print("model.name_get",ids)
        #if len(ids)>1000:
        #    import pdb; pdb.set_trace()
        vals = []
        for obj in self.browse(ids):
            if obj.name:
                name = "%s (%s)" % (obj.string, obj.name)
            else:
                name = obj.string
            vals.append((obj.id, name))
        return vals
    
    def name_search_multi(self, name, models, condition=[], limit=None, context={}):
        for model in models:
            m = get_model(model)
            res = m.name_search(name, condition=condition, limit=limit, context=context)
            if res:
                return {
                    "model": model,
                    "values": res,
                }
        return {
            "model": None,
            "values": [],
        }

    def gen_models(self,context={}):
        job_id = context.get("job_id")
        i = 0
        for name,m in sorted(models.items()):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i/len(models.items())*100,"Updating %s of %s models"%(i,len(models.items())))
            vals={
                "name": name,
                "string": m._string or name,
            }
            res=get_model("model").search([["name","=",name]])
            if res:
                model_id=res[0]
            else:
                model_id=get_model("model").create(vals)
            for n,f in m._fields.items():
                vals={
                    "model_id": model_id,
                    "name": n,
                    "string": f.string,
                }
                res=get_model("field").search([["model_id","=",model_id],["name","=",n]])
                if res:
                    field_id=res[0]
                else:
                    field_id=get_model("field").create(vals)
            i += 1

    def write(self, ids, vals, **kw):
        if not "state" in vals:
            for obj in self.browse(ids):
                if obj.state=="done":
                    raise Exception("Invalid model status")
        res = super().write(ids, vals, **kw)
        ipc.send_signal("clear_ui_params_cache")
        ipc.send_signal("clear_js_cache")

    def delete(self, *a, **kw):
        res = super().delete(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")
        ipc.send_signal("clear_js_cache")

    def transpile(self,ids,context={}):
        print("transpile",ids)
        obj=self.browse(ids[0])
        if not obj.code_js:
            raise Exception("Missing code")
        path="/home/nf/babel/orig_code.js"
        f=open(path,"w")
        f.write(obj.code_js)
        f.close()
        code_trans=os.popen("cd /home/nf/babel; npx babel %s"%path).read()
        print("=> code_trans")
        print(code_trans)
        obj.write({"code_trans":code_trans})

    def set_done(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"done"})

    def sync_download(self,models,last_write_time=None,context={}):
        max_t=None
        data={}
        for model in models:
            m=get_model(model)
            cond=[]
            if last_write_time:
                cond.append(["write_time",">=",last_write_time])
            field_names=[]
            for n,f in m._fields.items():
                if f.store:
                    field_names.append(n)
            res=m.search_read(cond,field_names)
            data[model]=res
            for r in res:
                if max_t is None or r["write_time"]>max_t:
                    max_t=r["write_time"]
        return {
            "data": data,
            "last_write_time": max_t,
        }

Model.register()
