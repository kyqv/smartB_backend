# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from netforce import database
from netforce import access
from . import fields
import csv
from io import StringIO
import netforce
import os
import shutil
import re
import ast
from datetime import *
import time
import psycopg2
import dateutil.parser
import netforce
from lxml import etree
from netforce import utils
from decimal import *
from pprint import pprint
import codecs
import tempfile
import json
import quickjs
try:
    import pandas as pd
except:
    print("Failed to import pandas")

dir_path=os.path.dirname(os.path.abspath(__file__))
model_js_code=open(dir_path+"/model.js").read()
moment_js_code=open(dir_path+"/moment.js").read()

models = {}
browse_cache = {}

def get_model(name):
    m = models.get(name)
    if m:
        return m
    return CustomModel(name)
    #raise Exception("Model not found: %s" % name)

def clear_cache():
    browse_cache.clear()

MAX_JS_CONTEXTS=100
num_used_js_contexts=0

js_context_pool=[]

# create qjs context here because quickjs bug
def init_js():
    print("init_js %s"%MAX_JS_CONTEXTS)
    for i in range(MAX_JS_CONTEXTS):
        ctx=quickjs.Context()
        js_context_pool.append(ctx)

def new_js_context():
    print("^"*80)
    print("new_js_context")
    global num_used_js_contexts
    if num_used_js_contexts>=MAX_JS_CONTEXTS:
        raise Exception("Too many js contexts (%s)"%(num_used_js_contexts+1,))
    ctx=js_context_pool[num_used_js_contexts]
    num_used_js_contexts+=1
    print("=> num_used_js_contexts=%s"%num_used_js_contexts)
    return ctx

js_contexts={}

def clear_js_cache():
    global num_used_js_contexts
    js_contexts.clear()    
    js_context_pool.clear()
    num_used_js_contexts=0
    init_js()

class ValidationError(Exception):

    def __init__(self, msg, error_fields=None):
        super().__init__(msg)
        self.error_fields = error_fields

class LogError(Exception):
    def __init__(self, msg, details=None, type=None, require_logout=False):
        super().__init__(msg)
        self.details = details
        self.type = type
        self.require_logout = require_logout

