var _models={};

function get_model(model) {
    var m=_models[model];
    if (!m) {
        m=exec(model,"get_meta",[]);
        _models[model]=m;
    }
    return m;
}

function get_field(model,field) {
    var m=get_model(model);
    if (!m.fields) throw "Missing model fields";
    return m.fields[field];
}

function _check_eager_load(model,field) {
    var f=get_field(model,field);
    if (!f) throw "Field not found: "+model+"."+field;
    if (f["function"]) return false;
    if (f.type=="one2many" || f.type=="many2many") return false;
    return true;
}

var _browse_handler={
    get: function(obj,name) {
        if (name=="id") return obj.id;
        else if (name=="_model") return obj._model;
        if (!obj.id) return null;
        var model_cache=obj._browse_cache[obj._model];
        if (!model_cache) {
            model_cache={};
            obj._browse_cache[obj._model]=model_cache;
        }
        var record_cache=model_cache[obj.id];
        if (!record_cache) {
            record_cache={};
            model_cache[obj.id]=record_cache;
        }
        if (name in record_cache) {
            return record_cache[name];
        }
        var read_ids=[obj.id];
        //throw "read_ids="+JSON.stringify(read_ids);
        var read_fields=[name];
        if (_check_eager_load(obj._model,name)) {
            var m=get_model(obj._model);
            for (var n in m.fields) {
                if (n==name) continue;
                if (_check_eager_load(obj._model,n)) read_fields.push(n);
            }
            for (var id of obj._related_ids) {
                if (id!=obj.id && !(id in model_cache) || !(name in model_cache[id])) {
                    read_ids.push(id);
                }
            }
        }
        //throw "read_fields="+JSON.stringify(read_fields);
        var res=exec(obj._model,"read",[read_ids,read_fields],{load_m2o:false});
        for (var n of read_fields) {
            var f=get_field(obj._model,n);
            if (!f) throw "Field not found: "+obj._model+"."+n;
            if (f.type=="many2one") {
                var rids_set={};
                var rids=[];
                for (var r of res) {
                    var rid=r[n];
                    if (!rid) continue;
                    if (!rids_set[rid]) rids.push(rid);
                    rids_set[rid]=true;
                }
                for (var r of res) {
                    var rid=r[n];
                    r[n]=browse(f.relation,rid,{related_ids:rids});
                }
            } else if (f.type=="one2many" || f.type=="many2many") {
                var rids_set={};
                var rids=[];
                for (var r of res) {
                    var val=r[n];
                    for (var rid of val) {
                        if (!rids_set[rid]) rids.push(rid);
                        rids_set[rid]=true;
                    }
                }
                for (var r of res) {
                    var val=r[n];
                    r[n]=browse_list(f.relation,val,{related_ids:rids,browse_cache:obj._browse_cache});
                }
            }
        }
        for (var r of res) {
            var vals=model_cache[r.id];
            if (!vals) {
                vals={};
                model_cache[r.id]=vals;
            }
            Object.assign(vals,r);
        }
        return record_cache[name];
    }
}

function browse(model,record_id,{related_ids,browse_cache}) {
    var obj={};
    if (!model) throw "Missing model";
    obj._model=model;
    obj.id=record_id;
    obj._browse_cache=browse_cache||{};
    if (related_ids) {
        obj._related_ids=related_ids;
    } else {
        obj._related_ids=record_id?[record_id]:[];
    }
    return new Proxy(obj,_browse_handler);
}

function browse_list(model,record_ids,{related_ids,browse_cache}) {
    if (!model) throw "Missing model";
    if (!record_ids) throw "Missing record_ids";
    if (!browse_cache) browse_cache={};
    var res=[];
    for (var id of record_ids) {
        var val=browse(model,id,{related_ids,browse_cache});
        res.push(val);
    }
    return res;
}

function search_browse(model,cond) {
    var ids=exec(model,"search",[cond]);
    var res=browse_list(model,ids,{related_ids:ids});
    return res;
}

function get_data_path(data, path) {
    //console.log("get_data_path",data,path);
    var parent=true;
    if (!path) {
        return data;
    }
    var val = data;
    var fields = path.split(".");
    if (parent) {
        fields = fields.slice(0,-1);
    }
    for (var field of fields) {
        //console.log("field",field);
        val = val[field];
    }
    //console.log("=> val",val);
    return val
}