class Model(object):
    _name = None
    _string = None
    _fields = None
    _custom_fields = None
    _table = None
    _inherit = None
    _defaults = {}
    _order = None
    _key = None
    _name_field = None
    _code_field = None
    _export_field = None
    _image_field = None
    _store = True
    _transient = False
    _context = {}
    _sql_constraints = []
    _constraints = []
    _export_fields = None
    _audit_log = False
    _indexes = []
    _multi_company = False
    _offline = False
    _content_search = False
    _history = False

    @classmethod
    def register(cls):
        if cls._inherit:
            parent_model = get_model(cls._inherit)
            parent_cls = parent_model.__class__
            model_cls = type(cls._inherit, (cls, parent_cls), {})
            model_cls._fields = parent_cls._fields.copy()
            model_cls._fields.update(cls._fields or {})
            model_cls._defaults = parent_cls._defaults.copy()
            model_cls._defaults.update(cls._defaults)
        else:
            if not cls._name:
                raise Exception("Missing model name in %s" % cls)
            if not cls._table:
                cls._table = cls._name.replace(".", "_")
            model_cls = cls
            cls_fields = {  # XXX
                "create_time": fields.DateTime("Create Time", readonly=True),
                "write_time": fields.DateTime("Write Time", readonly=True),
                "create_uid": fields.Integer("Create UID", readonly=True),
                "write_uid": fields.Integer("Write UID", readonly=True),
            }
            if model_cls._fields:
                cls_fields.update(model_cls._fields)
            model_cls._fields = cls_fields
        model = object.__new__(model_cls)
        models[model_cls._name] = model
        for n, f in model_cls._fields.items():
            f.register(model_cls._name, n)

    def update_db(self):
        db = database.get_connection()
        res = db.get("SELECT * FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname=%s", self._table)
        if not res:
            db.execute("CREATE TABLE %s (id SERIAL, PRIMARY KEY (id))" % self._table)
        else:
            res = db.query(
                "SELECT * FROM pg_attribute a WHERE attrelid=(SELECT pg_class.oid FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname=%s) AND attnum>0 AND attnotnull", self._table)
            for r in res:
                n = r.attname
                if n == "id":
                    continue
                f = self._fields.get(n)
                if f and f.store:
                    continue
                print("  dropping not-null of old column %s.%s" % (self._table, n))
                q = "ALTER TABLE %s ALTER COLUMN \"%s\" DROP NOT NULL" % (self._table, n)
                db.execute(q)

    def update_db_constraints(self):  # XXX: move to update_db
        db = database.get_connection()
        constraints = self._sql_constraints[:]
        # if self._key: # XXX
        #    constraints.append(("key_uniq","unique ("+", ".join([n for n in self._key])+")",""))
        for (con_name, con_def, _) in constraints:
            full_name = "%s_%s" % (self._table, con_name)
            res = db.get(
                "SELECT conname, pg_catalog.pg_get_constraintdef(pg_constraint.oid,true) AS condef FROM pg_constraint JOIN pg_catalog.pg_namespace n ON n.oid=pg_constraint.connamespace WHERE conname=%s", full_name)
            if res:
                if con_def == res["condef"].lower():
                    continue
                print("  constraint exists but must be deleted")
                print("    condef_old: %s" % res["condef"].lower())
                print("    condef_new: %s" % con_def)
                db.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (self._table, full_name))
            print("  adding constraint:", self._name, con_name, con_def)
            db.execute("ALTER TABLE %s ADD CONSTRAINT %s %s" % (self._table, full_name, con_def))

    def update_db_indexes(self):
        db = database.get_connection()
        for field_names in self._indexes:
            idx_name = self._table + "_" + "_".join(field_names) + "_idx"
            res = db.get("SELECT * FROM pg_index i,pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=i.indexrelid AND c.relname=%s", idx_name)
            if not res:
                print("creating index %s" % idx_name)
                db.execute("CREATE INDEX " + idx_name + " ON " + self._table + " (" + ",".join(field_names) + ")")

    def get_field(self, name):
        if not name in self._fields:
            raise Exception("No such field %s in %s" % (name, self._name))
        return self._fields[name]

    def default_get(self, field_names=None, context={}, load_m2o=True):
        vals = {}
        if field_names is None:
            field_names = self._defaults.keys()
        for n in field_names:
            v = self._defaults.get(n)
            if hasattr(v, "__call__"):
                vals[n] = v(self, context)
            else:
                vals[n] = v
        defaults = context.get("defaults", {})
        for n, v in defaults.items():
            f = self._fields.get(n)
            if not f:  # XXX
                continue
            if v:
                if isinstance(f, fields.Many2One):
                    v = int(v)
            vals[n] = v
        if field_names:
            db = database.get_connection()
            if db:
                user_id = access.get_active_user()
                res = db.query(
                    "SELECT field,value FROM field_default WHERE user_id=%s AND model=%s AND field IN %s", user_id, self._name, tuple(field_names))
                for r in res:
                    n = r.field
                    f = self._fields[n]
                    v = r.value
                    if v:
                        if isinstance(f, fields.Many2One):
                            v = int(v)
                        elif isinstance(f, fields.Float):
                            v = float(v)
                    vals[n] = v
        if load_m2o:
            def _add_name(vals, model):
                for n, v in vals.items():
                    if not v:
                        continue
                    f = model.get_field(n)
                    if isinstance(f, fields.Many2One):
                        mr = get_model(f.relation)
                        name = mr.name_get([v])[0][1]
                        vals[n] = [v, name]
                    elif isinstance(f, fields.One2Many):
                        for v2 in v:
                            _add_name(v2, get_model(f.relation))
            _add_name(vals, self)
        return vals

    def _add_missing_defaults(self, vals, context={}):
        other_fields = [n for n in self._fields if not n in vals or vals[n] is None]
        if not other_fields:
            return vals
        defaults = self.default_get(other_fields, context=context, load_m2o=False)
        for n in other_fields:
            v = defaults.get(n)
            if v is not None:
                f = self._fields[n]
                if isinstance(f, fields.One2Many): # XXX
                    v=[("create",x) for x in v]
                vals[n] = v
        return vals

    def _check_key(self, ids, context={}): # TODO: make more efficient
        if not self._key:
            return
        res=self.read(ids,self._key,load_m2o=False,context=context)
        for r in res:
            cond = [(k, "=", r[k]) for k in self._key]
            ids = self.search(cond)
            if len(ids) > 1:
                raise Exception("Duplicate keys: model=%s, %s" % (self._name, ", ".join(["%s='%s'"%(k,r[k]) for k in self._key])))
    
    def _check_required(self, vals, context={}):
        #Chin 2020-11-28
        for f_name in self._fields:
            f = self._fields.get(f_name)
            if not f.required:
                continue
            if f_name not in vals  or vals[f_name] is None or vals[f_name] == "":
                raise Exception("Violation of not null value: %s" % (f_name))

    def create(self, vals, context={}):
        vals=vals.copy() # XXX
        if not self.check_model_access("create",None,context={}):
            user_id=access.get_active_user()
            raise Exception("Permission denied (user_id=%s model=%s access=create)"%(user_id,self._name))
        vals = self._add_missing_defaults(vals, context=context)
        for n in vals:
            v=vals[n]
            if n not in self._fields:
                continue
            f = self._fields[n]
            if isinstance(f, fields.Char):
                if f.password and v:
                    vals[n] = utils.encrypt_password(v)
            elif isinstance(f, fields.Json):
                if not isinstance(v, str):
                    vals[n] = utils.json_dumps(v)
        if not vals.get("create_time"):
            vals["create_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if not vals.get("create_uid"):
            vals["create_uid"] = access.get_active_user()
        if vals.get("create_uid") and isinstance(vals["create_uid"],list): # XXX
            vals["create_uid"]=vals["create_uid"][0]
        if not vals.get("write_time"):
            vals["write_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if not vals.get("write_uid"):
            vals["write_uid"] = access.get_active_user()
        store_fields = [n for n in vals if n in self._fields and self._fields[n].store]
        trans_fields = [n for n in store_fields if self._fields[n].translate]
        for n in trans_fields:
            val=vals[n]
            if isinstance(val,dict):
                vals[n]=val.get("en_US")
        cols = store_fields[:]
        q = "INSERT INTO " + self._table
        q += " (" + ",".join(['"%s"' % col for col in cols]) + ")"
        q += " VALUES (" + ",".join(["%s" for col in cols]) + ") RETURNING id"
        args = [vals[n] for n in store_fields]
        db = database.get_connection()
        res = db.get(q, *args)
        new_id = res.id
        locale = netforce.locale.get_active_locale()
        if locale and locale != "en_US":  # XXX
            trans_fields = [n for n in store_fields if self._fields[n].translate]
            for n in trans_fields:
                val = vals[n]
                db.execute("INSERT INTO translation_field (lang,model,field,rec_id,translation) VALUES (%s,%s,%s,%s,%s)",
                           locale, self._name, n, new_id, val)
        multico_fields = [n for n in store_fields if self._fields[n].multi_company]
        if multico_fields:
            company_id = access.get_active_company()
            for n in multico_fields:
                val = vals[n]
                if val is not None:
                    f = self._fields[n]
                    if isinstance(f, fields.Many2One):
                        val = str(val)
                    elif isinstance(f, fields.Float):
                        val = str(val)
                    elif isinstance(f, fields.Char):
                        pass
                    elif isinstance(f, fields.File):
                        pass
                    elif isinstance(f, fields.Boolean):
                        val="1" if val else "0"
                    else:
                        raise Exception("Multicompany field not yet implemented: %s" % n)
                db.execute("INSERT INTO field_value (company_id,model,field,record_id,value) VALUES (%s,%s,%s,%s,%s)",
                           company_id, self._name, n, new_id, val)
        for n in vals:
            if n not in self._fields:
                continue
            f = self._fields[n]
            if isinstance(f, fields.One2Many):
                mr = get_model(f.relation)
                ops = vals[n]
                for op in ops:
                    if op[0] == "create":
                        vals_ = op[1].copy()
                        rf = mr.get_field(f.relfield)
                        if isinstance(rf, fields.Many2One):
                            vals_[f.relfield] = new_id
                        elif isinstance(rf, fields.Reference):
                            vals_[f.relfield] = "%s,%d" % (self._name, new_id)
                        else:
                            raise Exception("Invalid relfield: %s" % f.relfield)
                        if f.multi_company:
                            vals_["company_id"] = access.get_active_company()
                        mr.create(vals_, context=context)
                    elif op[0] == "add":
                        mr.write(op[1], {f.relfield: new_id})
                    elif op[0] in ("delete", "delete_all"):
                        pass
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
            elif isinstance(f, fields.Many2Many):
                mr = get_model(f.relation)
                ops = vals[n]
                for op in ops:
                    if op[0] in ("set", "add"):
                        ids_ = op[1]
                        for id in ids_:
                            db.execute("INSERT INTO %s (%s,%s) VALUES (%%s,%%s)" %
                                       (f.reltable, f.relfield, f.relfield_other), new_id, id)
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
        custom_fields = [n for n in vals if n not in self._fields]
        if custom_fields:
            for n in custom_fields:
                val = utils.json_dumps(vals[n])
                db.execute("INSERT INTO field_value (model,field,record_id,value) VALUES (%s,%s,%s,%s)", self._name, n, new_id, val)
        self._check_key([new_id])
        self._check_constraints([new_id])
        self._changed([new_id], vals.keys())
        self.audit_log("create", {"id": new_id, "vals": vals})
        #self.trigger([new_id], "create")
        return new_id

    def _copy(self,ids,vals={},context={}):
        new_ids=[]
        for obj in self.browse(ids):
            create_vals={}
            for n,f in self._fields.items():
                if not f.store:
                    continue
                v=obj[n]
                if isinstance(f,fields.Many2One):
                    v=v.id if v else None
                elif isinstance(f,fields.Reference):
                    v="%s,%d"%(v._model,v.id) if v else None
                create_vals[n]=v
            create_vals.update(vals)
            pprint(create_vals)
            new_id=self.create(create_vals,context=context)
            new_ids.append(new_id)
        return new_ids

    def copy(self,ids,context={}): # XXX
        self._copy(ids,context=context)
        return {
            "flash": "%d record(s) copied"%len(ids),
        }

    def _expand_condition(self, condition, depth=0, context={}):
        #print("_expand_condition",self._name,condition)
        if depth>10:
            raise Exception("Invalid condition: %s"%condition)
        if isinstance(condition,bool):
            return condition
        if not isinstance(condition,list):
            raise Exception("Invalid condition: %s"%(condition,))
        if not condition:
            return []
        if isinstance(condition[0],str) and condition[0] not in ("and","or","not"):
            condition=[condition]
        new_condition = []
        for clause in condition:
            if isinstance(clause,(str,bool)): # XXX
                new_clause = clause
            else:
                if isinstance(clause,(list,tuple)) and len(clause) > 1 and isinstance(clause[0], str) and clause[0] not in ("or", "and", "not"):
                    new_clause = clause
                    n = clause[0]
                    if n.find(".") == -1:
                        f = self._fields.get(n)
                        if f and f.function_search:
                            ctx = f.function_context or {}
                            ctx.update(context)
                            f = getattr(self, f.function_search)
                            new_clause = f(clause, ctx)
                else:
                    new_clause = self._expand_condition(clause, depth=depth+1, context=context)
            new_condition.append(new_clause)
        return new_condition

    def _where_calc(self, condition, context={}, tbl_count=1):
        # print("_where_calc",condition)
        condition = self._expand_condition(condition, context=context)
        # print("exp_condition",condition)
        joins = []
        args = []

        def _where_calc_r(cond):
            if cond==True:
                return "true"
            if cond==False:
                return "false"
            if len(cond)>=1 and cond[0]=="not":
                res=_where_calc_r(cond[1])
                return "NOT ("+res+")"
            nonlocal args, tbl_count, joins
            cond_list = []
            and_list = []
            if len(cond) >= 1 and cond[0] in ("or", "and"):
                mode = cond[0]
                cond = cond[1:]
            else:
                mode = "and"
            for clause in cond:
                if not isinstance(clause,(str,int,bool)) and len(clause) >= 1 and isinstance(clause[0], str) and clause[0] not in ("or", "and", "not"):
                    if len(clause)!=3:
                        raise Exception("Invalid clause: %s"%clause)
                    field, op, val = clause
                    fnames = field.split(".")
                    m = self
                    col_tbl = "tbl0"
                    for fname in fnames[:-1]:
                        if fname in m._fields:
                            f = m._fields[fname]
                            mr = get_model(f.relation)
                            rtbl = "tbl%d" % tbl_count
                            tbl_count += 1
                            if isinstance(f, fields.Many2One):
                                joins.append("LEFT JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, rtbl, col_tbl, fname))
                            elif isinstance(f, fields.One2Many):
                                joins.append("LEFT JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, col_tbl, rtbl, f.relfield))
                            elif isinstance(f, fields.Many2Many):
                                joins.append("LEFT JOIN %s %s ON EXISTS (SELECT * FROM %s WHERE %s=%s.id AND %s=%s.id)" %
                                             (mr._table, rtbl, f.reltable, f.relfield, col_tbl, f.relfield_other, rtbl))
                            else:
                                raise Exception("Invalid search condition: %s" % condition)
                            m = mr
                            col_tbl = rtbl
                        else:
                            raise Exception("Field not found: %s of %s"%(fname,m._name))
                    end_field = fnames[-1]
                    if end_field != "id":
                        if end_field in m._fields:
                            f=m._fields[end_field]
                            if isinstance(f, fields.Many2One):
                                m = get_model(f.relation)
                            elif isinstance(f, fields.One2Many):
                                mr = get_model(f.relation)
                                rtbl = "tbl%d" % tbl_count
                                tbl_count += 1
                                joins.append("JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, col_tbl, rtbl, f.relfield))
                                m = mr
                                col_tbl = rtbl
                                end_field = "id"
                            elif isinstance(f, fields.Many2Many):
                                mr = get_model(f.relation)
                                rtbl = "tbl%d" % tbl_count
                                tbl_count += 1
                                joins.append("JOIN %s %s ON EXISTS (SELECT * FROM %s WHERE %s=%s.id AND %s=%s.id)" %
                                             (mr._table, rtbl, f.reltable, f.relfield, col_tbl, f.relfield_other, rtbl))
                                m = mr
                                col_tbl = rtbl
                                end_field = "id"
                        else:
                            rtbl = "tbl%d" % tbl_count
                            tbl_count += 1
                            joins.append("LEFT JOIN field_value %s ON (%s.model='%s' AND %s.record_id=tbl0.id AND %s.field='%s')" % (rtbl, rtbl, m._name, rtbl, rtbl, end_field)) # XXX: injection
                            col_tbl=rtbl
                            end_field="value"
                            val = utils.json_dumps(val)

                    col = col_tbl + "." + end_field
                    if op == "=" and val is None:
                        cond_list.append("%s IS NULL" % col)
                    elif op == "!=" and val is None:
                        cond_list.append("%s IS NOT NULL" % col)
                    elif op == "~=":
                        cond_list.append("(%%s IS NULL OR %s=%%s)" % (col,))
                        args+=[val,val]
                    else:
                        if op in ("=", "!=", "<", ">", "<=", ">="):
                            cond_list.append("%s %s %%s" % (col, op))
                            args.append(val)
                        elif op in ("in", "not in"):
                            if val:
                                cond_list.append(col + " " + op + " (" + ",".join(["%s"] * len(val)) + ")")
                                args += val
                            else:
                                if op == "in":
                                    cond_list.append("false")
                                elif op == "not in":
                                    cond_list.append("true")
                        elif op=="between":
                            if val[0]:
                                cond_list.append("%s >= %%s" % col)
                                args.append(val[0])
                            if val[1]:
                                cond_list.append("%s <= %%s" % col)
                                args.append(val[1])
                        elif op in ("like", "ilike"):
                            cond_list.append("%s %s %%s" % (col, op))
                            args.append("%" + val + "%")
                        elif op in ("=like", "=ilike"):
                            cond_list.append("%s %s %%s" % (col, op[1:]))
                            args.append(val)
                        elif op=="not ilike":
                            cond_list.append("%s %s %%s" % (col, op))
                            args.append("%" + val + "%")
                        elif op == "child_of":
                            if isinstance(val, str):  # XXX
                                cond_list.append("%s IN (WITH RECURSIVE q AS (SELECT id FROM %s WHERE %s=%%s UNION ALL SELECT h.id FROM q JOIN %s h ON h.parent_id=q.id) SELECT id FROM q)" % (
                                    col, m._table, m._name_field or "name", m._table))
                                args.append(val)
                            else:
                                if isinstance(val, int):
                                    val = [val]
                                if val:
                                    cond_list.append("%s IN (WITH RECURSIVE q AS (SELECT id FROM %s WHERE id IN %%s UNION ALL SELECT h.id FROM q JOIN %s h ON h.parent_id=q.id) SELECT id FROM q)" % (
                                        col, m._table, m._table))
                                    args.append(tuple(val))
                                else:
                                    cond_list.append("FALSE")
                        elif op == "not child_of":
                            if isinstance(val, str):  # XXX
                                cond_list.append("%s NOT IN (WITH RECURSIVE q AS (SELECT id FROM %s WHERE %s=%%s UNION ALL SELECT h.id FROM q JOIN %s h ON h.parent_id=q.id) SELECT id FROM q)" % (
                                    col, m._table, m._name_field or "name", m._table))
                                args.append(val)
                            else:
                                if isinstance(val, int):
                                    val = [val]
                                if val:
                                    cond_list.append("%s NOT IN (WITH RECURSIVE q AS (SELECT id FROM %s WHERE id IN %%s UNION ALL SELECT h.id FROM q JOIN %s h ON h.parent_id=q.id) SELECT id FROM q)" % (
                                        col, m._table, m._table))
                                    args.append(tuple(val))
                                else:
                                    cond_list.append("TRUE")
                        elif op == "child_of<":
                            cond_list.append("%s IN (WITH RECURSIVE q AS (SELECT id FROM %s WHERE id=%%s UNION ALL SELECT h.id FROM q JOIN %s h ON h.parent_id=q.id) SELECT id FROM q WHERE id!=%%s)" % (
                                col, m._table, m._table))
                            args += [val, val]
                        elif op == "parent_of":
                            if isinstance(val, int):
                                val = [val]
                            if val:
                                cond_list.append("%s IN (WITH RECURSIVE q AS (SELECT id,parent_id FROM %s WHERE id IN %%s UNION ALL SELECT h.id,h.parent_id FROM q JOIN %s h ON h.id=q.parent_id) SELECT id FROM q)" % (
                                    col, m._table, m._table))
                                args.append(tuple(val))
                            else:
                                cond_list.append("FALSE")
                        else:
                            raise Exception("Invalid condition operator: %s" % op)
                else:
                    cond = _where_calc_r(clause)
                    cond_list.append(cond)
            if mode == "and":
                cond = " AND ".join(cond_list) if cond_list else "true"
            elif mode == "or":
                cond = "(" + (" OR ".join(cond_list) if cond_list else "false") + ")"
            if and_list:
                cond += " AND " + " AND ".join(and_list)
            return "("+cond+")"
        cond = _where_calc_r(condition)
        # print("=>",joins,cond,args)
        return [joins, cond, args]

    def _order_calc(self, order):
        joins = []
        clauses = []
        tbl_count = 1
        if order:
            for comp in order.split(","):
                comp = comp.strip()
                res = comp.split(" ")
                if len(res) > 1:
                    odir = res[1]
                else:
                    odir = "ASC"
                #odir+=" NULLS LAST" # XXX: breaks index
                path = res[0]
                m = self
                tbl = "tbl0"
                def _add_join(col):
                    f = m._fields[col]
                    if isinstance(f, fields.Many2One):
                        mr = get_model(f.relation)
                        rtbl = "otbl%d" % tbl_count
                        tbl_count += 1
                        joins.append("LEFT JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, rtbl, tbl, col))
                        m = mr
                        tbl = rtbl
                    else:
                        raise Exception("Invalid field %s in order clause %s" % (col, comp))
                cols = path.split(".")
                for col in cols[:-1]:
                    f = m.get_field(col)
                    mr = get_model(f.relation)
                    rtbl = "otbl%d" % tbl_count
                    tbl_count += 1
                    joins.append("LEFT JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, rtbl, tbl, col))
                    m = mr
                    tbl = rtbl
                col = cols[-1]
                f = m._fields.get(col)
                if f and not f.store and not f.sql_function:
                    path = f.function_context.get("path")  # XXX
                    if not path:
                        raise Exception("Invalid field %s in order clause %s" % (col, comp))
                    cols = path.split(".")
                    for col in cols[:-1]:
                        f = m.get_field(col)
                        mr = get_model(f.relation)
                        rtbl = "otbl%d" % tbl_count
                        tbl_count += 1
                        joins.append("LEFT JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, rtbl, tbl, col))
                        m = mr
                        tbl = rtbl
                    col = cols[-1]
                    f = m._fields.get(col)
                if isinstance(f, fields.Many2One):
                    mr = get_model(f.relation)
                    rtbl = "otbl%d" % tbl_count
                    tbl_count += 1
                    joins.append("LEFT JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, rtbl, tbl, col))
                    m = mr
                    tbl = rtbl
                    col = m._name_field or "name"
                if f:
                    if f.sql_function:  # XXX
                        clause = "\"%s\" %s" % (path, odir)
                    else:
                        clause = "%s.%s %s" % (tbl, col, odir)
                else:
                    if path=="id":
                        clause = "%s.%s %s" % (tbl, col, odir)
                    elif path=="random()":
                        clause = "%s %s" % (path, odir)
                    else:
                        raise Exception("Invalid field: %s"%path)
                clauses.append(clause)
        #print("_order_calc(%s: %s) -> %s %s"%(self._name,order,joins,clauses))
        return (joins, clauses)

    def _check_condition_has_active(self, condition):
        def _check_r(cond):
            #print("XXX _check_r",cond)
            for clause in cond:
                if not isinstance(clause, (tuple, list)):
                    continue  # XXX: [["id","in",[1,2,3]]]
                if len(clause) >= 1 and isinstance(clause[0], str) and clause[0] not in ("or", "and"):
                    if clause[0] == "active":
                        return True
                else:
                    if _check_r(clause):
                        return True
            return False
        return _check_r(condition)

    def get_filter(self,access_type,context={}):
        filter_cond=access.get_filter(self._name,access_type)
        return filter_cond

    def check_model_access(self,access_type,ids,context={}):
        return access.check_permission(self._name, access_type, ids)

    def filter_fields(self,ids,field_names,access_type,context={}):
        return field_names

    def get_filter_private(self,access_type,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return False
        if user_id==1:
            return []
        prof_code=access.get_active_profile_code()
        if prof_code=="ADMIN":
            return []
        if self._name=="base.user":
            cond=[["id","=",user_id]]
        else:
            cond=[["user_id","=",user_id]]
        return cond

    def check_model_access_private(self,access_type,ids,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return False
        if user_id==1:
            return True
        prof_code=access.get_active_profile_code()
        if prof_code=="ADMIN":
            return True
        if self._name=="base.user":
            cond=[["id","in",ids],["id","!=",user_id]]
        else:
            cond=[["id","in",ids],["user_id","!=",user_id]]
        access.set_active_user(1)
        try:
            res=self.search(cond)
        finally:
            access.set_active_user(user_id)
        if res:
            return False
        return True

    def search(self, condition, order=None, limit=None, offset=None, count=False, child_condition=None, context={}):
        """Search records

        Args:
            condition (list of clauses): expression to filter records

            order (str): order used to sort records

            limit (int): maximum number of records to return

            offset (int): number of records to skip

            count (bool): flag to return total number of records

        Result:
            if count is false:
                list of record ids 
            if count is true:
                (list of record ids, total number of results)

        Condition expression syntax:
            The condition parameter is a list of clauses, each clause of the form [<FIELD>,<OPERATOR>,<VALUE>] where:

            - <FIELD> is a field name or path
            - <OPERATOR> is a comparison operator
            - <VALUE> is a constant value.

            List of operators:
                - =: equals

                - !=: not equals

                - in: included in

                - <: smaller than

                - >: greater than

                - <=: smaller or equal than

                - >=: greater or equal than

                - between: combines >= and <=

                - like: check if pattern is included in string
                
                - ilike: check if pattern is included in string (case insensitive)

                - like=: check if pattern is included in string (match start and end of string)
                
                - ilike: check if pattern is included in string (case insensitive, match start and end of string)

                - child_of: check if record is a descendant in parent hierarchy

                - child_of<: check if record is a descendant in parent hierarchy (exclude record itself)

                - parent_of: check if record is a parent in hierarchy

            Examples:

            - [["last_name","=","Tan"],["gender","=","F"]]

                - Meaning: find records for which "last_name" is "Tan" AND "gender" is "F"

            - [["firm_id.phone","=","12345678"]]

                - Meaning: find records for which the related firm's phone number is "12345678"

            - ["or",["first_name","=","Cherilyn"],["last_name","=","Tan"]]

                - Meaning: find records for which "first_name" is "Tan" OR "last_name" is "Tan"

            - [["first_name","in",["Alice","Bob"]]]

                - Meaning: find records for which "first_name" is "Alice" OR "Bob"

            - [["gender","=","F"],["or",["first_name","=","Alice"],["first_name","=","Bob"]]]

                - Meaning: find records for which "gender" is "F" AND ("first_name" is "Alice" OR "last_name" is "Bob")

            - [["first_name","ilike","ily"]]

                - Meaning: find records for which "first_name" includes the substring "ily" (case insensitive)

            - [["date","between",["2017-01-01","2017-12-31"]]]

                - Meaning: find records for which "date" is greater or equal than "2017-01-01" and lesser or equal than "2017-12-31"

                - Note: this would return the same result as [["date",">=","2017-01-01"],["date","<=","2017-12-31"]]
        """
        #print(">>> SEARCH",self._name,condition)
        t0=time.time()
        q=None
        q_c=None
        try:
            if child_condition:
                child_ids = self.search(child_condition, context=context)
                res = self.search([condition, ["id", "parent_of", child_ids]], order=order,
                                  limit=limit, offset=offset, count=count, context=context)
                return res
            cond = [condition]
            if "active" in self._fields and context.get("active_test") != False:
                if not self._check_condition_has_active(condition): # XXX
                    print("ACTIVE",condition)
                    cond.append(["active", "=", True])
            filter_cond = self.get_filter("search",context=context)
            if filter_cond:
                cond.append(filter_cond)
            if self._name=="aln.job":
                print("L"*80)
                print("L"*80)
                print("L"*80)
                print("=> orig cond",cond)
            cond=utils.clean_cond(cond)
            if self._name=="aln.job":
                print("=> clean cond",cond)
            try:
                cond=utils.cond_distrib_or(cond)
            except Exception as e:
                raise Exception("Invalid condition: %s"%cond)
            if isinstance(cond,list) and cond and cond[0]=="or":
                u_conds=[[c] for c in cond[1:]]
            else:
                u_conds=[cond]
            db = database.get_connection()
            ord_joins, ord_clauses = self._order_calc(order or self._order or "id")
            ord_fields=[c.split(" ")[0] for c in ord_clauses]
            u_qs=[]
            u_args=[]
            for u_cond in u_conds:
                joins, q_cond, w_args = self._where_calc(u_cond, context=context)
                u_args+=w_args
                # print("CONDITION:",cond)
                q = "SELECT tbl0.id"
                for n in ord_fields:
                    q+=", "+n+" AS "+n.replace(".","_").replace("(","").replace(")","") # XXX
                q+=" FROM " + self._table + " tbl0"
                if joins:
                    q += " " + " ".join(joins)
                if ord_joins:
                    q += " " + " ".join(ord_joins)
                if q_cond:
                    q += " WHERE (" + q_cond + ")"
                if ord_clauses:
                    q += " ORDER BY " + ",".join(ord_clauses)
                if not context.get("no_limit"):
                    q+=" LIMIT 10000" # XXX: speed chp docs
                u_qs.append(q)
            q="SELECT DISTINCT id" # XXX: distinct not needed?
            for n in ord_fields:
                q+=", "+n.replace(".","_").replace("(","").replace(")","") # XXX
            q+=" FROM ("
            q+=" UNION ".join("("+u_q+")" for u_q in u_qs)
            q+=") AS temp"
            if ord_clauses:
                q += " ORDER BY " + ",".join([c.replace(".","_").replace("(","").replace(")","") for c in ord_clauses]) # XXX
            args=u_args[:]
            if offset is not None:
                q += " OFFSET %s"
                args.append(offset)
            if limit is not None:
                q += " LIMIT %s"
                args.append(limit)
            #if self._name=="aln.job": # XXX
            #    q_=db.fmt_query(q,*args)
            #    open("/tmp/search.log","a").write("%s %s %s %s\n"%(time.strftime("%Y-%m-%d %H:%M:%S"),cond,u_conds,q_))
            res = db.query(q, *args)
            ids=[r.id for r in res]
            if not count:
                return ids
            q_c = "SELECT COUNT(*) AS total FROM ("
            q_c+=" UNION ".join("("+u_q+")" for u_q in u_qs)
            q_c+=") AS temp"
            res = db.get(q_c, *u_args)
            #print("<<< SEARCH",self._name,condition)
            return (ids, res.total)
        finally:
            t1=time.time()
            dt=t1-t0
            if dt>1:
            #if self._name=="aln.doc":
                t=time.strftime("%Y-%m-%dT%H:%M:%S")
                msg="---\n[%s] dt=%s model=%s cond=%s\n    q=%s\n    qc=%s\n"%(t,dt,self._name,cond,db.fmt_query(q,*args),db.fmt_query(q_c,*u_args))
                open("/tmp/slow_search.log","a").write(msg)

    def record_history(self,ids,field_names,context={}):
        user_id=access.get_active_user()
        records=self.read(ids,field_names,load_m2o=False,context={})
        db=database.get_connection()
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        for r in records:
            res=db.get("INSERT INTO record_history (time,model,record_id,user_id) VALUES (%s,%s,%s,%s) RETURNING id",t,self._name,r["id"],user_id)
            hist_id=res.id
            for n,val in r.items():
                if n=="id":
                    continue
                if n in ("write_uid","write_time"):
                    continue
                print("n",n,"val",val)
                if val is None:
                    continue
                f = self._fields[n]
                if isinstance(f, fields.Many2One):
                    val = str(val)
                elif isinstance(f, fields.Float):
                    val = str(val)
                elif isinstance(f, fields.Integer):
                    val = str(val)
                elif isinstance(f, fields.Decimal):
                    val = str(val)
                elif isinstance(f, fields.Char):
                    pass
                elif isinstance(f, fields.Text):
                    pass
                elif isinstance(f, fields.Selection):
                    pass
                elif isinstance(f, fields.File):
                    pass
                elif isinstance(f, fields.Boolean):
                    val="1" if val else "0"
                else:
                    continue
                db.execute("INSERT INTO field_value (history_id,model,record_id,field,value) VALUES (%s,%s,%s,%s,%s)",hist_id,self._name,r["id"],n,val)

    def write(self, ids, vals, check_time=False, context={}):
        """Update records

        Args:
            ids (list of int): record ids to update

            vals (dict of str): field values

        Results:
            None
        """
        #print(">>> WRITE",self._name,ids,vals)
        if not ids or not vals:
            return
        ids=[int(i) for i in ids]
        if not self.check_model_access("write",ids,context=context):
            user_id=access.get_active_user()
            raise Exception("Permission denied (user_id=%s model=%s access=write ids=%s)"%(user_id,self._name,ids))
        # XXX
        #field_names=list(vals.keys())
        #field_names = self.filter_fields(ids,field_names,"write")
        if not vals.get("write_time"):
            vals["write_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if not vals.get("write_uid"):
            vals["write_uid"] = access.get_active_user()
        if vals.get("create_uid") and isinstance(vals["create_uid"],list): # XXX
            vals["create_uid"]=vals["create_uid"][0]
        for n, v in list(vals.items()):
            if n not in self._fields:
                continue
            f = self._fields[n]
            if isinstance(f, fields.Json):
                if not isinstance(v, str):
                    vals[n] = utils.json_dumps(v)  # XXX
            elif isinstance(f, fields.Char):
                if f.password and v:
                    vals[n] = utils.encrypt_password(v)
        db = database.get_connection()
        if check_time:
            q = "SELECT MAX(write_time) AS write_time FROM " + self._table + \
                " WHERE id IN (" + ",".join([str(int(id)) for id in ids]) + ")"

            res = db.get(q)
            write_time = res.write_time
            if write_time and write_time > check_time:  # TODO: check == case
                raise Exception("Failed to write record (concurrent access), please reload the page.")
        store_fields = [n for n in vals if n in self._fields and self._fields[n].store]
        locale = netforce.locale.get_active_locale()
        trans_fields = [n for n in store_fields if self._fields[n].translate]
        store_fields = list(set(store_fields) - set(trans_fields))
        multico_fields = [n for n in store_fields if self._fields[n].multi_company]
        if multico_fields:
            store_fields = list(set(store_fields) - set(multico_fields))
        if self._history:
            self.record_history(ids,store_fields,context=context)
        cols = store_fields[:]
        if cols:
            q = "UPDATE " + self._table
            q += " SET " + ",".join(['"%s"=%%s' % col for col in cols])
            q += " WHERE id IN (" + ",".join([str(int(id)) for id in ids]) + ")"
            args = [vals[n] for n in store_fields]
            db.execute(q, *args)
        if trans_fields:
            res = db.query("SELECT field,rec_id,lang FROM translation_field WHERE model=%s AND field IN %s AND rec_id IN %s",
                           self._name, tuple(trans_fields), tuple(ids))
            trans_ids = {}
            for r in res:
                trans_ids.setdefault((r.field,r.lang), []).append(r.rec_id)
            for n in trans_fields:
                val = vals[n]
                if isinstance(val,dict):
                    trans_vals=val
                else:
                    trans_vals={locale or "en_US":val}
                for lang,val in trans_vals.items():
                    if lang=="en_US":
                        db.execute("UPDATE "+self._table+" SET \""+n+"\"=%s WHERE id in %s", val, tuple(ids))
                    else:
                        update_ids = trans_ids.get((n,lang),[])
                        if update_ids:
                            db.execute("UPDATE translation_field SET translation=%s WHERE lang=%s AND model=%s AND field=%s AND rec_id IN %s", val, lang, self._name, n, tuple(update_ids))
                        new_ids = list(set(ids) - set(update_ids))
                        for rec_id in new_ids:
                            db.execute(
                                "INSERT INTO translation_field (lang,model,field,rec_id,translation) VALUES (%s,%s,%s,%s,%s)", lang, self._name, n, rec_id, val)
        if multico_fields:
            company_id = access.get_active_company()
            res = db.query("SELECT id,field,record_id FROM field_value WHERE company_id=%s AND model=%s AND field IN %s AND record_id in %s",
                           company_id, self._name, tuple(multico_fields), tuple(ids))
            val_ids = {}
            rec_ids = {}
            for r in res:
                val_ids.setdefault(r.field, []).append(r.id)
                rec_ids.setdefault(r.field, []).append(r.record_id)
            for n in multico_fields:
                val = vals[n]
                if val is not None:
                    f = self._fields[n]
                    if isinstance(f, fields.Many2One):
                        val = str(val)
                    elif isinstance(f, fields.Float):
                        val = str(val)
                    elif isinstance(f, fields.Char):
                        pass
                    elif isinstance(f, fields.File):
                        pass
                    elif isinstance(f, fields.Boolean):
                        val="1" if val else "0"
                    else:
                        raise Exception("Multicompany field not yet implemented: %s" % n)
                ids2 = val_ids.get(n)
                if ids2:
                    db.execute("UPDATE field_value SET value=%s WHERE id in %s", val, tuple(ids2))
                ids3 = rec_ids.get(n, [])
                ids4 = list(set(ids) - set(ids3))
                for rec_id in ids4:
                    db.execute("INSERT INTO field_value (company_id,model,field,record_id,value) VALUES (%s,%s,%s,%s,%s)",
                               company_id, self._name, n, rec_id, val)
        custom_fields = [n for n in vals if n not in self._fields]
        if custom_fields:
            self.load_custom_fields()
            res = db.query("SELECT id,field,record_id FROM field_value WHERE model=%s AND field IN %s AND record_id in %s", self._name, tuple(custom_fields), tuple(ids))
            val_ids = {}
            rec_ids = {}
            for r in res:
                val_ids.setdefault(r.field, []).append(r.id)
                rec_ids.setdefault(r.field, []).append(r.record_id)
            for n in custom_fields:
                f=self._custom_fields.get(n)
                if not f:
                    raise Exception("Invalid custom field: %s"%n)
                val=vals[n]
                if isinstance(f,fields.Many2Many):
                    val=val[0][1]
                val = utils.json_dumps(val)
                ids2 = val_ids.get(n)
                if ids2:
                    db.execute("UPDATE field_value SET value=%s WHERE id in %s", val, tuple(ids2))
                ids3 = rec_ids.get(n, [])
                ids4 = list(set(ids) - set(ids3))
                for rec_id in ids4:
                    db.execute("INSERT INTO field_value (model,field,record_id,value) VALUES (%s,%s,%s,%s)", self._name, n, rec_id, val)
        for n in vals:
            if n not in self._fields:
                continue
            f = self._fields[n]
            if f.function_write:
                continue
            if isinstance(f, fields.One2Many):
                mr = get_model(f.relation)
                rf = mr.get_field(f.relfield)
                ops = vals[n]
                for op in ops:
                    if op[0] == "create":
                        vals_ = op[1]
                        for id in ids:
                            if isinstance(rf, fields.Many2One):
                                vals_[f.relfield] = id
                            elif isinstance(rf, fields.Reference):
                                vals_[f.relfield] = "%s,%d" % (self._name, id)
                            else:
                                raise Exception("Invalid relfield: %s" % f.relfield)
                            if f.multi_company:
                                vals_["company_id"] = access.get_active_company()
                            mr.create(op[1])
                    elif op[0] == "write":
                        mr.write(op[1], op[2])
                    elif op[0] == "delete":
                        mr.delete(op[1])
                    elif op[0] == "delete_all":
                        if isinstance(rf, fields.Many2One):
                            ids2 = mr.search([[f.relfield, "in", ids]])
                        elif isinstance(rf, fields.Reference):
                            rel_ids = ["%s,%d" % (self._name, id) for id in ids]
                            ids2 = mr.search([[f.relfield, "in", rel_ids]])
                        else:
                            raise Exception("Invalid relfield: %s" % f.relfield)
                        mr.delete(ids2)
                    elif op[0] == "add":
                        mr.write(op[1], {f.relfield: ids[0]})
                    elif op[0] == "remove":
                        mr.write(op[1], {f.relfield: None})
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
            elif isinstance(f, fields.Many2Many):
                mr = get_model(f.relation)
                ops = vals[n]
                for op in ops:
                    if op[0] == "add":
                        ids_ = op[1]
                        for id1 in ids:
                            for id2 in ids_:
                                db.execute("INSERT INTO %s (%s,%s) VALUES (%%s,%%s)" %
                                           (f.reltable, f.relfield, f.relfield_other), id1, id2)
                    elif op[0] == "remove":
                        ids_ = op[1]
                        db.execute("DELETE FROM %s WHERE %s IN (%s) AND %s IN (%s)" % (
                            f.reltable, f.relfield, ",".join([str(int(x)) for x in ids]), f.relfield_other, ",".join([str(int(x)) for x in ids_])))
                    elif op[0] == "set":
                        ids_ = op[1]
                        db.execute("DELETE FROM %s WHERE %s IN (%s)" %
                                   (f.reltable, f.relfield, ",".join([str(int(x)) for x in ids])))
                        for id1 in ids:
                            for id2 in ids_:
                                db.execute("INSERT INTO %s (%s,%s) VALUES (%%s,%%s)" %
                                           (f.reltable, f.relfield, f.relfield_other), id1, id2)
        for n in vals:
            if n not in self._fields:
                continue
            f = self._fields[n]
            if not f.function_write:
                continue
            func = getattr(self, f.function_write)
            func(ids, n, vals[n], context=context)
        self._check_key(ids)
        self._check_constraints(ids)
        self._changed(ids, vals.keys())
        self.audit_log("write", {"ids": ids, "vals": vals})
        #self.trigger(ids, "write")

    def delete(self, ids, context={}):
        """Delete records

        Args:
            ids (list of int): record ids to delete

        Result:
            None
        """
        if not ids:
            return
        ids=[int(i) for i in ids]
        if not self.check_model_access("delete",ids,context=context):
            user_id=access.get_active_user()
            raise Exception("Permission denied (user_id=%s model=%s access=delete ids=%s)"%(user_id,self._name,ids))
        #self.trigger(ids, "delete")
        q = "DELETE FROM " + self._table + " WHERE id IN (" + ",".join([str(int(id)) for id in ids]) + ")"
        db = database.get_connection()
        try:
            db.execute(q)
            self.audit_log("delete", {"ids": ids})
        except psycopg2.Error as e:
            code = e.pgcode
            db.rollback()
            if code == "23502": # not_null_violation
                with database.Transaction():
                    refs={}
                    user_id=access.get_active_user()
                    access.set_active_user(1)
                    try:
                        for model,m in models.items():
                            for n,f in m._fields.items():
                                if isinstance(f,fields.Many2One) and f.relation==self._name and f.required and f.on_delete!="cascade":
                                    cond=[[n,"in",ids]]
                                    res=m.search(cond,context={"active_test":False})
                                    if res:
                                        rids=refs.setdefault(model,[])
                                        rids+=res
                    finally:
                        access.set_active_user(user_id)
                    msg="The items to delete are still being referenced by the following records:"
                    if refs:
                        for model,rids in sorted(refs.items()):
                            rids=sorted(list(set(rids)))
                            m=get_model(model)
                            try:
                                names=[r[1] or "" for r in m.name_get(rids)]
                            except:
                                names=[str(x) for x in rids]
                            msg+="\n- %s: %s"%(m._string or m._name,", ".join(names))
                raise Exception(msg)

    def read(self, ids, field_names=None, load_m2o=True, load_all_trans=False, get_time=False, context={}):
        """Read records

        Args:
            ids (list of int): record ids to read

            field_names (list of str): field names to read

        Result:
            (list of dict): record values
        """
        load_cust=False
        for n in field_names or []:
            if n not in self._fields:
                load_cust=True
                break
        if load_cust:
            self.load_custom_fields()
        if not ids:
            return []
        ids=[int(i) for i in ids]
        # XXX FIXME KFF bug: TG, bow, SO list
        #if not self.check_model_access("read",ids,context=context):
        #    user_id=access.get_active_user()
        #    raise Exception("Permission denied (user_id=%s model=%s access=read ids=%s)"%(user_id,self._name,ids))
        if not field_names:
            field_names = [n for n, f in self._fields.items() if not isinstance(
                f, (fields.One2Many, fields.Many2Many)) and not (not f.store and not f.function)]
        field_names = list(set(field_names)) # XXX
        field_names = self.filter_fields(ids,field_names,"read")
        cols = ["id"] + [n for n in field_names if n in self._fields and self._fields[n].store]
        q = "SELECT " + ",".join(['"%s"' % col for col in cols]) + " FROM " + self._table
        q += " WHERE id IN (" + ",".join([str(int(id)) for id in ids]) + ")"
        db = database.get_connection()
        res = db.query(q)
        id_res = {}
        for r in res:
            id_res[r["id"]] = r
        for id in ids:
            if id not in id_res:
                raise Exception("Invalid read ID %s (%s)" % (id, self._name))
        res = [dict(id_res[id]) for id in ids]
        multi_funcs = {}
        for n in field_names:
            f = self._fields.get(n)
            if not f:
                f=self._custom_fields.get(n)
                if not f:
                    continue
            if not f.function or f.store:
                continue
            if f.function_multi:
                multi_funcs[f.function] = True
            else:
                #func = getattr(self, f.function)
                ctx = context.copy()
                ctx.update(f.function_context)
                #print(">>> FUNC",f.function,n)
                #vals = func(ids, context=ctx)
                vals = self.exec_func(f.function,[ids],{"context":ctx})
                #print("<<< FUNC",f.function,n)
                for r in res:
                    #r[n] = vals.get(r["id"])
                    if str(r["id"]) in vals:
                        r[n] = vals.get(str(r["id"]))
                    else:
                        r[n] = vals.get(r["id"])
        for func_name in multi_funcs:
            func = getattr(self, func_name)
            if func:
                #print(">>> FUNC_MULTI",func_name)
                vals = func(ids, context=context)
                #print("<<< FUNC_MULTI",func_name)
                for r in res:
                    r.update(vals[r["id"]])
        multico_fields = [n for n in field_names if n in self._fields and self._fields[n].multi_company and self._fields[n].store]
        if multico_fields:
            company_id = access.get_active_company()
            res2 = db.query("SELECT field,record_id,value FROM field_value WHERE model=%s AND field IN %s AND record_id IN %s AND company_id=%s", self._name, tuple(
                multico_fields), tuple(ids), company_id)
            vals = {}
            for r in res2:
                vals[(r.record_id, r.field)] = r.value
            for n in multico_fields:
                for r in res:
                    k = (r["id"], n)
                    r[n]=vals.get(k)
                f = self._fields[n]
                if isinstance(f, fields.Many2One):
                    r_ids=[]
                    for r in res:
                        v = r[n]
                        if v is not None and v.isnumeric():
                        #if v is not None:
                            r_ids.append(int(v))
                    r_ids=list(set(r_ids))
                    mr=get_model(f.relation)
                    r_ids2=mr.search([["id","in",r_ids]],context={"active_test":False})
                    r_ids2_set=set(r_ids2)
                    for r in res:
                        v = r[n]
                        if v is not None and v.isnumeric():
                        #if v is not None:
                            v=int(v)
                            if v in r_ids2_set:
                                r[n]=v
                            else:
                                r[n]=None
                elif isinstance(f, fields.Float):
                    for r in res:
                        k = (r["id"], n)
                        if k not in vals:
                            continue
                        v = vals[k]
                        if v is not None and v.isnumeric():
                        #if v is not None:
                            r[n] = float(v)
                elif isinstance(f, fields.Char):
                    pass
                elif isinstance(f, fields.File):
                    pass
                elif isinstance(f, fields.Boolean):
                    for r in res:
                        k = (r["id"], n)
                        if k not in vals:
                            continue
                        v = vals[k]
                        if v is not None and v.isnumeric():
                            r[n] = int(v)
                else:  # TODO: add more field types...
                    raise Exception("Multicompany field not yet implemented: %s" % n)
        for n in field_names:
            if n not in self._fields:
                continue
            f = self._fields[n]
            if not f.function:
                if isinstance(f, fields.One2Many):
                    mr = get_model(f.relation)
                    rf = mr._fields[f.relfield]
                    if isinstance(rf, fields.Reference):
                        cond = [(f.relfield, "in", ["%s,%d" % (self._name, id) for id in ids])]
                        if f.condition:
                            cond += f.condition
                        if f.multi_company:
                            cond += [("company_id", "=", access.get_active_company())]
                        ids2 = mr.search(cond, context=context)
                        res2 = mr.read(ids2, [f.relfield], load_m2o=False, context=context)
                        vals = {}
                        for r in res2:
                            vals.setdefault(r[f.relfield], []).append(r["id"])
                        for r in res:
                            r[n] = vals.get("%s,%d" % (self._name, r["id"]), [])
                    else:
                        # XXX: remove this optimization and use general case below?
                        if not f.operator or f.operator == "in":
                            cond = [(f.relfield, "in", ids)]
                            if f.condition:
                                cond += f.condition
                            if f.multi_company:
                                cond += [("company_id", "=", access.get_active_company())]
                            ids2 = mr.search(cond, order=f.order, context=context)
                            res2 = mr.read(ids2, [f.relfield], load_m2o=False, context=context)
                            vals = {}
                            for r in res2:
                                vals.setdefault(r[f.relfield], []).append(r["id"])
                            for r in res:
                                r[n] = vals.get(r["id"], [])
                        else:
                            vals = {}
                            for id in ids:
                                cond = [(f.relfield, f.operator, id)]
                                if f.condition:
                                    cond += f.condition
                                if f.multi_company:
                                    cond += [("company_id", "=", access.get_active_company())]
                                rids = mr.search(cond)
                                vals[id] = rids
                            for r in res:
                                r[n] = vals.get(r["id"], [])
                elif isinstance(f, fields.Many2Many):
                    res2 = db.query("SELECT %s,%s FROM %s WHERE %s in (%s)" % (
                        f.relfield, f.relfield_other, f.reltable, f.relfield, ",".join([str(int(x)) for x in ids])))
                    r_ids = [r[f.relfield_other] for r in res2]
                    if f.condition:
                        mr = get_model(f.relation)
                        cond=[["id","in",r_ids]]
                        cond.append(f.condition)
                        r_ids_cond = mr.search(cond) # TODO: make this more efficient
                    else:
                        r_ids_cond = r_ids
                    vals = {}
                    for r in res2:
                        if r[f.relfield_other] in r_ids_cond:
                            vals.setdefault(r[f.relfield], []).append(r[f.relfield_other])
                    for r in res:
                        r[n] = vals.get(r["id"], [])
                elif isinstance(f, fields.Json):
                    for r in res:
                        val = r[n]
                        if val:
                            r[n] = utils.json_loads(val)
            if isinstance(f, fields.Many2One) and load_m2o:
                mr = get_model(f.relation)
                ids2 = [r[n] for r in res if r[n]]
                ids2 = list(set(ids2))
                #ids2 = mr.search([["id", "in", ids2]], context={"active_test": False})  # for permissions
                res2 = mr.name_get(ids2)
                names = {}
                images = {}
                for r in res2:
                    names[r[0]] = r[1]
                    if len(r) >= 3:
                        images[r[0]] = r[2]
                for r in res:
                    id = r[n]
                    if id:
                        r[n] = [id, names.get(id, "Permission Denied"), images.get(id)]
            elif isinstance(f, fields.Reference) and load_m2o:
                refs = {}
                for r in res:
                    v = r[n]
                    if v and "," in v:
                        r_model, r_id = v.split(",")
                        r_id = int(r_id)
                        refs.setdefault(r_model, []).append(r_id)
                names = {}
                for r_model, r_ids in refs.items():
                    mr = get_model(r_model)
                    r_ids = list(set(r_ids))
                    r_ids2 = mr.search([["id", "in", r_ids]], context={"active_test": False})
                    res2 = mr.name_get(r_ids2)
                    for r in res2:
                        names[(r_model, r[0])] = r[1]
                for r in res:
                    v = r[n]
                    if v and "," in v:
                        r_model, r_id = v.split(",")
                        r_id = int(r_id)
                        if (r_model, r_id) in names:
                            r[n] = [v, names[(r_model, r_id)]]
                        else:
                            r[n] = None
            elif isinstance(f, fields.Char) and f.password:
                for r in res:
                    if r[n]:
                        r[n] = "****"
            elif n=="create_uid":
                mr = get_model("base.user")
                ids2 = [r[n] for r in res if r[n]]
                ids2 = list(set(ids2))
                ids2 = mr.search([["id", "in", ids2]], context={"active_test": False})
                res2 = mr.name_get(ids2)
                names = {}
                images = {}
                for r in res2:
                    names[r[0]] = r[1]
                for r in res:
                    id = r[n]
                    if id:
                        r[n] = [id, names.get(id, "Permission Denied"), images.get(id)]
        trans_fields = [n for n in field_names if n in self._fields and self._fields[n].translate]
        if trans_fields and not context.get("no_translate"):
            if load_all_trans:
                res2 = db.query("SELECT field,rec_id,lang,translation FROM translation_field WHERE model=%s AND field IN %s AND rec_id IN %s",
                                self._name, tuple(trans_fields), tuple(ids))
                trans = {}
                for r in res2:
                    k=(r.rec_id, r.field)
                    trans.setdefault(k,{})[r.lang]=r.translation
                for n in trans_fields:
                    for r in res:
                        vals={"en_US":r[n]}
                        other_vals=trans.get((r["id"],n),{})
                        vals.update(other_vals)
                        r[n]=vals
            else:
                locale = netforce.locale.get_active_locale()
                if locale and locale != "en_US":
                    res2 = db.query("SELECT field,rec_id,translation FROM translation_field WHERE lang=%s AND model=%s AND field IN %s AND rec_id IN %s",
                                    locale, self._name, tuple(trans_fields), tuple(ids))
                    trans = {}
                    for r in res2:
                        trans[(r.rec_id, r.field)] = r.translation
                    for n in trans_fields:
                        for r in res:
                            r[n] = trans.get((r["id"], n), r[n])

        custom_fields=[]
        for n in field_names:
            if n=="id":
                continue
            if n in self._fields:
                continue
            f=self._custom_fields.get(n)
            if f and f.function:
                continue
            custom_fields.append(n)
        if custom_fields:
            res2 = db.query("SELECT field,record_id,value FROM field_value WHERE model=%s AND field IN %s AND record_id IN %s", self._name, tuple(custom_fields), tuple(ids))
            vals = {}
            for r in res2:
                vals[(r.record_id, r.field)] = utils.json_loads(r.value)
            for n in custom_fields:
                for r in res:
                    k = (r["id"], n)
                    r[n]=vals.get(k)

        if get_time:
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            for r in res:
                r["read_time"] = t
        #print("<<< READ",self._name)
        return res

    def browse(self, ids, context={}):
        # print("Model.browse",self._name,ids)
        cache = {}
        if isinstance(ids, (int,str)):
            #netforce.utils.print_color("WARNING: calling browse with int is DEPRECATED (model=%s)"%self._name,"red")
            ids=int(ids)
            return BrowseRecord(self._name, ids, [ids], context=context, browse_cache=cache)
        else:
            ids=[int(i) for i in ids]
            return BrowseList(self._name, ids, ids, context=context, browse_cache=cache)

    def search_browse(self, condition, **kw):
        ids = self.search(condition, **kw)
        ctx = kw.get("context", {})
        return self.browse(ids, context=ctx)

    def search_read(self, condition, field_names=None, context={}, **kw):
        """Search and read records

        search_read combines the search and read methods.

        Args:
            condition (list of clauses): expression to filter records

            field_names (list of str): field names to read

            order (str): order used to sort records

            limit (int): maximum number of records to return

            offset (int): number of records to skip

            count (bool): flag to return total number of records

        Result:
            if count is false:
                list of record values
            if count is true:
                (list of record values, total number of results)
        """
        print("Model.search_read",self._name,condition,field_names)
        res = self.search(condition, context=context, **kw)
        if isinstance(res, tuple):
            ids, count = res
            data = self.read(ids, field_names, context=context)
            return data, count
        else:
            ids = res
            data = self.read(ids, field_names, context=context)
            return data

    def read_one(self,obj_id,*args,**kw):
        res=self.read([obj_id],*args,**kw)
        return res[0]

    def write_one(self,obj_id,*args,**kw):
        self.write([obj_id],*args,**kw)

    def delete_one(self,obj_id,*args,**kw):
        self.delete([obj_id],*args,**kw)

    def get(self, key_vals, context={}, require=False):
        if not self._key:
            raise Exception("Model %s has no key" % self._name)
        if isinstance(key_vals, str):
            cond = [(self._key[0], "=", key_vals)]
        else:
            cond = [(n, "=", key_vals[n]) for n in self._key]
        res = self.search(cond)
        if not res:
            if require:
                raise Exception("Record not found: %s / %s" % (self._name, key_vals))
            return None
        if len(res) > 1:
            raise Exception("Duplicate keys (model=%s, key=%s)" % (self._name, key_vals))
        return res[0]

    def get_by_code(self,code,context={}):
        code_field=self._code_field or "code"
        res=self.search([[code_field,"=",code]])
        if not res:
            return None
        return res[0]

    def merge(self, vals):
        vals_ = {}
        for n, v in vals.items():
            if n == "id":
                continue
            f = self.get_field(n)
            if isinstance(f, fields.Many2One) and isinstance(v, str):
                mr = get_model(f.relation)
                v_ = mr.get(v)
                if not v_:
                    raise Exception("Key not found %s on %s" % (v, mr._name))
            else:
                v_ = v
            vals_[n] = v_
        if vals.get("id"):
            ids = [vals["id"]]
        else:
            if self._key:
                cond = [(k, "=", vals_.get(k)) for k in self._key]
                ids = self.search(cond)
                if len(ids) > 1:
                    raise Exception("Duplicate keys: %s %s" % (self._name, cond))
            else:
                ids = None
        if ids:
            self.write(ids, vals_)
            id = ids[0]
        else:
            id = self.create(vals_)
        return id

    def get_meta(self, field_names=None, context={}):
        if not field_names:
            field_names = self._fields.keys()
        res = {}
        for n in field_names:
            f = self.get_field(n)
            vals = f.get_meta(context=context)
            res[n] = vals
        return res

    def function_store(self, ids, field_names=None, context={}):
        t0 = time.time()
        if not field_names:
            field_names = [n for n, f in self._fields.items() if f.function and f.store]
        funcs = []
        multi_funcs = {}
        for n in field_names:
            f = self._fields[n]
            if not f.function:
                raise Exception("Not a function field: %s.%s", self._name, n)
            if f.function_multi:
                prev_order = multi_funcs.get(f.function)
                if prev_order is not None:
                    multi_funcs[f.function] = min(f.function_order, prev_order)
                else:
                    multi_funcs[f.function] = f.function_order
            else:
                funcs.append((f.function_order, f.function, f.function_context, n))
        for func_name, order in multi_funcs.items():
            funcs.append((order, func_name, {}, None))  # TODO: context
        funcs.sort(key=lambda a: (a[0], a[1]))
        db = database.get_connection()
        for order, func_name, func_ctx, n in funcs:
            func = getattr(self, func_name)
            ctx = context.copy()
            ctx.update(func_ctx)
            res = func(ids, context=ctx)
            if n:
                q = "UPDATE " + self._table
                q += " SET \"%s\"=%%s" % n
                q += " WHERE id=%s"
                for id, val in res.items():
                    db.execute(q, val, id)
            else:
                for id, vals in res.items():
                    cols = [n for n in vals.keys() if n in field_names]
                    q = "UPDATE " + self._table
                    q += " SET " + ",".join(['"%s"=%%s' % col for col in cols])
                    q += " WHERE id=%s" % int(id)
                    args = [vals[col] for col in cols]
                    db.execute(q, *args)
        self._check_constraints(ids, context=context)
        t1 = time.time()
        dt = (t1 - t0) * 1000
        print("function_store", self._name, ids, field_names, "<<< %d ms" % dt)

    def _check_constraints(self, ids, context={}):
        for name in self._constraints:
            f = getattr(self, name, None)
            if not f or not hasattr(f, "__call__"):
                raise Exception("No such method %s in %s" % (name, self._name))
            f(ids)

    def _changed(self, ids, field_names):
        funcs = {}
        for n in field_names:
            if n not in self._fields:
                continue
            f = self._fields[n]
            if f.on_write:
                funcs.setdefault(f.on_write, []).append(n)
        for f, fields in funcs.items():
            func = getattr(self, f)
            func(ids)

    def name_get(self, ids, context={}):
        user_id=access.get_active_user()
        try:
            access.set_active_user(1)
            if not self.check_model_access("read",ids,context=context):
                return [(id, "Permission denied") for id in ids]
            f_name = self._name_field or "name"
            f_image = self._image_field or "image"
            if f_image in self._fields:
                show_image = True
                fields = [f_name, f_image]
            else:
                show_image = False
                fields = [f_name]
            res = self.read(ids, fields)
            if show_image:
                return [(r["id"], r[f_name], r[f_image]) for r in res]
            else:
                return [(r["id"], r[f_name]) for r in res]
        finally:
            access.set_active_user(user_id)

    def name_search(self, name, condition=None, limit=None, order=None, context={}):
        f = self._name_field or "name"
        if name:
            search_mode = context.get("search_mode")
            if search_mode == "suffix":
                cond = [[f, "=ilike", "%" + name]]
            elif search_mode == "prefix":
                cond = [[f, "=ilike", name + "%"]]
            else:
                cond = [[f, "ilike", name]]
        else:
            cond=[]
        if condition:
            cond = [cond, condition]
        ids = self.search(cond, limit=limit, context=context, order=order)
        return self.name_get(ids, context=context)

    def name_create(self, name, context={}):
        f = self._name_field or "name"
        vals = {f: name}
        return self.create(vals, context=context)

    def _get_related(self, ids, context={}):
        path = context.get("path")
        if not path:
            raise Exception("Missing path")
        fnames = path.split(".")
        vals = {}
        for obj in self.browse(ids):
            parent = obj
            parent_m=get_model(obj._model)
            for n in fnames[:-1]:
                f=parent_m._fields[n]
                if not isinstance(f,(fields.Many2One,fields.Reference)):
                    raise Exception("Invalid field path for model %s: %s"%(self._name,path))
                parent = parent[n]
                if not parent:
                    parent=None
                    break
                parent_m=get_model(parent._model)
            if not parent:
                val=None
            else:
                n=fnames[-1]
                val=parent[n]
                if n!="id":
                    f=parent_m._fields.get(n)
                    if not f:
                        val=None
                    else:
                        if isinstance(f,(fields.Many2One,fields.Reference)):
                            val = val.id
                        elif isinstance(f,(fields.One2Many,fields.Many2Many)):
                            val=[v.id for v in val]
                
            vals[obj.id] = val
        return vals

    def _search_related(self, clause, context={}):
        path = context.get("path")
        if not path:
            raise Exception("Missing path")
        return [path, clause[1], clause[2]]

    def export_data(self, ids, exp_fields, context={}):
        print("Model.export_data", ids)
        from netforce import tasks
        job_id=context.get("job_id")
        self.load_custom_fields()

        def _get_header(path, model=self._name, prefix=""):
            print("_get_header", path, model, prefix)
            m = get_model(model)
            res = path.partition(".")
            if not res[1]:
                if path == "id":
                    label = "Database ID"
                else:
                    if path in m._fields:
                        f = m._fields[path]
                    elif path in m._custom_fields:
                        f = m._custom_fields[path]
                    else:
                        raise Exception("Invalid field: %s"%path)
                    label = f.string
                return prefix + label.replace("/", "&#47;")
            n, _, path2 = res
            if n == "id":
                label = "Database ID"
            else:
                f = m._fields[n]
                label = f.string
            prefix += label.replace("/", "&#47;") + "/"
            return _get_header(path2, f.relation, prefix)
        out = StringIO()
        wr = csv.writer(out)
        headers = [_get_header(n) for n in exp_fields]
        wr.writerow(headers)

        def _write_objs(objs, prefix=""):
            print("write_objs", len(objs))
            rows = []
            for i, obj in enumerate(objs):
                print("%s/%s: model=%s id=%s" % (i, len(objs), obj._model, obj.id))
                if not obj._model:
                    raise Exception("Missing model")
                if not prefix:
                    if job_id:
                        if tasks.is_aborted(job_id):
                            return
                        tasks.set_progress(job_id,i*100/len(objs),"Exporting record %s of %s."%(i+1,len(objs)))
                row = {}
                todo = {}
                for path in exp_fields:
                    if not path.startswith(prefix):
                        continue
                    rpath = path[len(prefix):]
                    n = rpath.split(".", 1)[0]
                    m = get_model(obj._model)
                    if n in m._fields:
                        f = m._fields[n]
                    elif n in m._custom_fields:
                        f = m._custom_fields[n]
                    else:
                        f=None
                    if not f and n != "id":
                        raise Exception("Invalid export field: %s" % path)
                    if isinstance(f, fields.One2Many):
                        if rpath.find(".") == -1:
                            print("WARNING: Invalid export field: %s" % path)
                            continue
                        if n not in todo:
                            todo[n] = obj[n]
                    elif isinstance(f, fields.Many2One):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v._model)
                                exp_field = mr.get_export_field()
                                v = v[exp_field]
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                if v:
                                    todo[n] = [v]
                    elif isinstance(f, fields.Selection):
                        v = obj[n]
                        if v:
                            for k, s in f.selection:
                                if v == k:
                                    v = s
                                    break
                        else:
                            v = ""
                        row[path] = v
                    elif isinstance(f, fields.Many2Many):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v.model)
                                exp_field = mr.get_export_field()
                                v = ", ".join([o[exp_field] for o in v])
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                todo[n] = v
                    else:
                        v = obj[n]
                        row[path] = v
                #print("todo",todo)
                subrows = {}
                for n, subobjs in todo.items():
                    subrows[n] = _write_objs(subobjs, prefix + n + ".")
                for rows2 in subrows.values():
                    if rows2:
                        row.update(rows2[0])
                rows.append(row)
                i = 1
                while 1:
                    row = {}
                    for rows2 in subrows.values():
                        if len(rows2) > i:
                            row.update(rows2[i])
                    if not row:
                        break
                    rows.append(row)
                    i += 1
            return rows
        #objs = self.browse(ids, context={})
        objs=[self.browse([obj_id])[0] for obj_id in ids] # for showing progress with slow function fields
        rows = _write_objs(objs)
        for row in rows:
            data = []
            for path in exp_fields:
                v = row.get(path)
                if v is None:
                    v = ""
                data.append(v)
            wr.writerow(data)
        data = out.getvalue()
        return data

    def export_data_new(self, ids, exp_fields, context={}):
        print("Model.export_data_new", ids)
        from netforce import tasks
        job_id=context.get("job_id")
        self.load_custom_fields()

        def _get_header(path, model=self._name, prefix=""):
            print("_get_header", path, model, prefix)
            m = get_model(model)
            res = path.partition(".")
            if not res[1]:
                if path == "id":
                    label = "Database ID"
                else:
                    if path in m._fields:
                        f = m._fields[path]
                    elif path in m._custom_fields:
                        f = m._custom_fields[path]
                    else:
                        raise Exception("Invalid field: %s"%path)
                    label = f.string
                return prefix + label.replace("/", "&#47;")
            n, _, path2 = res
            if n == "id":
                label = "Database ID"
            else:
                f = m._fields.get(n)
                if not f:
                    f=m._custom_fields.get(n)
                    if not f:
                        raise Exception("Invalid field: %s %s"%(n,m._name))
                label = f.string
            prefix += label.replace("/", "&#47;") + "/"
            return _get_header(path2, f.relation, prefix)
        out = StringIO()
        wr = csv.writer(out)
        headers = [_get_header(n) for n in exp_fields]
        wr.writerow(headers)

        def _write_objs(objs, model, prefix=""):
            print("write_objs", model, len(objs))
            rows = []
            for i, obj in enumerate(objs):
                print("%s/%s: model=%s id=%s" % (i, len(objs), model, obj["id"]))
                if not prefix:
                    if job_id:
                        if tasks.is_aborted(job_id):
                            return
                        tasks.set_progress(job_id,i*100/len(objs),"Exporting record %s of %s."%(i+1,len(objs)))
                row = {}
                todo = {}
                for path in exp_fields:
                    if not path.startswith(prefix):
                        continue
                    rpath = path[len(prefix):]
                    n = rpath.split(".", 1)[0]
                    m = get_model(model)
                    if n in m._fields:
                        f = m._fields[n]
                    elif n in m._custom_fields:
                        f = m._custom_fields[n]
                    else:
                        f=None
                    if not f and n != "id":
                        raise Exception("Invalid export field: %s" % path)
                    if isinstance(f, fields.One2Many):
                        if rpath.find(".") == -1:
                            print("WARNING: Invalid export field: %s" % path)
                            continue
                        if n not in todo:
                            todo[n] = obj[n]
                    elif isinstance(f, fields.Many2One):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v._model)
                                exp_field = mr.get_export_field()
                                v = v[exp_field]
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                if v:
                                    todo[n] = [v]
                    elif isinstance(f, fields.Selection):
                        v = obj[n]
                        if v:
                            for k, s in f.selection:
                                if v == k:
                                    v = s
                                    break
                        else:
                            v = ""
                        row[path] = v
                    elif isinstance(f, fields.Many2Many):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v.model)
                                exp_field = mr.get_export_field()
                                v = ", ".join([o[exp_field] for o in v])
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                todo[n] = v
                    else:
                        v = obj[n]
                        row[path] = v
                #print("todo",todo)
                subrows = {}
                for n, subobjs in todo.items():
                    m = get_model(model)
                    f = m._fields.get(n)
                    if not f:
                        f=m._custom_fields.get(n)
                        if not f:
                            raise Exception("Invalid field: %s %s"%(n,m._name))
                    rmodel=f.relation
                    subrows[n] = _write_objs(subobjs, rmodel, prefix + n + ".")
                for rows2 in subrows.values():
                    if rows2:
                        row.update(rows2[0])
                rows.append(row)
                i = 1
                while 1:
                    row = {}
                    for rows2 in subrows.values():
                        if len(rows2) > i:
                            row.update(rows2[i])
                    if not row:
                        break
                    rows.append(row)
                    i += 1
            return rows
        #objs = self.browse(ids, context={})
        print("reading data")
        objs=[]
        chunks=utils.chunks(ids,1000)
        for i,chunk_ids in enumerate(chunks):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*50/len(chunks),"Reading batch %s of %s (%s records)."%(i+1,len(chunks),len(ids)))
            res=self.read_path(chunk_ids,exp_fields,context=context)
            objs+=res
        print("finish reading data")
        #pprint(objs)
        rows = _write_objs(objs,self._name)
        for row in rows:
            data = []
            for path in exp_fields:
                v = row.get(path)
                if v is None:
                    v = ""
                data.append(v)
            wr.writerow(data)
        data = out.getvalue()
        return data

    def export_data_file(self,ids=None,condition=[],exp_fields=[],context={}):
        print("export_data_file",ids,condition)
        if ids is None:
            ids=self.search(condition)
        data=self.export_data(ids,exp_fields,context=context)
        print("export_data done, data size=%s"%len(data))
        f=tempfile.NamedTemporaryFile(prefix="export-",suffix=".csv",delete=False)
        fname=f.name.replace("/tmp/","")
        f.write(data.encode("utf-8"))
        f.close()
        return {
            "next": {
                "type": "download_export_file",
                "filename": fname,
            }
        }

    def export_data_file_new(self,ids=None,condition=[],exp_fields=[],context={}):
        print("export_data_file_new",ids,condition)
        ctx=context.copy()
        ctx["no_limit"]=True
        if ids is None:
            ids=self.search(condition,context=ctx)
        data=self.export_data_new(ids,exp_fields,context=ctx)
        print("export_data done, data size=%s"%len(data))
        f=tempfile.NamedTemporaryFile(prefix="export-",suffix=".csv",delete=False)
        fname=f.name.replace("/tmp/","")
        f.write(data.encode("utf-8"))
        f.close()
        return {
            "next": {
                "type": "download_export_file",
                "filename": fname,
            }
        }

    def import_data(self, data, context={}): # XXX: deprecated
        f = StringIO(data)
        rd = csv.reader(f)
        headers = next(rd)
        headers = [h.strip() for h in headers]
        rows = [r for r in rd]

        def _string_to_field(m, s):
            if s == "Database ID":
                return "id"
            strings = dict([(f.string, n) for n, f in m._fields.items()])
            n = strings.get(s.replace("&#47;", "/").strip())
            if not n:
                raise Exception("Field not found: '%s' in '%s'" % (s,m._name))
            return n

        def _get_prefix_model(prefix):
            model = self._name
            for s in prefix.split("/")[:-1]:
                m = get_model(model)
                n = _string_to_field(m, s)
                f = m._fields[n]
                model = f.relation
            return model

        def _get_vals(line, prefix):
            row = rows[line]
            model = _get_prefix_model(prefix)
            m = get_model(model)
            vals = {}
            empty = True
            for h, v in zip(headers, row):
                if not h:
                    continue
                if not h.startswith(prefix):
                    continue
                s = h[len(prefix):]
                if s.find("/") != -1:
                    continue
                n = _string_to_field(m, s)
                v = v.strip()
                if v == "":
                    v = None
                f = m._fields.get(n)
                if not f and n != "id":
                    raise Exception("Invalid field: %s" % n)
                if v:
                    if n == "id":
                        v = int(v)
                    elif isinstance(f, fields.Float):
                        v = float(v.replace(",", "").replace("-","")) # XXX
                    elif isinstance(f, fields.Decimal):
                        v = float(v.replace(",", "").replace("-","")) # XXX
                    elif isinstance(f, fields.Selection):
                        allowed_vals=[]
                        found=None
                        for k, s in f.selection:
                            if k!="_group":
                                allowed_vals.append(s)
                                if found is None and v==s:
                                    found=k
                        if found is None:
                            raise Exception("Invalid value '%s' for field '%s' of model '%s'. (allowed values: %s)" % (v, f.string, m._string or m._name, ",".join(["'%s'"%v for v in allowed_vals])))
                        v = found
                    elif isinstance(f, fields.Date):
                        dt = dateutil.parser.parse(v)
                        v = dt.strftime("%Y-%m-%d")
                    elif isinstance(f, fields.Many2One):
                        mr = get_model(f.relation)
                        ctx = {
                            "parent_vals": vals,
                        }
                        res = mr.import_get(v, context=ctx)
                        if not res:
                            raise Exception("Invalid value for field %s: '%s'" % (h, v))
                        v = res
                    elif isinstance(f, fields.Many2Many):
                        rnames = v.split(",")
                        rids = []
                        mr = get_model(f.relation)
                        for rname in rnames:
                            rname = rname.strip()
                            res = mr.import_get(rname)
                            rids.append(res)
                        v = [("set", rids)]
                else:
                    if isinstance(f, (fields.One2Many,)):
                        raise Exception("Invalid column '%s'" % s)
                if v is not None:
                    empty = False
                if not v and isinstance(f, fields.Many2Many):
                    v = [("set", [])]
                vals[n] = v
            if empty:
                return None
            return vals

        def _get_subfields(prefix):
            strings = []
            for h in headers:
                if not h:
                    continue
                if not h.startswith(prefix):
                    continue
                rest = h[len(prefix):]
                i = rest.find("/")
                if i == -1:
                    continue
                s = rest[:i]
                if s not in strings:
                    strings.append(s)
            model = _get_prefix_model(prefix)
            m = get_model(model)
            fields = []
            for s in strings:
                n = _string_to_field(m, s)
                fields.append((n, s))
            return fields

        def _has_vals(line, prefix=""):
            row = rows[line]
            for h, v in zip(headers, row):
                if not h:
                    continue
                if not h.startswith(prefix):
                    continue
                s = h[len(prefix):]
                if s.find("/") != -1:
                    continue
                v = v.strip()
                if v:
                    return True
            return False

        def _read_objs(line_start=0, line_end=len(rows), prefix=""):
            blocks = []
            line = line_start
            while line < line_end:
                vals = _get_vals(line, prefix)
                if vals:
                    if blocks:
                        blocks[-1]["line_end"] = line
                    blocks.append({"vals": vals, "line_start": line})
                line += 1
            if not blocks:
                return []
            blocks[-1]["line_end"] = line_end
            all_vals = []
            for block in blocks:
                vals = block["vals"]
                all_vals.append(vals)
                line_start = block["line_start"]
                line_end = block["line_end"]
                todo = _get_subfields(prefix)
                for n, s in todo:
                    vals[n] = [("delete_all",)]
                    res = _read_objs(line_start, line_end, prefix + s + "/")
                    for vals2 in res:
                        vals[n].append(("create", vals2))
            return all_vals
        line = 0
        while line < len(rows):
            while line < len(rows) and not _has_vals(line):
                line += 1
            if line == len(rows):
                break
            line_start = line
            line += 1
            while line < len(rows) and not _has_vals(line):
                line += 1
            line_end = line
            try:
                res = _read_objs(line_start=line_start, line_end=line_end)
                assert len(res) == 1
                self.merge(res[0])
            except Exception as e:
                raise Exception("Error row %d: %s" % (line_start + 2, e))

    def import_record(self, vals, skip_errors=False, context={}):
        print("import_record",self._name, vals)
        line_start=vals.get("_line_start")
        errors=[]
        try:
            job_id=context.get("job_id")
            if job_id:
                from netforce import tasks
                if tasks.is_aborted(job_id):
                    return
                num_rows=context["num_rows"]
                tasks.set_progress(job_id,50+line_start*50/num_rows,"Step 2/2: Writing record %s of %s to database."%(line_start+1,num_rows))
            vals={n:v for n,v in vals.items() if n[0]!="_"}
            vals2={}
            rec_id=None
            for n, v in vals.items():
                if n=="id":
                    rec_id=v
                    continue
                if n in self._fields:
                    f = self._fields[n]
                elif n in self._custom_fields:
                    f = self._custom_fields[n]
                else:
                    raise Exception("WARNING: no such field %s in %s"%(n,self._name))
                if v is None:
                    vals2[n]=None
                else:
                    if isinstance(f, (fields.Char, fields.Text, fields.Float, fields.Decimal, fields.Integer, fields.Date, fields.DateTime, fields.Selection, fields.Boolean, fields.File)):
                        vals2[n] = v
                    elif isinstance(f, fields.Many2One):
                        mr=get_model(f.relation)
                        if isinstance(v,int):
                            vals2[n]=v
                        elif isinstance(v,dict):
                            cond=[]
                            for k,kv in v.items(): # TODO: allow recursive m2o import
                                if k[0]=="_":
                                    continue
                                if isinstance(kv,dict): # XXX: improve this
                                    for k2,kv2 in kv.items():
                                        if k2[0]=="_":
                                            continue
                                        cond.append([k+"."+k2,"=",kv2])
                                else:
                                    cond.append([k,"=",kv])
                            res=mr.search(cond,context=context)
                            if len(res)>1:
                                #raise Exception("Duplicate records of model %s (%s)"%(mr._name,cond))
                                vals2[n]=res[0]
                            elif len(res)==1:
                                vals2[n]=res[0]
                            else:
                                #vals2[n] = mr.import_record(v,context=context)
                                raise Exception("Record not found: %s (%s)"%(cond,mr._name))
                        else:
                            raise Exception("Invalid import value for field %s of %s"%(n,self._name))
                    elif isinstance(f, fields.Many2Many):
                        mr=get_model(f.relation)
                        if not isinstance(v,dict) or len(v)!=1:
                            raise Exception("Invalid import value for field %s of %s: %s"%(n,self._name,v))
                        k=list(v.keys())[0]
                        rids=[]
                        for kv in (v[k] or "").split(","):
                            kv=kv.strip()
                            if not kv:
                                continue
                            cond=[[k,"=",kv]]
                            res=mr.search(cond,context=context)
                            if not res:
                                raise Exception("Record not found of model %s (%s)"%(mr._name,cond))
                            if len(res)>1:
                                raise Exception("Duplicate records of model %s (%s)"%(mr._name,cond))
                            rids.append(res[0])
                        vals2[n] = [("set",rids)]
            vals2_d=vals2.copy()
            vals2_d = self._add_missing_defaults(vals2_d, context=context)
            if rec_id:
                ctx=context.copy()
                ctx["active_test"]=False
                res = self.search([["id","=",rec_id]],context=ctx)
                if not res:
                    raise Exception("Invalid ID for model %s: %s"%(self._name,rec_id))
                self.write([rec_id], vals2, context=context)
            elif self._key:
                cond = [[n, "=", vals2_d.get(n)] for n in self._key]
                ids = self.search(cond,context=context)
                if not ids:
                    #raise Exception("Record not found: %s (condition=%s)"%(self._name,cond))
                    try:
                        rec_id=self.create(vals2_d,context=context)
                    except Exception as e:
                        raise Exception("Failed to create %s (vals=%s, error=%s)"%(self._name,vals2_d,str(e)))
                else:
                    if len(ids) > 1:
                        raise Exception("Duplicate key (model=%s, cond=%s)" % (self._name, cond))
                    rec_id=ids[0]
                    self.write([rec_id], vals2, context=context)
            else:
                try:
                    rec_id=self.create(vals2_d,context=context)
                except Exception as e:
                    raise Exception("Failed to create %s (vals=%s, error=%s)"%(self._name,vals2_d,str(e)))
            print("==> rec_id",rec_id)
        except Exception as e:
            err="Line %s: %s"%(line_start,e)
            if not skip_errors:
                raise Exception(err)
            errors.append(err)
        for n, v in vals.items():
            f = self._fields.get(n)
            if isinstance(f, fields.One2Many):
                mr=get_model(f.relation)
                rids=mr.search([[f.relfield,"=",rec_id]],context=context)
                if rids:
                    mr.delete(rids,context=context)
                for rvals in v:
                    rvals2={f.relfield:rec_id}
                    rvals2.update(rvals)
                    res=mr.import_record(rvals2,skip_errors=skip_errors,context=context)
                    if res.get("errors"):
                        errors+=res["errors"]
        self.function_store([rec_id],context=context)
        return {
            "record_id": rec_id,
            "errors": errors,
        }

    def import_csv(self, fname, skip_errors=True, date_fmt=None, context={}):
        print("import_csv",fname,skip_errors)
        path=utils.get_file_path(fname)
        errors=[]
        res=csv_to_json(path,self._name,skip_errors=skip_errors,date_fmt=date_fmt,context=context)
        records=res["records"]
        if res.get("errors"):
            errors+=res["errors"]
        #print("records") # XXX
        #pprint(records)
        from netforce import tasks
        job_id=context.get("job_id")
        ids=[]
        for i,record in enumerate(records):
            #print("#"*80)
            #print("Importing record %d/%d"%(i+1,len(records)))
            #print("record",record)
            vals=record["vals"]
            line_start=record["line_start"]
            line_end=record["line_end"]
            ctx=context.copy()
            ctx["no_function_store"]=True # for speed
            ctx["num_rows"]=records[-1]["line_end"]
            res=self.import_record(vals,skip_errors=skip_errors,context=ctx)
            ids.append(res["record_id"])
            errors+=res["errors"]
        self.function_store(ids,context=context)
        res={
            "count": len(ids),
        }
        if errors:
            res["alert"]="WARNING: Some records could not be imported:\n"+("\n".join(errors))
            res["alert_type"]="warning"
        return res

    def import_csv2(self, params, context={}):
        print("import_csv2",params)
        filename=params["file"]
        file_type=params["file_type"]
        imp_fields=params.get("fields")
        field_cols=params.get("field_cols",{})
        start_row=params.get("start_row")
        end_row=params.get("end_row")
        date_fmt=params.get("date_fmt")
        skip_errors=params.get("skip_errors")
        path=utils.get_file_path(filename)
        errors=[]
        res=csv_to_json(path,self._name,skip_errors=skip_errors,date_fmt=date_fmt,context=context,file_type=file_type,imp_fields=imp_fields,field_cols=field_cols,start_row=start_row,end_row=end_row)
        records=res["records"]
        if res.get("errors"):
            errors+=res["errors"]
        #print("records") # XXX
        #pprint(records)
        from netforce import tasks
        job_id=context.get("job_id")
        ids=[]
        for i,record in enumerate(records):
            #print("#"*80)
            #print("Importing record %d/%d"%(i+1,len(records)))
            #print("record",record)
            vals=record["vals"]
            line_start=record["line_start"]
            line_end=record["line_end"]
            ctx=context.copy()
            ctx["no_function_store"]=True # for speed
            ctx["num_rows"]=records[-1]["line_end"]
            res=self.import_record(vals,skip_errors=skip_errors,context=ctx)
            ids.append(res["record_id"])
            errors+=res["errors"]
        try:
            self.function_store(ids,context=context)
        except Exception as e:
            import traceback
            traceback.print_exc()
            if skip_errors:
                errors.append(str(e))
            else:
                raise e
        res={
            "count": len(ids),
        }
        if errors:
            res["alert"]="WARNING: Some records could not be imported:\n"+("\n".join(errors))
            res["alert_type"]="warning"
        return res

    def audit_log(self, operation, params, context={}):
        if not self._audit_log:
            return
        related_id=None
        if self._string:
            model_name = self._string
        else:
            model_name = self._name
        if operation == "create":
            msg = "%s %d created" % (model_name, params["id"])
            details = utils.json_dumps(params["vals"])
            related_id="%s,%d"%(self._name,params["id"])
        elif operation == "delete":
            msg = "%s %s deleted" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = ""
        elif operation == "write":
            vals = params["vals"]
            if not vals:
                return
            msg = "%s %s changed" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = utils.json_dumps(params["vals"])
            if params["ids"]:
                related_id="%s,%d"%(self._name,params["ids"][0]) # XXX
        if operation == "sync_create":
            msg = "%s %d created by remote sync" % (model_name, params["id"])
            details = utils.json_dumps(params["vals"])
        elif operation == "sync_delete":
            msg = "%s %s deleted by remote_sync" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = ""
        elif operation == "sync_write":
            vals = params["vals"]
            if not vals:
                return
            msg = "%s %s changed by remote sync" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = utils.json_dumps(params["vals"])
        netforce.logger.audit_log(msg, details, related_id=related_id)

    def get_view(self, name=None, type=None, context={}):  # XXX: remove this
        #print("get_view model=%s name=%s type=%s"%(self._name,name,type))
        if name:
            res = get_model("view").search([["name", "=", name]])
            if not res:
                raise Exception("View not found: %s" % name)
            view_id = res[0]
        elif type:
            res = get_model("view").search([["model", "=", self._name], ["type", "=", type]])
            if not res:
                raise Exception("View not found: %s/%s" % (self._name, type))
            view_id = res[0]
        view = get_model("view").browse(view_id)
        fields = {}
        doc = etree.fromstring(view.layout)
        for el in doc.iterfind(".//field"):
            name = el.attrib["name"]
            f = self._fields.get(name)
            if not f:
                raise Exception("No such field %s in %s" % (name, self._name))
            fields[name] = f.get_meta()
        view_opts = {
            "name": view.name,
            "type": view.type,
            "layout": view.layout,
            "model": self._name,
            "model_string": self._string,
            "fields": fields,
        }
        return view_opts

    def call_onchange(self, method, context={}):
        #print("call_onchange",self._name,method)
        data=context.get("data",{})
        path=context.get("path")
        def _conv_data(m,vals):
            for n,v in vals.items():
                f=m._fields.get(n)
                if not f:
                    continue
                if isinstance(f,fields.Decimal) and isinstance(v,float):
                    vals[n]=round(Decimal(v),6)
                elif isinstance(f,fields.Many2One) and isinstance(v,list):
                    vals[n]=v[0]
                elif isinstance(f,fields.Reference) and isinstance(v,list):
                    vals[n]=v[0]
                elif isinstance(f,fields.One2Many) and isinstance(v,list):
                    mr=get_model(f.relation)
                    for line_vals in v:
                        _conv_data(mr,line_vals)
        _conv_data(self,data)
        #f = getattr(self, method)
        #res = f(context=context)
        ctx={"data":data,"path":path} # XXX
        res=self.exec_func(method,[ctx],{}) # XXX
        if res is None:
            res = {}
        if "data" in res or "field_attrs" in res or "alert" in res:
            out=res
        else:
            out={"data":res}
        def _fill_m2o(m, records):
            m2o_ids={}
            for vals in records:
                for k, v in vals.items():
                    f=m._fields.get(k)
                    if not f:
                        continue
                    if not v:
                        continue
                    if isinstance(f, fields.Many2One):
                        if isinstance(v, int):
                            m2o_ids.setdefault(k,[]).append(v)
                    if isinstance(f, fields.Reference):
                        if isinstance(v, str):
                            relation,rid=v.split(",")
                            rid=int(rid)
                            mr = get_model(relation)
                            vals[k] = ["%s,%d"%(relation,rid),mr.name_get([rid])[0][1]]
                    elif isinstance(f, fields.One2Many):
                        mr = get_model(f.relation)
                        _fill_m2o(mr, v)
            print("m2o_ids",m2o_ids)
            for n,ids in m2o_ids.items():
                print("n",n)
                f=m._fields[n]
                mr = get_model(f.relation)
                names=mr.name_get(ids)
                id_names={}
                for r in names:
                    id_names[r[0]]=r
                print("id_names",id_names)
                for vals in records:
                    v=vals.get(n)
                    if isinstance(v, int):
                        vals[n]=id_names.get(v)
        if out.get("data"):
            _fill_m2o(self, [out["data"]])
            #print("L"*80)
            #print("out line",out["data"]["lines"][0])
        return out

    def _check_cycle(self, ids, context={}):
        for obj in self.browse(ids):
            count = 0
            p = obj.parent_id
            while p:
                count += 1
                if count > 100:
                    raise Exception("Cycle detected!")
                p = p.parent_id

    def trigger(self, ids, event, context={}):
        #print(">>> TRIGGER",self._name,ids,event)
        user_id=access.get_active_user()
        try:
            access.set_active_user(1)
            db = database.get_connection()
            res = db.query(
                "SELECT r.id,r.sequence,r.condition_method,r.condition_args,am.name AS action_model,r.action_method,r.action_args,r.action_stop FROM wkf_rule r JOIN model tm ON tm.id=r.trigger_model_id LEFT JOIN model am ON am.id=r.action_model_id WHERE tm.name=%s AND r.trigger_event=%s AND r.state='active' ORDER BY r.sequence", self._name, event)
            if event=="received":
                print("@"*80)
                print("@"*80)
                print("@"*80)
            for r in res:
                print("rule %s %s"%(event,r.sequence))
                try:
                    if r.condition_method:
                        f = getattr(self, r.condition_method)
                        if r.condition_args:
                            try:
                                args = utils.json_loads(r.condition_args)
                            except:
                                raise Exception("Invalid condition arguments: %s" % r.condition_args)
                        else:
                            args = {}
                        trigger_ids = f(ids, **args)
                    else:
                        trigger_ids = ids
                    if trigger_ids:
                        if r.action_model and r.action_method:
                            am = get_model(r.action_model)
                            f = getattr(am, r.action_method)
                            if r.action_args:
                                try:
                                    args = utils.json_loads(r.action_args)
                                except:
                                    raise Exception("Invalid action arguments: %s" % r.action_args)
                            else:
                                args = {}
                            ctx = context.copy()
                            ctx.update({
                                "trigger_model": self._name,
                                "trigger_ids": trigger_ids,
                            })
                            f(context=ctx, **args)
                        if r.action_stop:
                            break
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    err=traceback.format_exc()
                    db.execute("UPDATE wkf_rule SET state='inactive',error=%s WHERE id=%s", err, r.id)
        finally:
            access.set_active_user(user_id)

    def check_condition(self, ids, condition=None, context={}):
        cond = []
        if ids:
            cond.append(["id", "in", ids])
        if condition:
            cond.append(condition)
        res = self.search(cond, context=context)
        return res

    def archive(self, ids, context={}):
        self.write(ids, {"active": False})

    def restore(self, ids, context={}):
        self.write(ids, {"active": True})

    def get_export_field(self):
        try_fields=[self._export_field,self._code_field,"code",self._name_field,"name"]
        for f in try_fields:
            if f and f in self._fields:
                return f
        raise Exception("No export field for model %s"%self._name)

    def import_get(self, name, context={}):
        exp_field = self.get_export_field()
        res = self.search([[exp_field, "=", name]])
        if not res:
            return None
        if len(res) > 1:
            raise Exception("Duplicate records named '%s' of %s" % (name, self._name))
        return res[0]

    def get_report_data(self, ids, context={}):
        print("get_report_data", self._name, ids)
        if not ids:
            return
        settings = get_model("settings").browse(1)
        objs = self.browse(ids)
        data = {
            "settings": settings,
            "objs": objs,
        }
        if objs:
            data["obj"] = objs[0]
        user_id = access.get_active_user()
        if user_id:
            user = get_model("base.user").browse(user_id)
            data["user"] = user
        company_id = access.get_active_company()
        if company_id:
            company = get_model("company").browse(company_id)
            data["company"] = company
        return data

    def get_report_data_old(self, context={}):  # XXX: remove this later
        print("get_report_data_old", self._name)
        refer_id = int(context["refer_id"])
        ids = [refer_id]
        return self.get_report_data(ids, context=context)

    def read_group(self, group_fields=[], agg_fields=[], condition=[], having=[], order=None, limit=None, offset=None, context={}):
        select_cols = []
        group_cols = []
        tbl_count = 1
        joins = []
        for n in group_fields:
            fnames = n.split(".")
            m = self
            tbl = "tbl0"
            for fname in fnames[:-1]:
                f = m.get_field(fname)
                mr = get_model(f.relation)
                rtbl = "tbl%d" % tbl_count
                tbl_count += 1
                if isinstance(f, fields.Many2One):
                    joins.append("JOIN %s %s ON %s.id=%s.%s" % (mr._table, rtbl, rtbl, tbl, fname))
                elif isinstance(f, fields.One2Many):
                    rf = mr.get_field(f.relfield)
                    if isinstance(rf, fields.Many2One):
                        joins.append("JOIN %s %s ON %s.%s=%s.id" % (mr._table, rtbl, rtbl, f.relfield, tbl))
                    elif isinstance(rf, fields.Reference):
                        joins.append("JOIN %s %s ON %s.%s='%s,'||%s.id" %
                                     (mr._table, rtbl, rtbl, f.relfield, m._name, tbl))
                    else:
                        raise Exception("Invalid relfield: %s" % f.relfield)
                else:
                    raise Exception("Invalid field path: %s" % n)
                m = mr
                tbl = rtbl
            fname = fnames[-1]
            f = m.get_field(fname)
            func = f.sql_function
            if func:
                op = func[0]
                param = func[1]
                if op == "year":
                    expr = "to_char(%s.\"%s\",'YYYY')" % (tbl, param)
                elif op == "quarter":
                    expr = "to_char(%s.\"%s\",'YYYY-Q')" % (tbl, param)
                elif op == "month":
                    expr = "to_char(%s.\"%s\",'YYYY-MM')" % (tbl, param)
                elif op == "week":
                    expr = "to_char(%s.\"%s\",'YYYY-IW')" % (tbl, param)
                else:
                    raise Exception("Invalid sql function: %s" % func)
            else:
                expr = "%s.\"%s\"" % (tbl, fname)
            select_cols.append("%s AS \"%s\"" % (expr, n))
            #group_cols.append("\"%s\"" % n)
            group_cols.append(expr)
        select_cols.append("COUNT(*) AS _count")
        for n in agg_fields:
            f = self.get_field(n)
            func = f.agg_function
            if func:
                op = func[0]
                param = func[1]
            else:
                op="sum"
                param=n
            if op == "sum":
                col = "SUM(tbl0.\"%s\")" % param
            else:
                raise Exception("Invalid aggregate function: %s" % func)
            col += " AS \"%s\"" % n
            select_cols.append(col)
        q = "SELECT " + ",".join(select_cols)
        q += " FROM " + self._table + " tbl0"
        if joins:
            q += " " + " ".join(joins)
        cond=[condition]
        if "active" in self._fields and context.get("active_test") != False:
            if not self._check_condition_has_active(condition):
                cond.append(["active", "=", True])
        share_condition = self.get_filter("read",context=context)
        if share_condition:
            cond.append(share_condition)
        joins, cond, args = self._where_calc(cond, context=context, tbl_count=tbl_count)
        if joins:
            q += " " + " ".join(joins)
        if cond:
            q += " WHERE (" + cond + ")"
        if group_cols:
            q += " GROUP BY " + ",".join(group_cols)
        db = database.get_connection()
        print("q", q)
        print("args", args)
        res = db.query(q, *args)
        res = [dict(r) for r in res]
        for n in group_fields:
            fnames = n.split(".")
            m = self
            for fname in fnames[:-1]:
                f = m.get_field(fname)
                if not isinstance(f, (fields.Many2One, fields.One2Many)):
                    raise Exception("Invalid field path: %s" % n)
                m = get_model(f.relation)
            fname = fnames[-1]
            f = m.get_field(fname)
            if isinstance(f, fields.Many2One):
                mr = get_model(f.relation)
                r_ids = [r[n] for r in res if r[n]]
                r_ids = list(set(r_ids))
                res2 = mr.name_get(r_ids)
                names = {}
                for r in res2:
                    names[r[0]] = r[1]
                for r in res:
                    r_id = r[n]
                    if r_id:
                        r[n] = [r_id, names.get(r_id, "Permission Denied")]

        def _sort_key(r):  # XXX: faster
            k = []
            for n in group_fields:
                v = r[n]
                fnames = n.split(".")
                m = self
                for fname in fnames[:-1]:
                    f = m.get_field(fname)
                    if not isinstance(f, (fields.Many2One, fields.One2Many)):
                        raise Exception("Invalid field path: %s" % n)
                    m = get_model(f.relation)
                fname = fnames[-1]
                f = m.get_field(fname)
                if v is None:
                    s = ""
                elif isinstance(f, fields.Many2One):
                    s = v[1]
                else:
                    s = str(v)
                k.append(s)
            return k
        res.sort(key=_sort_key)
        return res

    def read_path(self, ids, field_paths, context={}):
        """Read records (with nested field names)

        Args:
            ids (list of int): ids of records to read

            field_paths (list of str): paths of fields to read (paths can include nested field names, like field1.field2.field3)

        Result:
            (list of dict): record values
        """
        print(">>> read_path %s %s %s"%(self._name,ids,field_paths))
        self.load_custom_fields()
        field_names=[]
        sub_paths={}
        for path in field_paths:
            if isinstance(path,str):
                n,_,paths=path.partition(".")
            elif isinstance(path,list):
                n=path[0]
                if not isinstance(n,str):
                    raise Exception("Invalid path field path %s for model %s"%(path,self._name))
                paths=path[1]
            if n=="id":
                continue
            f=self._fields.get(n)
            if not f and self._custom_fields:
                f=self._custom_fields.get(n)
            if not f:
                raise Exception("Invalid field: %s"%n)
            field_names.append(n)
            if paths:
                if not isinstance(f,(fields.Many2One,fields.Reference,fields.One2Many,fields.Many2Many)):
                    raise Exception("Invalid path field path %s for model %s"%(path,self._name))
                sub_paths.setdefault(n,[])
                if isinstance(paths,str) :
                    sub_paths[n].append(paths)
                elif isinstance(paths,list) :
                    sub_paths[n]+=paths
        field_names=list(set(field_names))
        res=self.read(ids,field_names,context=context,load_m2o=False)
        for n in field_names:
            if n=="id":
                f=None
            else:
                f=self._fields.get(n)
                if not f and self._custom_fields:
                    f=self._custom_fields.get(n)
                    if not f:
                        raise Exception("Invalid field: %s"%n)
            rpaths=sub_paths.get(n)
            if rpaths:
                if isinstance(f,fields.Many2One):
                    mr=get_model(f.relation)
                    rids=[]
                    for r in res:
                        v=r[n]
                        if v:
                            rids.append(v)
                    rids=list(set(rids))
                    rids_perm=mr.search([["id","in",rids]],context={"active_test":False}) # don't remove this (need for global search)
                    #rids_perm=rids # XXX
                    try:
                        res2=mr.read_path(rids_perm,rpaths,context=context)
                    except Exception as e:
                        print("ERROR",e)
                        res2=[]
                    rvals={}
                    for r in res2:
                        rvals[r["id"]]=r
                    for r in res:
                        v=r[n]
                        if v:
                            r[n]=rvals.get(v)
                elif isinstance(f,fields.Reference):
                    rmodel_ids={}
                    for r in res:
                        v=r[n]
                        if v:
                            rmodel,rid=v.split(",")
                            rid=int(rid)
                            rmodel_ids.setdefault(rmodel,[]).append(rid)
                    print("rmodel_ids",rmodel_ids)
                    rvals={}
                    for rmodel,rids in rmodel_ids.items():
                        mr=get_model(rmodel)
                        rids=list(set(rids))
                        rids_perm=mr.search([["id","in",rids]],context={"active_test":False})
                        rids_perm=rids
                        res2=mr.read_path(rids_perm,rpaths,context=context)
                        for r in res2:
                            rvals["%s,%s"%(rmodel,r["id"])]=r
                    print("=> rvals",rvals)
                    for r in res:
                        v=r[n]
                        if v:
                            r[n]=rvals.get(v)
                elif isinstance(f,(fields.One2Many,fields.Many2Many)):
                    mr=get_model(f.relation)
                    rids=[]
                    for r in res:
                        rids+=r[n] or []
                    rids=list(set(rids))
                    rids_perm=mr.search([["id","in",rids]])
                    try:
                        res2=mr.read_path(rids_perm,rpaths,context=context)
                    except Exception as e: # XXX
                        print("!"*80)
                        print("!"*80)
                        print("!"*80)
                        import traceback
                        traceback.print_exc()
                        res2=[]
                    rvals={}
                    for r in res2:
                        rvals[r["id"]]=r
                    for r in res:
                        r[n]=[rvals[v] for v in r[n] or [] if rvals.get(v)]
        return res

    def search_read_path(self, condition, field_paths, context={}, **kw):
        """Search and read records (with nested field names)

        search_read_path combines the search and read_path methods.

        Args:
            condition (list of clauses): expression to filter records

            field_paths (list of str): paths of field names to read

            order (str): order used to sort records

            limit (int): maximum number of records to return

            offset (int): number of records to skip

            count (bool): flag to return total number of records

        Result:
            if count is false:
                list of record values
            if count is true:
                (list of record values, total number of results)
        """
        res=self.search(condition,context=context,**kw)
        if isinstance(res, tuple):
            ids, count = res
            data = self.read_path(ids, field_paths, context=context)
            return data, count
        else:
            ids = res
            data = self.read_path(ids, field_paths, context=context)
            return data

    def save_data(self,data,context={}):
        print(">>> save_data %s %s"%(self._name,data))
        o2m_fields=[]
        obj_vals={}
        for n,v in data.items():
            if n=="id":
                continue
            f=self._fields[n]
            if isinstance(f,fields.One2Many):
                o2m_fields.append(n)
            else:
                obj_vals[n]=v
        obj_id=data.get("id")
        if obj_id:
            self.write([obj_id],obj_vals,context=context)
        else:
            obj_id=self.create(obj_vals,context=context)
        if o2m_fields:
            o2m_vals=self.read([obj_id],o2m_fields,context=context)[0]
            for n in o2m_fields:
                f=self._fields[n]
                mr=get_model(f.relation)
                new_rids=set()
                for rdata in data[n]:
                    rdata2=rdata.copy()
                    rdata2[f.relfield]=obj_id
                    rid=mr.save_data(rdata2,context={})
                    new_rids.add(rid)
                del_rids=[rid for rid in o2m_vals[n] if rid not in new_rids]
                if del_rids:
                    mr.delete(del_rids)
        return obj_id

    def sync_get_key(self, ids, context={}):
        if not self._key:
            raise Exception("Missing key fields (model=%s)" % self._name)
        obj = self.browse(ids[0])  # XXX: speed
        key = []
        for n in self._key:
            f = self._fields[n]
            v = obj[n]
            if isinstance(f, (fields.Many2One, fields.Reference)):
                v = v.sync_get_key() if v else None
            key.append(v)
        return tuple(key)

    def sync_list_keys(self, condition, context={}):
        ids = self.search(condition, order="write_time", context={"active_test": False})
        keys = []
        for obj in self.browse(ids):
            k = obj.sync_get_key()
            keys.append([k, obj.id, obj.write_time])
        return keys

    def sync_check_keys(self, keys, context={}):
        res=[]
        for k in keys:
            obj_id=self.sync_find_key(k)
            if obj_id:
                obj=self.browse(obj_id) # XXX: speed
                mtime=obj.write_time
                if not mtime:
                    raise Exception("Internal error: missing write_time for %s.%d"%(self._name,obj_id))
            else:
                mtime=None
            res.append((k,mtime))
        return res

    def sync_export(self, ids, field_names=None, context={}):
        # print("Model.sync_export",self._name,ids)
        data = []
        for obj in self.browse(ids):
            vals = {}
            for n in self._fields:
                if field_names and n not in field_names:
                    continue
                f = self._fields[n]
                if not f.store and not isinstance(f, fields.Many2Many):
                    continue
                if isinstance(f, (fields.Char, fields.Text, fields.Float, fields.Decimal, fields.Integer, fields.Date, fields.DateTime, fields.Selection, fields.Boolean)):
                    vals[n] = obj[n]
                elif isinstance(f, fields.Many2One):
                    v = obj[n]
                    if v:
                        mr = get_model(f.relation)
                        if mr._key:
                            v = v.sync_get_key()
                        else:
                            v = None
                    else:
                        v = None
                    vals[n] = v
                elif isinstance(f, fields.Reference):
                    v = obj[n]
                    if v:
                        mr = get_model(v._model)
                        if mr._key:
                            v = [v._model, v.sync_get_key()]
                        else:
                            v = None
                    else:
                        v = None
                    vals[n] = v
                elif isinstance(f, fields.Many2Many):
                    v = obj[n]
                    vals[n] = [x.sync_get_key() for x in v]
            print(">" * 80)
            print("sync_export record", vals)
            data.append(vals)
        return data

    def sync_find_key(self, key, check_dup=False, context={}):
        print("sync_find_key",self._name,key)
        if not self._key:
            raise Exception("Missing key fields (model=%s)" % self._name)
        cond = []
        for n, v in zip(self._key, key):
            f = self._fields[n]
            if isinstance(f, fields.Many2One):
                if v:
                    mr = get_model(f.relation)
                    v = mr.sync_find_key(v)
            elif isinstance(f, fields.Reference):
                if v:
                    mr = get_model(v[0])
                    v = mr.sync_find_key(v[1])
            cond.append([n, "=", v])
        ids = self.search(cond, context={"active_test": False})
        if not ids:
            return None
        if len(ids) > 1:
            if check_dup:
                raise Exception("Duplicate key (model=%s, key=%s)" % (self._name, key))
            else:
                return None
        return ids[0]

    def sync_import(self, data, context={}):
        # print("Model.sync_import",self._name,data)
        for rec in data:
            print("<" * 80)
            print("sync_import record", rec)
            try:
                vals = {}
                for n, v in rec.items():
                    f = self._fields.get(n)
                    if not f:
                        print("WARNING: no such field %s in %s"%(n,self._name))
                        continue
                    if isinstance(f, (fields.Char, fields.Text, fields.Float, fields.Decimal, fields.Integer, fields.Date, fields.DateTime, fields.Selection, fields.Boolean)):
                        vals[n] = v
                    elif isinstance(f, fields.Many2One):
                        if v:
                            mr = get_model(f.relation)
                            vals[n] = mr.sync_find_key(v)
                        else:
                            vals[n] = None
                    elif isinstance(f, fields.Reference):
                        if v:
                            mr = get_model(v[0])
                            r_id = mr.sync_find_key(v[1])
                            vals[n] = "%s,%d" % (v[0], r_id) if r_id else None
                        else:
                            vals[n] = None
                    elif isinstance(f, fields.Many2Many):
                        mr = get_model(f.relation)
                        r_ids = []
                        for x in v:
                            r_id = mr.sync_find_key(x)
                            if r_id:
                                r_ids.append(r_id)
                        vals[n] = [("set", r_ids)]
                if not self._key:
                    raise Exception("Missing key fields (model=%s)" % self._name)
                for n in self._key:
                    if rec[n] and not vals[n]:
                        raise Exception("Key field not found: %s (%s)" % (rec[n], n))
                cond = [[n, "=", vals[n]] for n in self._key]
                ids = self.search(cond, context={"active_test": False})
                if not ids:
                    self.sync_create(vals)
                else:
                    if len(ids) > 1:
                        key = [rec[n] for n in self._key]
                        raise Exception("Duplicate key (model=%s, key=%s)" % (self._name, key))
                    self.sync_write(ids, vals)
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception("Error importing sync data: %s %s" % (e, rec))

    def sync_create(self, vals, context={}):
        # print("Model.sync_create",self._name,vals)
        # TODO: check perm
        cols = [n for n in vals if self._fields[n].store]
        q = "INSERT INTO " + self._table
        q += " (" + ",".join(['"%s"' % col for col in cols]) + ")"
        q += " VALUES (" + ",".join(["%s" for col in cols]) + ") RETURNING id"
        args = [vals[n] for n in cols]
        db = database.get_connection()
        res = db.get(q, *args)
        new_id = res.id
        for n in vals:
            f = self._fields[n]
            if isinstance(f, fields.Many2Many):
                mr = get_model(f.relation)
                ops = vals[n]
                for op in ops:
                    if op[0] == "set":
                        r_ids = op[1]
                        for r_id in r_ids:
                            db.execute("INSERT INTO %s (%s,%s) VALUES (%%s,%%s)" %
                                       (f.reltable, f.relfield, f.relfield_other), new_id, r_id)
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
        self.audit_log("sync_create", {"id": new_id, "vals": vals})
        return new_id

    def sync_write(self, ids, vals, context={}):
        # print("Model.sync_write",ids,vals)
        # TODO: check perm
        if not ids or not vals:
            return
        db = database.get_connection()
        cols = [n for n in vals if self._fields[n].store]
        q = "UPDATE " + self._table
        q += " SET " + ",".join(['"%s"=%%s' % col for col in cols])
        q += " WHERE id IN (" + ",".join([str(int(id)) for id in ids]) + ")"
        args = [vals[n] for n in cols]
        db.execute(q, *args)
        for n in vals:
            f = self._fields[n]
            if isinstance(f, fields.Many2Many):
                mr = get_model(f.relation)
                ops = vals[n]
                for op in ops:
                    if op[0] == "set":
                        r_ids = op[1]
                        db.execute("DELETE FROM %s WHERE %s IN %%s" % (f.reltable, f.relfield), tuple(ids))
                        for id1 in ids:
                            for id2 in r_ids:
                                db.execute("INSERT INTO %s (%s,%s) VALUES (%%s,%%s)" %
                                           (f.reltable, f.relfield, f.relfield_other), id1, id2)
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
        self.audit_log("sync_write", {"ids": ids, "vals": vals})

    def sync_delete(self, ids, context={}):
        # TODO: check perm
        if not ids:
            return
        q = "DELETE FROM " + self._table + " WHERE id IN (" + ",".join([str(int(id)) for id in ids]) + ")"
        db = database.get_connection()
        try:
            db.execute(q)
        except psycopg2.Error as e:
            code = e.pgcode
            if code == "23502":
                raise Exception(
                    "Can't delete item because it is still being referenced (model=%s, ids=%s)" % (self._name, ids))
        self.audit_log("sync_delete", {"ids": ids})

    def _clean_references(self,ids,context={}):
        print("_clean_references",self._name,ids)
        field_names = [n for n, f in self._fields.items() if isinstance(f,fields.Reference)]
        print("field_names",field_names)
        res=self.read(ids,field_names,load_m2o=False)
        ref_ids={}
        for r in res:
            for n in field_names:
                v=r[n]
                if not v:
                    continue
                model,model_id=v.split(",")
                model_id=int(model_id)
                ref_ids.setdefault(model,[]).append(model_id)
        print("ref_ids",ref_ids)
        invalid_refs=set()
        for model,rids in ref_ids.items():
            rids2=get_model(model).search([["id","in",rids]])
            rids2=set(rids2)
            for rid in rids:
                if rid not in rids2:
                    invalid_refs.add("%s,%d"%(model,rid))
        print("invalid_refs",invalid_refs)
        for r in res:
            for n in field_names:
                v=r[n]
                if not v:
                    continue
                if v in invalid_refs:
                    print("cleaning field %s of %s.%d..."%(n,model,r["id"]))
                    self.write([r["id"]],{n:None})

    def start_job(self,method,args=[],opts={},context={}):
        from netforce import tasks
        job_id=tasks.start_task(self._name,method,args,opts)
        return {
            "job_id": job_id,
        }

    def abort_job(self,job_id,context={}):
        from netforce import tasks
        tasks.abort_task(job_id)

    def content_search(self,q,limit=None,order="create_time desc",context={}):
        print("content_search",self._name,q)
        words=[w.lower() for w in q.split(" ") if w]
        search_fields=[]
        for n,f in self._fields.items():
            if not isinstance(f,(fields.Char,fields.Text)):
                continue
            if not f.store:
                continue
            search_fields.append(n)
        if not search_fields:
            return []
        cond=[]
        for word in words:
            cond_word=["or"]
            for n in search_fields:
                cond_word.append([n,"ilike",word])
            cond.append(cond_word)
        print("=> cond",cond)
        res=self.search_read(cond,search_fields+["create_time"],limit=limit,order=order)
        data=[]
        for r in res:
            vals={
                "id": r["id"],
                "create_time": r["create_time"],
                "fields": {},
            }
            for n in search_fields:
                val=r[n]
                if not val:
                    continue
                if val[0] in ("{","["): # XXX: JSON
                    continue
                val_lower=val.lower()
                match=False
                for word in words:
                    if val_lower.find(word)!=-1:
                        match=True
                if match:
                    vals["fields"][n]=val
            if vals["fields"]:
                data.append(vals)
        print("=> %s results"%len(data))
        return data

    def exec_func(self,method,args,opts):
        print("Model.exec_func",method,args,opts)
        f=getattr(self, method, None)
        if f:
            res=f(*args,**opts)
        else:
            res=self.exec_func_custom(method,args,opts)
        return res

    def exec_func_custom(self,method,args,opts):
        print("Model.exec_func_custom",method,args,opts)
        dbname=database.get_active_db()
        js_ctx=js_contexts.get((dbname,self._name))
        if not js_ctx:
            print("new js context",self._name,os.getpid())
            db=database.get_connection()
            res=db.get("SELECT code_js FROM model WHERE name=%s",self._name)
            code=res["code_js"] if res else None
            if not code:
                raise Exception("Custom code not found for model %s, method %s"%(self._name,method))
            code=code.replace('"use strict";',"")
            #print("code",code)
            js_ctx=new_js_context()
            js_ctx.eval(model_js_code)
            js_ctx.eval(moment_js_code) # XXX
            js_ctx.eval(code)
            def _log(*args):
                try:
                    print("JS._log",*args)
                    args_=_conv_from_js(args)
                    print("args_",args)
                    log_dir=os.path.join(utils.get_static_path(),"logs")
                    if log_dir:
                        if not os.path.exists(log_dir):
                            os.makedirs(log_dir)
                        log_path=os.path.join(log_dir,"console.log")
                        line=" ".join(str(a) for a in args_)
                        f=open(log_path,"a")
                        t=time.strftime("%Y-%m-%d %H:%M:%S")
                        f.write("[%s] "%t+line+"\n")
                        f.flush()
                except Exception as e:
                    print("!"*80)
                    print("JS._log ERROR")
                    import traceback
                    traceback.print_exc()
            def _exec(model,method,args,opts={}):
                try:
                    print("JS._exec",model,method,args,opts)
                    m=get_model(model)
                    args_=_conv_from_js(args)
                    opts_=_conv_from_js(opts)
                    res=m.exec_func(method,args_,opts_)
                    res_=_conv_to_js(js_ctx,res)
                    #print("=> res_",res_)
                    return res_
                except Exception as e:
                    print("!"*80)
                    print("JS._exec ERROR")
                    import traceback
                    traceback.print_exc()
                    raise e
            def _fmt_date(d=None,fmt="YYYY-MM-DD"):
                if not d:
                    d=time.strftime("%Y-%m-%d")
                return utils.format_date(d,fmt)
            def _get_active_user():
                return access.get_active_user()
            def _get_active_company():
                return access.get_active_company()
            js_ctx.add_callable("log",_log)
            js_ctx.add_callable("exec",_exec)
            js_ctx.add_callable("fmt_date",_fmt_date)
            js_ctx.add_callable("get_active_user",_get_active_user)
            js_ctx.add_callable("get_active_company",_get_active_company)
            js_ctx.eval("var console={log};")
            js_contexts[(dbname,self._name)]=js_ctx
        js_func=js_ctx.get(method)
        if not js_func:
            raise Exception("Missing function: "+method)
        try:
            js_args=[_conv_to_js(js_ctx,a) for a in args]

            # Chin Added for options 2020-11-10
            if opts is not None and 'condtion' in opts:
                js_args.append(_conv_to_js(js_ctx,opts['condition']))
            
            res=js_func(*js_args)
            return _conv_from_js(res)
        except Exception as e:
            msg=str(e)
            #err="ERROR in function '%s' of '%s' (args: %s): %s"%(method,self._name,args,msg)
            err="ERROR in function '%s' of '%s': %s"%(method,self._name,msg)
            raise Exception(err)

    def load_custom_fields(self):
        #print("Model.load_custom_fields",self._name)
        db=database.get_connection()
        if not db:
            return
        res=db.query("SELECT f.name,f.string,f.type,f.selection,mr.name AS relation,rf.name AS relfield,f.unique,f.function FROM field f JOIN model m ON m.id=f.model_id LEFT JOIN model mr ON mr.id=f.relation_id LEFT JOIN field rf ON rf.id=f.relfield_id WHERE m.name=%s",self._name)
        self._custom_fields={}
        for r in res:
            if r.type=="char":
                f=fields.Char(r.string,unique=r.unique,function=r.function)
            elif r.type=="text":
                f=fields.Text(r.string,unique=r.unique)
            elif r.type=="integer":
                f=fields.Integer(r.string,unique=r.unique)
            elif r.type=="decimal":
                f=fields.Decimal(r.string,unique=r.unique,function=r.function)
            elif r.type=="boolean":
                f=fields.Boolean(r.string,unique=r.unique)
            elif r.type=="date":
                f=fields.Date(r.string,unique=r.unique)
            elif r.type=="file":
                f=fields.File(r.string)
            elif r.type=="selection":
                try:
                    sel=json.loads(r.selection)
                except:
                    sel=[]
                f=fields.Selection(sel,r.string,unique=r.unique)
            elif r.type=="many2one":
                f=fields.Many2One(r.relation,r.string,unique=r.unique)
            elif r.type=="one2many":
                f=fields.One2Many(r.relation,r.relfield,r.string)
            elif r.type=="many2many":
                f=fields.Many2Many(r.relation,r.string)
            else:
                continue
            self._custom_fields[r.name]=f

    def get_meta(self,context={}):
        res=model_to_json(self)
        return res

class BrowseList(object):  # TODO: optimize for speed

    def __init__(self, model, ids, related_ids, context={}, browse_cache=None):
        self.model = model
        self.ids = ids
        self.related_ids = related_ids
        self.browse_cache = browse_cache
        self.context = context
        self.records = [
            BrowseRecord(model, id, related_ids, context=context, browse_cache=self.browse_cache) for id in ids]
        self.id_records = {obj.id: obj for obj in self.records}

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        for obj in self.records:
            yield obj

    def get(self, key, default=None):
        return self[key]

    def __getattr__(self, name):
        return self[name]

    def by_id(self, obj_id):
        return self.id_records[obj_id]

    def __getitem__(self, key):
        if key == "_count":
            return len(self.ids)
        elif isinstance(key, int):
            return self.records[key]
        elif isinstance(key, slice):
            return self.records[key]
        elif isinstance(key, str):
            m = get_model(self.model)
            f = getattr(m, key, None)
            if f and hasattr(f, "__call__"):
                def call(*a, **kw):
                    return f(self.ids, *a, **kw)
                return call
            return None # XXX
        else:
            raise Exception("Invalid browse key: %s" % key)

class BrowseRecord(object):

    def __init__(self, model, id, related_ids, context={}, browse_cache=None):
        if browse_cache is None:
            browse_cache = {}
        self._model = model
        self.id = id
        self.related_ids = related_ids
        self.context = context
        self.browse_cache = browse_cache

    def get(self, key, default=None):
        return self[key]

    def __getattr__(self, name):
        return self[name]

    def __getitem__(self, name):
        if name == "id":
            return self.id
        if name == "_model":
            return self._model
        if name == "_cache":
            return self.browse_cache
        if not self.id:
            return None
        m = get_model(self._model)
        fld = m._fields.get(name)
        if not fld and m._custom_fields:
            fld = m._custom_fields.get(name)
        if not fld:
            f = getattr(m, name, None)
            if not f or not hasattr(f, "__call__"):
                #raise Exception("No such attribute %s in %s"%(name,self._model))
                return None  # XXX: check if safe to do this, need it for report...

            def call(*a, **kw):
                #print("BrowseRecord call %s %s %s"%(m._name,self.id,name))
                return f([self.id], *a, **kw)
            return call
        model_cache = self.browse_cache.setdefault(self._model, {})
        cache = model_cache.setdefault(self.id, {})
        if not name in cache:
            missing_ids = [id for id in self.related_ids if id not in model_cache or name not in model_cache[id]]
            missing_ids = list(set(missing_ids))
            field_names = [name]
            if fld.eager_load:
                for n, f in m._fields.items():
                    if f.eager_load and n != name:
                        field_names.append(n)
            #print("BrowseRecord read %s %s %s"%(m._name,missing_ids,field_names))
            res = m.read(missing_ids, field_names, load_m2o=False, context=self.context)
            for n in field_names:
                fld = m._fields.get(n)
                if isinstance(fld, fields.Many2One):
                    ids2 = [r[n] for r in res if r[n]]
                    ids2 = list(set(ids2))
                    for r in res:
                        val = r[n]
                        r[n] = BrowseRecord(
                            fld.relation, val, ids2, context=self.context, browse_cache=self.browse_cache)
                elif isinstance(fld, (fields.One2Many, fields.Many2Many)):
                    ids2 = []
                    for r in res:
                        ids2 += r[n]
                    ids2 = list(set(ids2))
                    for r in res:
                        val = r[n]
                        r[n] = BrowseList(
                            fld.relation, val, related_ids=ids2, context=self.context, browse_cache=self.browse_cache)
                elif isinstance(fld, fields.Reference):
                    r_model_ids = {}
                    for r in res:
                        val = r[n]
                        if val and "," in val:
                            r_model, r_id = val.split(",")
                            r_id = int(r_id)
                            r_model_ids.setdefault(r_model, []).append(r_id)
                    for r_model, r_ids in r_model_ids.items():
                        r_ids=list(set(r_ids))
                        r_ids2=get_model(r_model).search([["id","in",r_ids]])
                        r_model_ids[r_model] = r_ids2
                    for r in res:
                        val = r[n]
                        if val and "," in val:
                            r_model, r_id = val.split(",")
                            r_id = int(r_id)
                            r_ids = r_model_ids[r_model]
                            if r_id in r_ids: # XXX: make faster, use dict
                                r[n] = BrowseRecord(
                                    r_model, r_id, r_ids, context=self.context, browse_cache=self.browse_cache)
                            else:
                                r[n]=None
                        else:
                            r[n] = BrowseRecord(None, None, [], context=self.context, browse_cache=self.browse_cache)
            for r in res:
                model_cache.setdefault(r["id"], {}).update(r)
        val = cache.get(name)
        return val

    def __bool__(self):
        return self.id != None


def update_db(force=False):
    print("update_db")
    access.set_active_user(1)
    db_version = utils.get_db_version() or "0"
    mod_version = netforce.get_module_version_name()
    if utils.compare_version(db_version, mod_version) == 0:
        print("Database is already at version %s" % mod_version)
        if not force:
            return
        print("Upgrading anyway...")
    if utils.compare_version(db_version, mod_version) > 0:
        print("Database is at a newer version (%s)" % db_version)
        if not force:
            return
        print("Upgrading anyway...")
    print("Upgrading database from version %s to %s" % (db_version, mod_version))
    for model in sorted(models):
        m = models[model]
        if not m._store:
            continue
        m.update_db()
    for model in sorted(models):
        try:
            m = models[model]
            if not m._store:
                continue
            for field in sorted(m._fields):
                f = m._fields[field]
                f.update_db()
        except Exception as e:
            print("Failed to update fields of %s" % model)
            raise e
    for model in sorted(models):
        try:
            m = models[model]
            if not m._store:
                continue
            m.update_db_constraints()
        except Exception as e:
            print("Failed to update constraints of %s" % model)
            raise e
    for model in sorted(models):
        try:
            m = models[model]
            if not m._store:
                continue
            m.update_db_indexes()
        except Exception as e:
            print("Failed to update indexes of %s" % model)
            raise e
    if utils.is_empty_db():
        print("Initializing empty database...")
        utils.init_db()
    utils.set_db_version(mod_version)
    print("Upgrade completed")


def delete_transient():
    pass  # XXX


def models_to_json():
    data = {}
    for name, m in models.items():
        m.load_custom_fields()
        res = model_to_json(m)
        data[name] = res
    dbname=database.get_active_db()
    if dbname:
        db=database.get_connection()
        res=db.query("SELECT name FROM model WHERE custom=true")
        for r in res:
            m=CustomModel(r.name)
            m.load_fields()
            res = model_to_json(m)
            data[r.name] = res
    return data

def model_to_json(m):
    data = {}
    if m._string:
        data["string"] = m._string
    if m._offline:
        data["offline"] = True
    if m._name_field:
        data["name_field"] = m._name_field
    data["fields"] = {}
    field_items=list(m._fields.items())
    if m._custom_fields:
        field_items+=list(m._custom_fields.items())
    #print("XXX",fields)
    for n, f in field_items:
        f_data = {}
        f_data["string"] = f.string
        if isinstance(f, fields.Char):
            f_data["type"] = "char"
        elif isinstance(f, fields.Text):
            f_data["type"] = "text"
        elif isinstance(f, fields.Float):
            f_data["type"] = "float"
        elif isinstance(f, fields.Decimal):
            f_data["type"] = "decimal"
            if f.scale != 2:
                f_data["scale"] = f.scale
            if f.precision != 16:
                f_data["precision"] = f.precision
        elif isinstance(f, fields.Integer):
            f_data["type"] = "integer"
        elif isinstance(f, fields.Boolean):
            f_data["type"] = "boolean"
        elif isinstance(f, fields.Date):
            f_data["type"] = "date"
        elif isinstance(f, fields.DateTime):
            f_data["type"] = "datetime"
        elif isinstance(f, fields.Time):
            f_data["type"] = "time"
        elif isinstance(f, fields.Selection):
            f_data["type"] = "selection"
            f_data["selection"] = f.selection
        elif isinstance(f, fields.File):
            f_data["type"] = "file"
        elif isinstance(f, fields.Json):
            f_data["type"] = "json"
        elif isinstance(f, fields.Many2One):
            f_data["type"] = "many2one"
            f_data["relation"] = f.relation
            if f.condition:
                f_data["condition"] = f.condition
        elif isinstance(f, fields.One2Many):
            f_data["type"] = "one2many"
            f_data["relation"] = f.relation
            f_data["relfield"] = f.relfield
            if f.condition:
                f_data["condition"] = f.condition
            if f.order:
                f_data["order"] = f.order
        elif isinstance(f, fields.Many2Many):
            f_data["type"] = "many2many"
            f_data["relation"] = f.relation
        elif isinstance(f, fields.Reference):
            f_data["type"] = "reference"
            f_data["selection"] = f.selection
        elif isinstance(f, fields.Array):
            f_data["type"] = "array"
        else:
            raise Exception("Invalid field: %s.%s" % (m._name, n))
        if f.required:
            f_data["required"] = True
        if f.readonly:
            f_data["readonly"] = True
        if f.search:
            f_data["search"] = True
        if f.store:
            f_data["store"] = True
        if f.translate:
            f_data["translate"] = True
        if f.help:
            f_data["help"] = f.help
        if f.function:
            f_data["function"] = f.function
        data["fields"][n] = f_data
    return data


def add_method(model):
    def decorator(f):
        m = get_model(model)
        setattr(m.__class__, f.__name__, f)
        return f
    return decorator


def add_default(model, field):
    def decorator(f):
        m = get_model(model)
        setattr(m.__class__, f.__name__, f)
        m._defaults[field] = f
        return f
    return decorator

def csv_to_json(path,root_model,skip_errors=False,date_fmt=None,file_type=None,start_row=None,end_row=None,imp_fields=None,field_cols=None,context={}): # TODO: move this
    print("csv_to_json",path,root_model)
    errors=[]
    m=get_model(root_model)
    m.load_custom_fields()
    from netforce import tasks
    job_id=context.get("job_id")
    if not file_type:
        file_type=os.path.splitext(path.lower())[1][1:]
    #f=open(path)
    if file_type=="csv":
        f=codecs.open(path,encoding="utf-8",errors="ignore")
        rd = csv.reader(f)
    elif file_type in ("xls","xlsx"):
        df=pd.read_excel(path,header=None)
        rd=df.as_matrix()
        i=0
        for line in rd:
            i+=1
            print("Line #%s: %s"%(i,line))
    if start_row:
        rd=rd[(start_row-1):]
    if end_row:
        rd=rd[:end_row-((start_row-1) or 0)]
    if not imp_fields:
        if file_type=="csv":
            headers = next(rd)
        else:
            headers=[str(v) if v else None for v in rd[0]]
            rd=rd[1:]
        headers = [h.strip() for h in headers]
        print("=> headers",headers)
        columns=[{"title":h for h in headers}]
    else:
        col_headers={}
        for i,path in enumerate(imp_fields):
            mr=get_model(root_model)
            labels=[]
            for n in path.split("."):
                f=mr._fields.get(n)
                if not f:
                    f=mr._custom_fields.get(n)
                if not f:
                    raise Exception("No field %s of %s"%(n,mr._name))
                labels.append(f.string)
                if isinstance(f,(fields.Many2One,fields.One2Many)):
                    mr=get_model(f.relation)
            h=" / ".join(labels)
            if field_cols and path in field_cols:
                col_no=field_cols[path]
            else:
                col_no=i
            col_headers[col_no]=h
        n=max([col_no for col_no in col_headers])
        headers=[]
        for i in range(n+1):
            headers.append(col_headers.get(i))
        columns=[]
    print("headers",headers)
    rows=[]
    i=0
    for r in rd:
        i+=1
        row=[str(v) for v in r]
        row=[v if v!="nan" else "" for v in row] # XXX
        print("row %d"%i,row)
        rows.append(row)
    settings=get_model("settings").browse(1)

    def _string_to_field(m, s):
        s=s.replace("&#47;", "/").strip()
        if s and ord(s[0])==0xfeff:
            s=s[1:]
        if s == "Database ID":
            return "id"
        strings = dict([(f.string, n) for n, f in m._fields.items()])
        if m._custom_fields:
            strings.update(dict([(f.string, n) for n, f in m._custom_fields.items()]))
        if s in m._fields:
            return s
        n = strings.get(s)
        if not n:
            raise Exception("Field not found: '%s' in '%s'" % (s,m._name))
        return n

    def _get_prefix_model(prefix):
        model = root_model
        for s in prefix.split("/")[:-1]:
            m = get_model(model)
            n = _string_to_field(m, s)
            if n in m._fields:
                f = m._fields[n]
            elif m._custom_fields and n in m._custom_fields:
                f = m._custom_fields[n]
            else:
                raise Exception("Field not found %s %s"%(m._name,n))
            model = f.relation
        return model

    def _get_vals(line, prefix):
        row = rows[line]
        model = _get_prefix_model(prefix)
        m = get_model(model)
        vals = {}
        empty = True
        for h, v in zip(headers, row):
            if not h:
                continue
            if not h.startswith(prefix):
                continue
            s = h[len(prefix):].strip()
            if s.find("/") != -1:
                #empty=False # XXX
                continue
            n = _string_to_field(m, s)
            v = v.strip()
            if v == "":
                v = None
            if n in m._fields:
                f = m._fields[n]
            elif m._custom_fields and n in m._custom_fields:
                f = m._custom_fields[n]
            else:
                f=None
            if not f and n != "id":
                raise Exception("Invalid field: %s" % n)
            if v:
                if n == "id":
                    v = int(v)
                elif isinstance(f, fields.Float):
                    v = float(v.replace(",", ""))
                elif isinstance(f, fields.Decimal):
                    v = Decimal(v.replace(",", "") or "0")
                elif isinstance(f, fields.Boolean):
                    if v.lower() in ("1","yes","true","y","t"):
                        v=True
                    else:
                        v=False
                elif isinstance(f, fields.Selection):
                    allowed_vals=[]
                    found=None
                    for k, s in f.selection:
                        if k!="_group":
                            allowed_vals.append(s)
                            if found is None and v==s:
                                found=k
                    if found is None:
                        raise Exception("Invalid value '%s' for field '%s' of model '%s'. (allowed values: %s)" % (v, f.string, m._string or m._name, ",".join(["'%s'"%v for v in allowed_vals])))
                    v = found
                elif isinstance(f, fields.Date):
                    #dt = dateutil.parser.parse(v)
                    try:
                        v = utils.parse_date(v,date_fmt or settings.date_format,settings.use_buddhist_date)
                    except:
                        v = utils.parse_datetime(v,date_fmt or settings.date_format,settings.use_buddhist_date)
                        if v:
                            v=v[:10]
                elif isinstance(f, fields.DateTime):
                    #dt = dateutil.parser.parse(v)
                    v = utils.parse_datetime(v,date_fmt or settings.date_format,settings.use_buddhist_date)
                elif isinstance(f, fields.Decimal):
                    v = v.replace(",","")
                elif isinstance(f, fields.Many2Many):
                    mr = get_model(f.relation)
                    name=mr._export_field or "code"
                    v={name:v}
            else:
                if isinstance(f, (fields.One2Many,)):
                    raise Exception("Invalid column '%s'" % s)
            if v is not None:
                empty = False
            if not v and isinstance(f, fields.Many2Many):
                mr = get_model(f.relation)
                name=mr._export_field or "code"
                v={name:None}
            vals[n] = v
        if empty:
            return None
        return vals

    def _get_subfields(prefix):
        strings = []
        for h in headers:
            if not h:
                continue
            if not h.startswith(prefix):
                continue
            rest = h[len(prefix):]
            i = rest.find("/")
            if i == -1:
                continue
            s = rest[:i]
            if s not in strings:
                strings.append(s)
        model = _get_prefix_model(prefix)
        m = get_model(model)
        fields = []
        for s in strings:
            n = _string_to_field(m, s)
            fields.append((n, s))
        return fields

    def _has_vals(line, prefix=""):
        row = rows[line]
        for h, v in zip(headers, row):
            if not h:
                continue
            if not h.startswith(prefix):
                continue
            s = h[len(prefix):]
            if s.find("/") != -1:
                continue
            v = v.strip()
            if v:
                return True
        return False

    def _get_head_vals(line, prefix=""): # XXX: use _get_vals instead?
        row = rows[line]
        vals={}
        for h, v in zip(headers, row):
            if not h:
                continue
            if not h.startswith(prefix):
                continue
            s = h[len(prefix):]
            if s.find("/") != -1:
                continue
            v = v.strip()
            if v:
                vals[h]=v
        return vals

    def _vals_diff(vals1,vals2):
        diff=False
        for k in vals1:
            if vals1[k]!=vals2.get(k):
                diff=True
                break
        for k in vals2:
            if vals2[k]!=vals1.get(k):
                diff=True
                break
        return diff

    def _read_objs(line_start=0, line_end=len(rows), prefix=""):
        #print("_read_objs %s->%s prefix=%s"%(line_start,line_end,prefix))
        blocks = []
        line = line_start
        while line < line_end:
            vals = _get_vals(line, prefix)
            if vals is not None:
                if blocks:
                    blocks[-1]["line_end"] = line
                blocks.append({"vals": vals, "line_start": line})
            line += 1
        if not blocks:
            print("no blocks")
            return []
        blocks[-1]["line_end"] = line_end
        all_vals = []
        for block in blocks:
            vals = block["vals"]
            all_vals.append(vals)
            line_start = block["line_start"]
            line_end = block["line_end"]
            vals["_line_start"]=line_start+2 # XXX
            vals["_line_end"]=line_end+2
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,line_start*50/len(rows),"Step 1/2: Converting record %s of %s."%(line_start+1,len(rows)))
            todo = _get_subfields(prefix)
            for n, s in todo:
                vals[n] = []
                res = _read_objs(line_start, line_end, prefix + s + "/")
                for vals2 in res:
                    vals[n].append(vals2)
                model = _get_prefix_model(prefix)
                m=get_model(model)
                if n in m._fields:
                    f = m._fields[n]
                elif m._custom_fields and n in m._custom_fields:
                    f = m._custom_fields[n]
                else:
                    raise Exception("Invalid field: %s %s" % (m._model,n))
                if not isinstance(f,(fields.Many2One,fields.One2Many)):
                    raise Exception("Invalid value for field %s: '%s'"%(n,vals[n]))
                if isinstance(f,fields.Many2One):
                    if len(vals[n])==0:
                        vals[n]=None
                    elif len(vals[n])==1:
                        vals[n]=vals[n][0]
                    else:
                        raise Exception("Invalid value for field %s: '%s'"%(n,vals[n]))
        #print("=>",all_vals)
        return all_vals

    records=[]
    line = 0
    if root_model=="account.statement": # XXX
        root_prefix="Lines /"
    else:
        root_prefix=""
    while line < len(rows):
        while line < len(rows) and not _has_vals(line,root_prefix):
            line += 1
        if line == len(rows):
            break
        line_start = line
        start_vals=_get_head_vals(line,root_prefix)
        line += 1
        while line < len(rows):
            end_vals=_get_head_vals(line,root_prefix)
            if end_vals:
                break
            line += 1
        line_end = line
        try:
            print("reading %d->%d"%(line_start,line_end))
            res = _read_objs(line_start=line_start, line_end=line_end, prefix=root_prefix)
            if len(res) != 1:
                raise Exception("Invalid length: %s"%res)
            records.append({
                "vals": res[0],
                "line_start": line_start+2,
                "line_end": line_end+2,
            })
        except Exception as e:
            if not skip_errors:
                raise Exception("Error row %d: %s" % (line_start + 2, e))
            err="Line %s: %s"%(line_start+2,e)
            errors.append(err)
    if root_model=="account.statement" and records: # XXX
        records=[{
            "vals": {
                "lines": [r["vals"] for r in records],
            },
            "line_start": line_start,
            "line_end": line_end,
        }]
    return {
        "records": records,
        "columns": columns,
        "errors": errors,
    }

class CustomModel(object):
    _name = None
    _name_field = None
    _offline = False
    _key=None
    _custom_fields=None # XXX
    _export_field = None
    _audit_log = False

    def __init__(self,name):
        #print("CustomModel.__init__",name)
        self._name=name
        db=database.get_connection()
        res=db.get("SELECT id,string,\"order\",name_field,audit_log FROM model WHERE name=%s AND custom=true",name)
        if not res:
            raise Exception("Model not found: %s"%name)
        self._model_id=res.id
        self._string=res.string
        self._order=res.order
        self._name_field=res.name_field
        self._audit_log=res.audit_log
        self.load_fields() # XXX

    def load_fields(self):
        db=database.get_connection()
        res=db.query("SELECT f.name,f.string,f.type,f.selection,mr.name AS relation,rf.name AS relfield,f.function,f.function_multi,f.\"unique\",f.required,f.store FROM field f LEFT JOIN model mr ON mr.id=f.relation_id LEFT JOIN field rf ON rf.id=f.relfield_id WHERE f.model_id=%s",self._model_id)
        self._fields = {
            "create_time": fields.DateTime("Create Time", readonly=True),
            "write_time": fields.DateTime("Write Time", readonly=True),
            "create_uid": fields.Integer("Create UID", readonly=True),
            "write_uid": fields.Integer("Write UID", readonly=True),
        }
        self._custom_fields={} # XXX
        for r in res:
            if r.type=="char":
                f=fields.Char(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="text":
                f=fields.Text(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="integer":
                f=fields.Integer(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="decimal":
                f=fields.Decimal(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="boolean":
                f=fields.Boolean(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="date":
                f=fields.Date(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="datetime":
                f=fields.DateTime(r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="file":
                f=fields.File(r.string)
            elif r.type=="selection":
                try:
                    sel=json.loads(r.selection)
                except:
                    sel=[]
                f=fields.Selection(sel,r.string,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="many2one":
                f=fields.Many2One(r.relation,r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="reference":
                try:
                    sel=json.loads(r.selection)
                except:
                    sel=[]
                f=fields.Reference(sel,r.string,function=r.function,function_multi=r.function_multi,unique=r.unique,required=r.required,store=r.store)
            elif r.type=="one2many":
                f=fields.One2Many(r.relation,r.relfield,r.string,function=r.function,function_multi=r.function_multi,required=r.required)
            elif r.type=="many2many":
                f=fields.Many2Many(r.relation,r.string,function=r.function,function_multi=r.function_multi)
            else:
                continue
            self._fields[r.name]=f
        if "code" in self._fields: # XXX
            self._export_field="code"
        elif "name" in self._fields: # XXX
            self._export_field="name"

    def load_custom_fields(self):
        self.load_fields()

    def _where_calc(self, condition, context={}):
        #print("CustomModel._where_calc",self._name,condition)
        tbl_count=1
        joins = []
        cond_list=[]
        args = []
        for clause in condition:
            try:
                field, op, val = clause
            except:
                print("WARNING: invalid clause: %s"%str(clause))
                continue
            if field=="id":
                col="tbl0.record_id"
            else:
                rtbl = "tbl%d" % tbl_count
                tbl_count += 1
                joins.append("LEFT JOIN field_value %s ON (%s.inst_id=tbl0.id AND %s.field='%s')" % (rtbl, rtbl, rtbl, field)) # XXX: injection
                col="%s.value"%rtbl
            if op == "=" and val is None:
                cond_list.append("%s IS NULL" % col)
            elif op == "!=" and val is None:
                cond_list.append("%s IS NOT NULL" % col)
            elif op in ("=", "!=", "<", ">", "<=", ">="):
                cond_list.append("%s %s %%s" % (col, op))
                if field=="id":
                    args.append(val)
                else:
                    val_str=str(val)
                    args.append(val_str)
            elif op in ("in", "not in"):
                if val:
                    cond_list.append(col + " " + op + " (" + ",".join(["%s"] * len(val)) + ")")
                    args += [str(v) for v in val]
                else:
                    if op == "in":
                        cond_list.append("false")
                    elif op == "not in":
                        cond_list.append("true")
            elif op=="between":
                if val[0]:
                    cond_list.append("%s >= %%s" % col)
                    args.append(val[0])
                if val[1]:
                    cond_list.append("%s <= %%s" % col)
                    args.append(val[1])
            elif op in ("like", "ilike"):
                cond_list.append("%s %s %%s" % (col, op))
                args.append("%" + val + "%")
            elif op in ("=like", "=ilike"):
                cond_list.append("%s %s %%s" % (col, op[1:]))
                args.append(val)
            elif op=="not ilike":
                cond_list.append("%s %s %%s" % (col, op))
                args.append("%" + val + "%")
            elif op=="includes":
                cond_list.append("(%s IS NOT NULL AND EXISTS (SELECT 1 FROM json_array_elements(%s::json) WHERE value::text=%%s))"%(col,col)) # XXX: for postgres 9.3
                args.append(str(val))
            elif op=="not includes":
                cond_list.append("(%s IS NULL OR NOT EXISTS (SELECT 1 FROM json_array_elements(%s::json) WHERE value::text=%%s))"%(col,col)) # XXX: for postgres 9.3
                args.append(str(val))
                #cond_list.append("true")
        #print("=> joins",joins)
        #print("=> cond_list",cond_list)
        #print("=> args",args)
        cond = " AND ".join(cond_list) if cond_list else "true"
        return [joins, cond, args]

    def _order_calc(self, order):
        ord_vals=[]
        joins=[]
        clauses=[]
        if order:
            tbl_count=0
            for comp in order.split(","):
                comp = comp.strip()
                res = comp.split(" ")
                field=res[0]
                if len(res) > 1:
                    odir = res[1]
                else:
                    odir = "ASC"
                tbl="otbl%s"%tbl_count
                tbl_count+=1
                ord_vals.append("%s.value"%tbl)
                #ord_vals.append("%s.value::int"%tbl)
                joins.append("LEFT JOIN field_value %s ON (%s.inst_id=tbl0.id AND %s.field='%s')" % (tbl, tbl, tbl, field))
                clause="%s.value %s"%(tbl,odir)
                #clause="%s.value::int %s"%(tbl,odir)
                clauses.append(clause)
        return [ord_vals,joins,clauses]

    def search(self, condition, order=None, limit=None, offset=None, count=False, context={}):
        #print("CustomModel.search",self._name,condition)
        joins, cond, w_args = self._where_calc(condition, context=context)
        ord_vals, ord_joins, ord_clauses = self._order_calc(order or self._order)
        q = "SELECT DISTINCT tbl0.record_id"
        if ord_vals:
            q+=","+",".join(ord_vals)
        q+=" FROM model_inst tbl0"
        if joins:
            q += " " + " ".join(joins)
        if ord_joins:
            q += " " + " ".join(ord_joins)
        q+=" WHERE tbl0.model=%s"
        if cond:
            q += " AND (" + cond + ")"
        if ord_clauses:
            q += " ORDER BY " + ",".join(ord_clauses)
        args=[self._name]
        args+=w_args
        db = database.get_connection()
        #print("=> q",q)
        #print("=> args",args)
        q_s=db.fmt_query(q,*args)
        print("=> query",q_s)
        res = db.query(q, *args)
        all_ids=[r.record_id for r in res]
        #print("=> all_ids",all_ids)
        if offset:
            ids=all_ids[offset:]
        else:
            ids=all_ids
        if limit:
            limit=int(limit) # XXX
            ids=ids[:limit]
        else:
            ids=ids
        #if self._name=="pd.design":
        #    raise Exception("ids=%s"%ids)
        if not count:
            return ids
        return (ids,len(all_ids))

    def read(self, ids, field_names=None, context={}, load_m2o=True, load_all_trans=False):
        #print("CustomModel.read",self._name,ids,field_names)
        if not ids:
            return []
        self.load_fields()
        ids=[int(i) for i in ids]
        if not field_names:
            field_names = [n for n, f in self._fields.items() if not isinstance(f, (fields.One2Many, fields.Many2Many)) and not f.function]
        field_names=list(set(field_names)) # XXX: order
        db=database.get_connection()
        #res=db.query("SELECT record_id,field,value FROM field_value v WHERE model=%s AND record_id IN %s",self._name,tuple(ids))
        res=db.query("SELECT record_id,field,value FROM field_value v WHERE model=%s AND record_id IN %s ORDER BY id",self._name,tuple(ids)) # XXX: for dup field value
        id_vals={}
        for r in res:
            vals=id_vals.setdefault(r.record_id,{})
            vals[r.field]=r.value
        data=[]
        for id in ids:
            vals=id_vals.get(id,{})
            id_data={"id":id}
            for n in field_names:
                id_data[n]=vals.get(n)
            data.append(id_data)
        #raise Exception("data1: %s"%data)
        funcs={}
        for n in field_names:
            if n not in self._fields:
                continue
            f = self._fields[n]
            if not f.function:
                continue
            funcs.setdefault(f.function,[]).append(n)
        for func_name,names in funcs.items():
            #if len(names)>1:
            #    import pdb; pdb.set_trace()
            func_res = self.exec_func(func_name, [ids], {"context":context})
            for r in data:
                if r["id"] in func_res:
                    res=func_res[r["id"]]
                elif str(r["id"]) in func_res:
                    res=func_res[str(r["id"])]
                else:
                    continue
                if isinstance(res,dict):
                    for n in res:
                        if n not in names:
                            raise Exception("Invalid function values: %s (fields=%s)"%(res,names))
                    r.update(res)
                else:
                    if len(names)>1:
                        raise Exception("Multiple fields with same function: %s (fields=%s)"%(func_name,names))
                    n=names[0]
                    r[n]=res
        for n in field_names:
            f=self._fields.get(n)
            if isinstance(f,fields.Many2One):
                for r in data:
                    rid=r[n]
                    if rid:
                        try:
                            r[n]=int(rid)
                        except:
                            r[n]=None
                if load_m2o:
                    rids=[]
                    for r in data:
                        rid=r[n]
                        if rid:
                            rids.append(rid)
                    if not f.relation:
                        raise Exception("Missing relation model for field %s %s"%(self._name,n))
                    mr=get_model(f.relation)
                    name_field=mr._name_field or "name"
                    rids2=mr.search([["id","in",rids]],context={"active_test":False})
                    res=mr.read(rids2,[name_field])
                    id_names={}
                    for r in res:
                        id_names[r["id"]]=r[name_field]
                    for r in data:
                        rid=r[n]
                        if rid:
                            rid=int(rid)
                            if rid in id_names:
                                name=id_names[rid]
                                r[n]=[rid,name]
                            else:
                                r[n]=None
            elif isinstance(f,fields.One2Many):
                mr=get_model(f.relation)
                relfield=f.relfield
                if not relfield:
                    raise Exception("Missing relfield for field %s of %s"%(n,self._name))
                rf=mr._fields.get(relfield)
                if isinstance(rf, fields.Reference):
                    cond = [[(relfield, "in", ["%s,%d" % (self._name, id) for id in ids])]]
                else:
                    cond=[[relfield,"in",ids]]
                all_rids=mr.search(cond)
                #raise Exception("all_rids=%s"%all_rids)
                res=mr.read(all_rids,[relfield],load_m2o=False)
                id_rids={}
                for r in res:
                    rid=r[relfield]
                    id_rids.setdefault(rid,[]).append(r["id"])
                #raise Exception("id_rids=%s"%id_rids)
                if isinstance(rf, fields.Reference):
                    for r in data:
                        rids=id_rids.get("%s,%d"%(self._name,r["id"]),[])
                        r[n]=rids
                else:
                    for r in data:
                        rids=id_rids.get(r["id"],[])
                        r[n]=rids
            elif isinstance(f,fields.Many2Many):
                for r in data:
                    val=r[n]
                    if val:
                        r[n]=json.loads(val)
                    else:
                        r[n]=[]

        #print("=> data",data)
        return data

    def search_read(self, condition, field_names=None, context={}, **kw):
        #print("CustomModel.search_read",self._name,condition,field_names)
        res = self.search(condition, context=context, **kw)
        if isinstance(res, tuple):
            ids, count = res
            data = self.read(ids, field_names, context=context)
            return data, count
        else:
            ids = res
            data = self.read(ids, field_names, context=context)
            return data

    def name_get(self, ids, context={}):
        #print("CustomModel.name_get",self._name,ids)
        f_name = self._name_field or "name"
        fields = [f_name]
        res = self.read(ids, fields)
        return [(r["id"], r[f_name]) for r in res]

    def name_search(self, name, condition=None, limit=None, order=None, context={}):
        #print("CustomModel.name_search",self._name,name)
        if name=="%":
            name="" # XXX
        f = self._name_field or "name"
        if name:
            cond = [[f, "ilike", name]]
        else:
            cond=[]
        if condition:
            #cond = [cond, condition]
            cond+=condition # XXX
        ids = self.search(cond, limit=limit, context=context, order=order)
        return self.name_get(ids, context=context)

    def default_get(self, field_names=None, context={}, load_m2o=True):
        #print("CustomModel.default_get",self._name,field_names)
        try:
            defaults=self.exec_func_custom("get_defaults",[field_names],{})
        except Exception as e:
            print("!"*80)
            print("Failed to get defaults: %s"%e)
            defaults={}
        return defaults

    def create(self, vals, context={}):
        #print("CustomModel.create",self._name,vals)
        defaults=self.default_get()
        for n,v in defaults.items():
            # if n in vals:
            if vals.get(n) is not None:
                continue
            vals[n]=v
        db=database.get_connection()
        res=db.get("SELECT next_record_id FROM model WHERE name=%s",self._name)
        record_id=res.next_record_id or 1
        db.execute("UPDATE model SET next_record_id=%s WHERE name=%s",record_id+1,self._name)
        res=db.get("INSERT INTO model_inst (model_id,model,record_id) VALUES (%s,%s,%s) RETURNING id",self._model_id,self._name,record_id)
        inst_id=res.id
        self.load_fields()
        for n,v in vals.items():
            f=self._fields.get(n)
            if not f:
                continue
            if isinstance(f, fields.One2Many):
                continue
            res=db.get("SELECT f.id FROM field f JOIN model m ON m.id=f.model_id WHERE m.name=%s AND f.name=%s",self._name,n)
            if not res:
                raise Exception("Field not found: %s of %s"%(n,self._name))
            field_id=res.id
            if isinstance(f, fields.Many2Many):
                if not isinstance(v,list):
                    raise Exception("Invalid value for many2many field: %s"%v)
                rids=[]
                for op in v:
                    if op[0] in ("set", "add"):
                        rids = op[1]
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
                val_str=json.dumps(rids)
            elif isinstance(f, fields.Boolean):
                if v is None:
                    val_str=None 
                else:
                    val_str="1" if v else "0"
            elif isinstance(f, fields.Date):
                if v is None:
                    val_str=None 
                else:
                    d=datetime.strptime(v,"%Y-%m-%d")
                    val_str=d.strftime("%Y-%m-%d")
            else:
                if v is None:
                    val_str=None 
                else:
                    val_str=str(v)
            db.execute("INSERT INTO field_value (model_id,model,inst_id,record_id,field_id,field,value) VALUES (%s,%s,%s,%s,%s,%s,%s)",self._model_id,self._name,inst_id,record_id,field_id,n,val_str)
        for n,v in vals.items():
            f=self._fields.get(n)
            if not f:
                continue
            if isinstance(f, fields.One2Many):
                mr = get_model(f.relation)
                ops = vals[n]
                for op in ops:
                    if op[0] == "create":
                        vals_ = op[1]
                        vals_[f.relfield] = record_id
                        mr.create(vals_, context=context)
                    elif op[0] == "add":
                        mr.write(op[1], {f.relfield: record_id})
                    elif op[0] in ("delete", "delete_all"):
                        pass
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
        self._check_unique(vals)
        #self._check_required(vals) #Chin 2020-11-28
        self.audit_log("create", {"id": record_id, "vals": vals})
        return record_id

    def write(self, ids, vals, check_time=False, context={}):
        #print("CustomModel.write",self._name,ids,vals)
        ids=[int(i) for i in ids]
        self.load_fields()
        #self._check_required(vals) #Chin 2020-11-28
        db=database.get_connection()
        for rec_id in ids:
            res=db.get("SELECT id FROM model_inst WHERE model=%s AND record_id=%s",self._name,rec_id)
            if not res:
                raise Exception("Invalid ID %s for custom model %s"%(rec_id,self._name))
            inst_id=res.id
            for n,v in vals.items():
                f=self._fields.get(n)
                if not f:
                    continue
                if isinstance(f, fields.One2Many):
                    continue
                res=db.get("SELECT f.id FROM field f JOIN model m ON m.id=f.model_id WHERE m.name=%s AND f.name=%s",self._name,n)
                if not res:
                    raise Exception("Field not found: %s of %s"%(n,self._name))
                field_id=res.id
                if isinstance(f, fields.Many2Many):
                    if not isinstance(v,list):
                        raise Exception("Invalid value for many2many field: %s"%v)
                    rids=[]
                    for op in v:
                        if op[0] in ("set", "add"):
                            rids = op[1]
                        else:
                            raise Exception("Invalid operation: %s" % op[0])
                    val_str=json.dumps(rids)
                elif isinstance(f, fields.Boolean):
                    if v is None:
                        val_str=None 
                    else:
                        val_str="1" if v else "0"
                else:
                    if v is None:
                        val_str=None 
                    else:
                        val_str=str(v)
                #res=db.get("SELECT id FROM field_value WHERE model=%s AND field=%s AND record_id=%s",self._name,n,rec_id)
                res=db.get("SELECT id FROM field_value WHERE model=%s AND field=%s AND record_id=%s ORDER BY id desc",self._name,n,rec_id) # XXX: for dup
                if res:
                    val_id=res.id
                    db.execute("UPDATE field_value SET value=%s WHERE id=%s",val_str,val_id)
                else:
                    db.execute("INSERT INTO field_value (model_id,model,inst_id,record_id,field_id,field,value) VALUES (%s,%s,%s,%s,%s,%s,%s)",self._model_id,self._name,inst_id,rec_id,field_id,n,val_str)
        for n,v in vals.items():
            f=self._fields.get(n)
            if not f:
                continue
            if isinstance(f, fields.One2Many):
                mr = get_model(f.relation)
                rf=mr._fields.get(f.relfield)
                ops = vals[n]
                for op in ops:
                    if op[0] == "create":
                        vals_ = op[1]
                        for id in ids:
                            if isinstance(rf, fields.Reference):
                                vals_[f.relfield] = "%s,%s"%(self._name,id)
                            else:
                                vals_[f.relfield] = id
                            #import pdb; pdb.set_trace()
                            mr.create(vals_)
                    elif op[0] == "write":
                        mr.write(op[1], op[2])
                    elif op[0] == "delete":
                        mr.delete(op[1])
                    elif op[0] == "delete_all":
                        ids2 = mr.search([[f.relfield, "in", ids]])
                        mr.delete(ids2)
                    elif op[0] == "add":
                        mr.write(op[1], {f.relfield: ids[0]})
                    elif op[0] == "remove":
                        mr.write(op[1], {f.relfield: None})
                    else:
                        raise Exception("Invalid operation: %s" % op[0])
        self.function_store(ids) # XXX
        self._check_unique(vals)
        self.audit_log("write", {"ids": ids, "vals": vals})

    def function_store(self, ids, field_names=None, context={}):
        if not field_names:
            field_names = [n for n, f in self._fields.items() if f.function and f.store]
        funcs = []
        multi_funcs = {}
        for n in field_names:
            f = self._fields[n]
            if not f.function:
                raise Exception("Not a function field: %s.%s", self._name, n)
            prev_order = multi_funcs.get(f.function)
            if prev_order is not None:
                multi_funcs[f.function] = min(f.function_order, prev_order)
            else:
                multi_funcs[f.function] = f.function_order
        for func_name, order in multi_funcs.items():
            funcs.append((order, func_name, {}, None))  # TODO: context
        funcs.sort(key=lambda a: (a[0], a[1]))
        db = database.get_connection()
        for order, func_name, func_ctx, n in funcs:
            func = getattr(self, func_name)
            ctx = context.copy()
            ctx.update(func_ctx)
            res = func(ids, context=ctx)
            for rec_id, vals in res.items():
                res=db.get("SELECT id FROM model_inst WHERE model=%s AND record_id=%s",self._name,rec_id)
                if not res:
                    raise Exception("Invalid ID %s for custom model %s"%(rec_id,self._name))
                inst_id=res.id
                for n,v in vals.items():
                    res=db.get("SELECT f.id FROM field f JOIN model m ON m.id=f.model_id WHERE m.name=%s AND f.name=%s",self._name,n)
                    if not res:
                        raise Exception("Field not found: %s of %s"%(n,self._name))
                    field_id=res.id
                    if v is None:
                        val_str=None 
                    else:
                        val_str=str(v)
                    res=db.get("SELECT id FROM field_value WHERE model=%s AND field=%s AND record_id=%s ORDER BY id desc",self._name,n,rec_id)
                    if res:
                        val_id=res.id
                        db.execute("UPDATE field_value SET value=%s WHERE id=%s",val_str,val_id)
                    else:
                        db.execute("INSERT INTO field_value (model_id,model,inst_id,record_id,field_id,field,value) VALUES (%s,%s,%s,%s,%s,%s,%s)",self._model_id,self._name,inst_id,rec_id,field_id,n,val_str)

    def _check_unique(self, vals, context={}):
        cond=[]
        for n,v in vals.items():
            f=self._fields.get(n)
            if not f:
                continue
            if not f.unique:
                continue
            cond.append([n,"=",v])
        if not cond:
            return
        ids=self.search(cond)
        if len(ids)>1:
            raise Exception("Duplicate entries: %s"%cond)

    def _check_required(self, vals, context={}):
        #Chin 2020-11-28
        for f_name in self._fields:
            f = self._fields.get(f_name)
            if not f.required:
                continue
            if f_name not in vals  or vals[f_name] is None or vals[f_name] == "":
                raise Exception("Violation of not null value: %s" % (f_name))

    def delete(self, ids, context={}):
        #print("CustomModel.delete",self._name,ids)
        ids=[int(i) for i in ids]
        db=database.get_connection()
        res=db.query("SELECT rm.name AS relation,rf.name AS relfield FROM field rf JOIN model rm ON rm.id=rf.model_id JOIN model m ON m.id=rf.relation_id WHERE m.name=%s AND rf.delete_cascade=true",self._name)
        for r in res:
            print("=> delete cascade",r.relation,r.relfield)
            mr=get_model(r.relation)
            rids=mr.search([[r.relfield,"in",ids]])
            print("=> rids",rids)
            if rids:
                mr.delete(rids)
        db.execute("DELETE FROM model_inst WHERE model=%s AND record_id IN %s",self._name,tuple(ids))
        db.execute("DELETE FROM field_value WHERE model=%s AND record_id IN %s",self._name,tuple(ids))
        self.audit_log("delete", {"ids": ids})

    def read_path(self, ids, field_paths, context={}):
        #print("CustomModel.read_path",self._name,ids,field_paths)
        self.load_fields()
        field_names=[]
        sub_paths={}
        for path in field_paths:
            if isinstance(path,str):
                n,_,paths=path.partition(".")
            elif isinstance(path,list):
                n=path[0]
                if not isinstance(n,str):
                    raise Exception("Invalid path field path %s for model %s"%(path,self._name))
                paths=path[1]
            f=self._fields.get(n)
            if not f:
                raise Exception("Invalid field: %s"%n)
            field_names.append(n)
            if paths:
                if not isinstance(f,(fields.Many2One,fields.One2Many,fields.Many2Many)):
                    raise Exception("Invalid path field path %s for model %s"%(path,self._name))
                sub_paths.setdefault(n,[])
                if isinstance(paths,str) :
                    sub_paths[n].append(paths)
                elif isinstance(paths,list) :
                    sub_paths[n]+=paths
        field_names=list(set(field_names))
        res=self.read(ids,field_names,context=context,load_m2o=False)
        for n in field_names:
            f=self._fields.get(n)
            if not f:
                raise Exception("Invalid field: %s"%n)
            rpaths=sub_paths.get(n)
            if rpaths:
                mr=get_model(f.relation)
                if isinstance(f,fields.Many2One):
                    rids=[]
                    for r in res:
                        v=r[n]
                        if v:
                            rids.append(v)
                    rids=list(set(rids))
                    rids2=mr.search([["id","in",rids]])
                    res2=mr.read_path(rids2,rpaths,context=context)
                    rvals={}
                    for r in res2:
                        rvals[r["id"]]=r
                    for r in res:
                        v=r[n]
                        if v:
                            r[n]=rvals.get(v)
                elif isinstance(f,(fields.One2Many,fields.Many2Many)):
                    rids=[]
                    for r in res:
                        rids+=r[n]
                    rids=list(set(rids))
                    res2=mr.read_path(rids,rpaths,context=context)
                    rvals={}
                    for r in res2:
                        rvals[r["id"]]=r
                    for r in res:
                        r[n]=[rvals[v] for v in r[n]]
        return res

    def search_read_path(self, condition, field_paths, context={}, **kw):
        #print("CustomModel.search_read_path",self._name,condition,field_paths)
        res=self.search(condition,context=context,**kw)
        if isinstance(res, tuple):
            ids, count = res
            data = self.read_path(ids, field_paths, context=context)
            return data, count
        else:
            ids = res
            data = self.read_path(ids, field_paths, context=context)
            return data

    def read_one(self,obj_id,*args,**kw):
        res=self.read([obj_id],*args,**kw)
        return res[0]

    def write_one(self,obj_id,*args,**kw):
        self.write([obj_id],*args,**kw)

    def delete_one(self,obj_id,*args,**kw):
        self.delete([obj_id],*args,**kw)

    def import_csv(self, fname, skip_errors=None, date_fmt=None, context={}):
        print("import_csv",fname)
        path=utils.get_file_path(fname)
        errors=[]
        res=csv_to_json(path,self._name,context=context)
        records=res["records"]
        if res.get("errors"):
            errors+=res["errors"]
        from netforce import tasks
        job_id=context.get("job_id")
        ids=[]
        for i,record in enumerate(records):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,50+i*50/len(records),"Step 2/2: Writing record %s of %s to database."%(i+1,len(records)))
            print("record",record)
            vals=record["vals"]
            line_start=record["line_start"]
            line_end=record["line_end"]
            ctx=context.copy()
            ctx["no_function_store"]=True # for speed
            try:
                rec_id=self.import_record(vals,context=ctx)
                ids.append(rec_id)
            except Exception as e:
                raise Exception("Failed to import record, line %s in CSV: %s"%(line_start,str(e)))
        return {
            "count": len(ids),
        }

    def import_csv2(self, params, context={}):
        print("import_csv2",params)
        filename=params["file"]
        file_type=params["file_type"]
        imp_fields=params.get("fields")
        field_cols=params.get("field_cols",{})
        start_row=params.get("start_row")
        end_row=params.get("end_row")
        date_fmt=params.get("date_fmt")
        skip_errors=params.get("skip_errors")
        path=utils.get_file_path(filename)
        errors=[]
        res=csv_to_json(path,self._name,skip_errors=skip_errors,date_fmt=date_fmt,context=context,file_type=file_type,imp_fields=imp_fields,field_cols=field_cols,start_row=start_row,end_row=end_row)
        records=res["records"]
        if res.get("errors"):
            errors+=res["errors"]
        from netforce import tasks
        job_id=context.get("job_id")
        ids=[]
        for i,record in enumerate(records):
            vals=record["vals"]
            line_start=record["line_start"]
            line_end=record["line_end"]
            ctx=context.copy()
            ctx["no_function_store"]=True # for speed
            ctx["num_rows"]=records[-1]["line_end"]
            res=self.import_record(vals,skip_errors=skip_errors,context=ctx)
            ids.append(res["record_id"])
            errors+=res["errors"]
        try:
            pass
            #self.function_store(ids,context=context)
        except Exception as e:
            import traceback
            traceback.print_exc()
            if skip_errors:
                errors.append(str(e))
            else:
                raise e
        res={
            "count": len(ids),
        }
        if errors:
            res["alert"]="WARNING: Some records could not be imported:\n"+("\n".join(errors))
            res["alert_type"]="warning"
        return res

    def import_record(self, vals, skip_errors=False, context={}):
        print("import_record",self._name, vals)
        vals={n:v for n,v in vals.items() if n[0]!="_"}
        vals2={}
        rec_id=None
        for n, v in vals.items():
            if n=="id":
                rec_id=v
                continue
            f = self._fields.get(n)
            if not f:
                raise Exception("WARNING: no such field %s in %s"%(n,self._name))
            if v is None:
                vals2[n]=None
            else:
                if isinstance(f, (fields.Char, fields.Text, fields.Float, fields.Decimal, fields.Integer, fields.Date, fields.DateTime, fields.Selection, fields.Boolean, fields.File)):
                    vals2[n] = v
                elif isinstance(f, fields.Many2One):
                    mr=get_model(f.relation)
                    if isinstance(v,int):
                        vals2[n]=v
                    elif isinstance(v,dict):
                        cond=[]
                        for k,kv in v.items(): # TODO: allow recursive m2o import
                            if k[0]=="_":
                                continue
                            if isinstance(kv,dict): # XXX: improve this
                                for k2,kv2 in kv.items():
                                    cond.append([k+"."+k2,"=",kv2])
                            else:
                                cond.append([k,"=",kv])
                        res=mr.search(cond,context=context)
                        if len(res)>1:
                            #raise Exception("Duplicate records of model %s (%s)"%(mr._name,cond))
                            vals2[n]=res[0]
                        elif len(res)==1:
                            vals2[n]=res[0]
                        else:
                            #vals2[n] = mr.import_record(v,context=context)
                            raise Exception("Record not found: %s (%s)"%(cond,mr._name))
                    else:
                        raise Exception("Invalid import value for field %s of %s"%(n,self._name))
                elif isinstance(f, fields.Many2Many):
                    mr=get_model(f.relation)
                    if not isinstance(v,dict) or len(v)!=1:
                        raise Exception("Invalid import value for field %s of %s: %s"%(n,self._name,v))
                    k=list(v.keys())[0]
                    rids=[]
                    for kv in (v[k] or "").split(","):
                        kv=kv.strip()
                        if not kv:
                            continue
                        cond=[[k,"=",kv]]
                        res=mr.search(cond,context=context)
                        if not res:
                            raise Exception("Record not found of model %s (%s)"%(mr._name,cond))
                        if len(res)>1:
                            raise Exception("Duplicate records of model %s (%s)"%(mr._name,cond))
                        rids.append(res[0])
                    vals2[n] = [("set",rids)]
        vals2_d=vals2.copy()
        if rec_id:
            ctx=context.copy()
            ctx["active_test"]=False
            res = self.search([["id","=",rec_id]],context=ctx)
            if not res:
                raise Exception("Invalid ID for model %s: %s"%(self._name,rec_id))
            self.write([rec_id], vals2, context=context)
        else:
            cond=[]
            for n,v in vals2_d.items():
                f=self._fields.get(n)
                if not f:
                    continue
                if not f.unique:
                    continue
                cond.append([n,"=",v])
            print("=> import cond",cond)
            rec_id=None
            if cond:
                ids = self.search(cond,context=context)
                if ids:
                    rec_id=ids[0]
            if not rec_id:
                #raise Exception("Record not found: %s (condition=%s)"%(self._name,cond))
                try:
                    rec_id=self.create(vals2_d,context=context)
                except:
                    raise Exception("Failed to create %s (vals=%s)"%(self._name,vals2_d))
            else:
                self.write([rec_id], vals2, context=context)
        print("==> rec_id",rec_id)
        for n, v in vals.items():
            f = self._fields.get(n)
            if isinstance(f, fields.One2Many):
                mr=get_model(f.relation)
                rids=mr.search([[f.relfield,"=",rec_id]],context=context)
                if rids:
                    mr.delete(rids,context=context)
                for rvals in v:
                    rvals2={f.relfield:rec_id}
                    rvals2.update(rvals)
                    mr.import_record(rvals2,context=context)
        return {
            "record_id": rec_id,
            "errors": [],
        }

    # XXX/ move this
    def start_job(self,method,args=[],opts={},context={}):
        from netforce import tasks
        job_id=tasks.start_task(self._name,method,args,opts)
        return {
            "job_id": job_id,
        }

    # XXX/ move this
    def abort_job(self,job_id,context={}):
        from netforce import tasks
        tasks.abort_task(job_id)

    def exec_func(self,method,args,opts):
        print("CustomModel.exec_func",method,args,opts)
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        msg="[%s] %s %s %s\n"%(t,self._name,method,args)
        #open("/tmp/exec_func.log","a").write(msg)
        f=getattr(self, method, None)
        if method=="name_search": # XXX
            try:
                res=self.exec_func_custom(method,args,opts)
            except Exception as e:
                print("ERROR: %s"%e)
                import traceback; traceback.print_exc()
                res=f(*args,**opts)
        else:
            if f:
                res=f(*args,**opts)
            else:
                res=self.exec_func_custom(method,args,opts)
        return res

    def exec_func_custom(self,method,args,opts):
        #print("CustomModel.exec_func_custom",method,args,opts)
        dbname=database.get_active_db()
        js_ctx=js_contexts.get((dbname,self._name))
        if not js_ctx:
            print("new js context",self._name,os.getpid())
            db=database.get_connection()
            res=db.get("SELECT code_js FROM model WHERE name=%s",self._name)
            code=res["code_js"] if res else None
            if not code:
                raise Exception("Custom code not found for model %s"%self._name)
            code=code.replace('"use strict";',"")
            #print("code",code)
            js_ctx=new_js_context()
            js_ctx.eval(model_js_code)
            js_ctx.eval(moment_js_code) # XXX
            js_ctx.eval(code)
            def _log(*args):
                try:
                    print("JS._log",*args)
                    args_=_conv_from_js(args)
                    print("args_",args_)
                    log_dir=os.path.join(utils.get_static_path(),"logs")
                    if log_dir:
                        if not os.path.exists(log_dir):
                            os.makedirs(log_dir)
                        log_path=os.path.join(log_dir,"console.log")
                        line=" ".join(str(a) for a in args_)
                        f=open(log_path,"a")
                        t=time.strftime("%Y-%m-%d %H:%M:%S")
                        f.write("[%s] "%t+line+"\n")
                        f.flush()
                except Exception as e:
                    print("!"*80)
                    print("JS._log ERROR")
                    import traceback
                    traceback.print_exc()
            def _exec(model,method,args,opts={}):
                try:
                    print("JS._exec",model,method,args,opts)
                    m=get_model(model)
                    args_=_conv_from_js(args)
                    opts_=_conv_from_js(opts)
                    res=m.exec_func(method,args_,opts_)
                    res_=_conv_to_js(js_ctx,res)
                    #print("=> res_",res_)
                    return res_
                except Exception as e:
                    print("!"*80)
                    print("JS._exec ERROR")
                    import traceback
                    traceback.print_exc()
                    raise e
            def _fmt_date(d=None,fmt="YYYY-MM-DD"):
                if not d:
                    d=time.strftime("%Y-%m-%d")
                return utils.format_date(d,fmt)
            def _get_active_user():
                return access.get_active_user()
            def _get_active_company():
                return access.get_active_company()
            def _get_data_path(data,path):
                data_=_conv_from_js(data)
                print("_get_data_path",data_,path)
                res=utils.get_data_path(data_,path,parent=True)
                print("=> res",res)
                res_=_conv_to_js(js_ctx,res)
                return res_
            js_ctx.add_callable("log",_log)
            js_ctx.add_callable("exec",_exec)
            js_ctx.add_callable("fmt_date",_fmt_date)
            js_ctx.add_callable("get_active_user",_get_active_user)
            js_ctx.add_callable("get_active_company",_get_active_company)
            #js_ctx.add_callable("get_data_path",_get_data_path)
            js_ctx.eval("var console={log};")
            js_contexts[(dbname,self._name)]=js_ctx
        js_func=js_ctx.get(method)
        if not js_func:
            raise Exception("Missing function: "+method)
        try:
            js_args=[_conv_to_js(js_ctx,a) for a in args]
            
            # Chin Added for options 2020-11-10
            if opts is not None and 'condition' in opts:
                js_args.append(_conv_to_js(js_ctx,opts['condition']))

            res=js_func(*js_args)
            return _conv_from_js(res)
        except Exception as e:
            msg=str(e)
            #err="ERROR in function '%s' of '%s' (args: %s): %s"%(method,self._name,args,msg)
            import traceback
            traceback.print_exc()
            err="ERROR in function '%s' of '%s': %s"%(method,self._name,msg)
            raise Exception(err)

    def browse(self, ids, context={}):
        cache = {}
        if isinstance(ids, list):
            ids=[int(i) for i in ids]
            return BrowseList(self._name, ids, ids, context=context, browse_cache=cache)
        else:
            ids=int(ids)
            return BrowseRecord(self._name, ids, [ids], context=context, browse_cache=cache)

    def export_data(self, ids, exp_fields, context={}):
        print("CustomModel.export_data", ids)
        from netforce import tasks
        job_id=context.get("job_id")

        def _get_header(path, model=self._name, prefix=""):
            print("_get_header", path, model, prefix)
            m = get_model(model)
            res = path.partition(".")
            if not res[1]:
                if path == "id":
                    label = "Database ID"
                else:
                    f = m._fields[path]
                    label = f.string
                return prefix + label.replace("/", "&#47;")
            n, _, path2 = res
            if n == "id":
                label = "Database ID"
            else:
                f = m._fields[n]
                label = f.string
            prefix += label.replace("/", "&#47;") + "/"
            return _get_header(path2, f.relation, prefix)
        out = StringIO()
        wr = csv.writer(out)
        headers = [_get_header(n) for n in exp_fields]
        wr.writerow(headers)

        def _write_objs(objs, prefix=""):
            print("write_objs", len(objs))
            rows = []
            for i, obj in enumerate(objs):
                print("%s/%s: model=%s id=%s" % (i, len(objs), obj._model, obj.id))
                if not obj._model:
                    raise Exception("Missing model")
                if job_id:
                    if tasks.is_aborted(job_id):
                        return
                    tasks.set_progress(job_id,i*100/len(objs),"Exporting record %s of %s."%(i+1,len(objs)))
                row = {}
                todo = {}
                for path in exp_fields:
                    if not path.startswith(prefix):
                        continue
                    rpath = path[len(prefix):]
                    n = rpath.split(".", 1)[0]
                    m = get_model(obj._model)
                    f = m._fields.get(n)
                    if not f and n != "id":
                        raise Exception("Invalid export field: %s" % path)
                    if isinstance(f, fields.One2Many):
                        if rpath.find(".") == -1:
                            print("WARNING: Invalid export field: %s" % path)
                            continue
                        if n not in todo:
                            todo[n] = obj[n]
                    elif isinstance(f, fields.Many2One):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v._model)
                                exp_field = mr.get_export_field()
                                v = v[exp_field]
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                if v:
                                    todo[n] = [v]
                    elif isinstance(f, fields.Selection):
                        v = obj[n]
                        if v:
                            for k, s in f.selection:
                                if v == k:
                                    v = s
                                    break
                        else:
                            v = ""
                        row[path] = v
                    elif isinstance(f, fields.Many2Many):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v.model)
                                exp_field = mr.get_export_field()
                                v = ", ".join([o[exp_field] for o in v])
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                todo[n] = v
                    else:
                        v = obj[n]
                        row[path] = v
                #print("todo",todo)
                subrows = {}
                for n, subobjs in todo.items():
                    subrows[n] = _write_objs(subobjs, prefix + n + ".")
                for rows2 in subrows.values():
                    if rows2:
                        row.update(rows2[0])
                rows.append(row)
                i = 1
                while 1:
                    row = {}
                    for rows2 in subrows.values():
                        if len(rows2) > i:
                            row.update(rows2[i])
                    if not row:
                        break
                    rows.append(row)
                    i += 1
            return rows
        #objs = self.browse(ids, context={})
        objs=[self.browse([obj_id])[0] for obj_id in ids] # for showing progress with slow function fields
        rows = _write_objs(objs)
        for row in rows:
            data = []
            for path in exp_fields:
                v = row.get(path)
                if v is None:
                    v = ""
                data.append(v)
            wr.writerow(data)
        data = out.getvalue()
        return data

    def export_data_file(self,ids=None,condition=[],exp_fields=[],context={}):
        print("CustomModel.export_data_file",ids,condition)
        if ids is None:
            ids=self.search(condition)
        data=self.export_data(ids,exp_fields,context=context)
        print("export_data done, data size=%s"%len(data))
        f=tempfile.NamedTemporaryFile(prefix="export-",suffix=".csv",delete=False)
        fname=f.name.replace("/tmp/","")
        f.write(data.encode("utf-8"))
        f.close()
        return {
            "next": {
                "type": "download_export_file",
                "filename": fname,
            }
        }

    def export_data_new(self, ids, exp_fields, context={}):
        print("CustomModel.export_data_new", ids)
        from netforce import tasks
        job_id=context.get("job_id")
        self.load_custom_fields()

        def _get_header(path, model=self._name, prefix=""):
            print("_get_header", path, model, prefix)
            m = get_model(model)
            res = path.partition(".")
            if not res[1]:
                if path == "id":
                    label = "Database ID"
                else:
                    if path in m._fields:
                        f = m._fields[path]
                    elif path in m._custom_fields:
                        f = m._custom_fields[path]
                    else:
                        raise Exception("Invalid field: %s"%path)
                    label = f.string
                return prefix + label.replace("/", "&#47;")
            n, _, path2 = res
            if n == "id":
                label = "Database ID"
            else:
                f = m._fields[n]
                label = f.string
            prefix += label.replace("/", "&#47;") + "/"
            return _get_header(path2, f.relation, prefix)
        out = StringIO()
        wr = csv.writer(out)
        headers = [_get_header(n) for n in exp_fields]
        wr.writerow(headers)

        def _write_objs(objs, model, prefix=""):
            print("write_objs", model, len(objs))
            rows = []
            for i, obj in enumerate(objs):
                print("%s/%s: model=%s id=%s" % (i, len(objs), model, obj["id"]))
                if not prefix:
                    if job_id:
                        if tasks.is_aborted(job_id):
                            return
                        tasks.set_progress(job_id,i*100/len(objs),"Exporting record %s of %s."%(i+1,len(objs)))
                row = {}
                todo = {}
                for path in exp_fields:
                    if not path.startswith(prefix):
                        continue
                    rpath = path[len(prefix):]
                    n = rpath.split(".", 1)[0]
                    m = get_model(model)
                    if n in m._fields:
                        f = m._fields[n]
                    elif n in m._custom_fields:
                        f = m._custom_fields[n]
                    else:
                        f=None
                    if not f and n != "id":
                        raise Exception("Invalid export field: %s" % path)
                    if isinstance(f, fields.One2Many):
                        if rpath.find(".") == -1:
                            print("WARNING: Invalid export field: %s" % path)
                            continue
                        if n not in todo:
                            todo[n] = obj[n]
                    elif isinstance(f, fields.Many2One):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v._model)
                                exp_field = mr.get_export_field()
                                v = v[exp_field]
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                if v:
                                    todo[n] = [v]
                    elif isinstance(f, fields.Selection):
                        v = obj[n]
                        if v:
                            for k, s in f.selection:
                                if v == k:
                                    v = s
                                    break
                        else:
                            v = ""
                        row[path] = v
                    elif isinstance(f, fields.Many2Many):
                        if rpath.find(".") == -1:
                            v = obj[n]
                            if v:
                                mr = get_model(v.model)
                                exp_field = mr.get_export_field()
                                v = ", ".join([o[exp_field] for o in v])
                            else:
                                v = ""
                            row[path] = v
                        else:
                            if n not in todo:
                                v = obj[n]
                                todo[n] = v
                    else:
                        v = obj[n]
                        row[path] = v
                #print("todo",todo)
                subrows = {}
                for n, subobjs in todo.items():
                    m = get_model(model)
                    f = m._fields[n]
                    rmodel=f.relation
                    subrows[n] = _write_objs(subobjs, rmodel, prefix + n + ".")
                for rows2 in subrows.values():
                    if rows2:
                        row.update(rows2[0])
                rows.append(row)
                i = 1
                while 1:
                    row = {}
                    for rows2 in subrows.values():
                        if len(rows2) > i:
                            row.update(rows2[i])
                    if not row:
                        break
                    rows.append(row)
                    i += 1
            return rows
        #objs = self.browse(ids, context={})
        print("reading data")
        objs=self.read_path(ids,exp_fields,context=context)
        print("finish reading data")
        #pprint(objs)
        rows = _write_objs(objs,self._name)
        for row in rows:
            data = []
            for path in exp_fields:
                v = row.get(path)
                if v is None:
                    v = ""
                data.append(v)
            wr.writerow(data)
        data = out.getvalue()
        return data

    def export_data_file_new(self,ids=None,condition=[],exp_fields=[],context={}):
        print("export_data_file_new",ids,condition)
        if ids is None:
            ids=self.search(condition)
        data=self.export_data_new(ids,exp_fields,context=context)
        print("export_data done, data size=%s"%len(data))
        f=tempfile.NamedTemporaryFile(prefix="export-",suffix=".csv",delete=False)
        fname=f.name.replace("/tmp/","")
        f.write(data.encode("utf-8"))
        f.close()
        return {
            "next": {
                "type": "download_export_file",
                "filename": fname,
            }
        }

    def audit_log(self, operation, params, context={}):
        if not self._audit_log:
            return
        related_id=None
        if self._string:
            model_name = self._string
        else:
            model_name = self._name
        if operation == "create":
            msg = "%s %d created" % (model_name, params["id"])
            details = utils.json_dumps(params["vals"])
            related_id="%s,%d"%(self._name,params["id"])
        elif operation == "delete":
            msg = "%s %s deleted" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = ""
        elif operation == "write":
            vals = params["vals"]
            if not vals:
                return
            msg = "%s %s changed" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = utils.json_dumps(params["vals"])
            if params["ids"]:
                related_id="%s,%d"%(self._name,params["ids"][0]) # XXX
        if operation == "sync_create":
            msg = "%s %d created by remote sync" % (model_name, params["id"])
            details = utils.json_dumps(params["vals"])
        elif operation == "sync_delete":
            msg = "%s %s deleted by remote_sync" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = ""
        elif operation == "sync_write":
            vals = params["vals"]
            if not vals:
                return
            msg = "%s %s changed by remote sync" % (model_name, ",".join([str(x) for x in params["ids"]]))
            details = utils.json_dumps(params["vals"])
        netforce.logger.audit_log(msg, details, related_id=related_id)

    def trigger(self, ids, event, context={}):
        #print(">>> TRIGGER",self._name,ids,event)
        user_id=access.get_active_user()
        try:
            access.set_active_user(1)
            db = database.get_connection()
            res = db.query(
                "SELECT r.id,r.sequence,r.condition_method,r.condition_args,am.name AS action_model,r.action_method,r.action_args,r.action_stop FROM wkf_rule r JOIN model tm ON tm.id=r.trigger_model_id LEFT JOIN model am ON am.id=r.action_model_id WHERE tm.name=%s AND r.trigger_event=%s AND r.state='active' ORDER BY r.sequence", self._name, event)
            if event=="received":
                print("@"*80)
                print("@"*80)
                print("@"*80)
            for r in res:
                print("rule %s %s"%(event,r.sequence))
                try:
                    if r.condition_method:
                        f = getattr(self, r.condition_method)
                        if r.condition_args:
                            try:
                                args = utils.json_loads(r.condition_args)
                            except:
                                raise Exception("Invalid condition arguments: %s" % r.condition_args)
                        else:
                            args = {}
                        trigger_ids = f(ids, **args)
                    else:
                        trigger_ids = ids
                    if trigger_ids:
                        if r.action_model and r.action_method:
                            am = get_model(r.action_model)
                            f = getattr(am, r.action_method)
                            if r.action_args:
                                try:
                                    args = utils.json_loads(r.action_args)
                                except:
                                    raise Exception("Invalid action arguments: %s" % r.action_args)
                            else:
                                args = {}
                            ctx = context.copy()
                            ctx.update({
                                "trigger_model": self._name,
                                "trigger_ids": trigger_ids,
                            })
                            f(context=ctx, **args)
                        if r.action_stop:
                            break
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    err=traceback.format_exc()
                    db.execute("UPDATE wkf_rule SET state='inactive',error=%s WHERE id=%s", err, r.id)
        finally:
            access.set_active_user(user_id)

    def call_onchange(self, method, context={}):
        print("CustomModel.call_onchange",self._name,method)
        data=context.get("data",{})
        def _conv_data(m,vals):
            for n,v in vals.items():
                f=m._fields.get(n)
                if not f:
                    continue
                if isinstance(f,fields.Decimal) and isinstance(v,float):
                    vals[n]=round(Decimal(v),6)
                elif isinstance(f,fields.Many2One) and isinstance(v,list):
                    vals[n]=v[0]
                elif isinstance(f,fields.Reference) and isinstance(v,list):
                    vals[n]=v[0]
                elif isinstance(f,fields.One2Many) and isinstance(v,list):
                    mr=get_model(f.relation)
                    for line_vals in v:
                        _conv_data(mr,line_vals)
        _conv_data(self,data)
        path=context.get("path")
        print("path",path)
        res = self.exec_func(method,[data,path],{})
        print("<"*80)
        print("onchange res:")
        pprint(res)
        if res is None:
            res = {}
        if "data" in res or "field_attrs" in res or "alert" in res:
            out=res
        else:
            out={"data":res}
        def _fill_m2o(m, records):
            m2o_ids={}
            for vals in records:
                for k, v in vals.items():
                    f=m._fields.get(k)
                    if not f:
                        continue
                    if not v:
                        continue
                    if isinstance(f, fields.Many2One):
                        if isinstance(v, int):
                            m2o_ids.setdefault(k,[]).append(v)
                    if isinstance(f, fields.Reference):
                        if isinstance(v, str):
                            relation,rid=v.split(",")
                            rid=int(rid)
                            mr = get_model(relation)
                            vals[k] = ["%s,%d"%(relation,rid),mr.name_get([rid])[0][1]]
                    elif isinstance(f, fields.One2Many):
                        mr = get_model(f.relation)
                        _fill_m2o(mr, v)
            print("m2o_ids",m2o_ids)
            for n,ids in m2o_ids.items():
                print("n",n)
                f=m._fields[n]
                mr = get_model(f.relation)
                names=mr.name_get(ids)
                id_names={}
                for r in names:
                    id_names[r[0]]=r
                print("id_names",id_names)
                for vals in records:
                    v=vals.get(n)
                    if isinstance(v, int):
                        vals[n]=id_names.get(v)
        if out.get("data"):
            _fill_m2o(self, [out["data"]])
            #print("L"*80)
            #print("out line",out["data"]["lines"][0])
        print("<"*80)
        print("onchange out:")
        pprint(out)
        return out

    def get_meta(self,context={}):
        res=model_to_json(self)
        return res

def _conv_from_js(val):
    if isinstance(val,quickjs.Object):
        val2=json.loads(val.json())
    elif isinstance(val,(list,tuple)):
        val2=[_conv_from_js(v) for v in val]
    elif isinstance(val,dict):
        val2={n:_conv_from_js(val[n]) for n in val}
    else:
        val2=val
    return val2

def _conv_to_js(ctx,val):
    s=utils.json_dumps(val)
    js_val=ctx.parse_json(s)
    return js_val
