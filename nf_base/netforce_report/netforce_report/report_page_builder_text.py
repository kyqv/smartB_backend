from netforce.model import fields,get_model
from netforce import utils
import json
import urllib.request
import re
from datetime import *
import time
import random
from pprint import pprint

def replace_fields(s,data,model=None):
    #print("replace_fields",s,model)
    def _replace_expr(m):
        path=m.group(1)
        #print("replace path",path)
        val=utils.get_data_path(data,path)
        if val is None:
            val=""
        if model: 
            try:
                field_model,field_name=utils.get_field_path(model,path)
                m=get_model(field_model)
                f=m.get_field(field_name)
                if isinstance(f,fields.Date):
                    try:
                        d=datetime.strptime(val,"%Y-%m-%d")
                        val=d.strftime("%d/%m/%Y")
                    except Exception as e:
                        print("ERROR: %s"%e)
                elif isinstance(f,fields.Decimal):
                    try:
                        val=utils.format_money(val)
                    except Exception as e:
                        print("ERROR: %s"%e)
                elif isinstance(f,fields.DateTime):
                    try:
                        d=datetime.strptime(val,"%Y-%m-%d %H:%M:%S")
                        val=d.strftime("%I:%m %p")
                    except Exception as e:
                        print("ERROR: %s"%e)
            except Exception as e:
                print("Failed to format field %s %s"%(model,path))
        return str(val)
    res=re.sub("\{(.*?)\}",_replace_expr,s)
    #print("replace_fields => %s"%res)
    return res

def render_box(el,context):
    print("render_box")
    items=[]
    for el2 in el["children"]:
        items+=render_element(el2,context)
    return items

def render_text(el,context):
    print("render_text",el.get("name"),el)
    contents=el.get("contents")
    data=context.get("data") or {}
    model=context.get("model")
    ops=contents.get("ops",[])
    out=""
    for op in ops:
        insert=op.get("insert")
        if insert:
            if insert=="\n":
                out+="\n"
            else:
                insert=insert.strip()
                insert_vals=replace_fields(insert,data,model)
                out+=insert_vals
    return out.split("\n")

def render_list(el,context):
    print("render_list")
    name=el.get("name")
    if not name:
        pprint(el)
        raise Exception("Missing field name in list")
    child=el.get("child")
    if not child:
        raise Exception("Missing child")
    data=context.get("data",{})
    list_data=utils.get_data_path(data,name) or []
    print("L"*80)
    print("list_data",list_data)
    model=context.get("model")
    if model:
        field_model,field_name=utils.get_field_path(model,name)
        m=get_model(field_model)
        f=m._fields[field_name]
        list_model=f.relation
    else:
        list_model=None
    print("list_model",list_model)
    items=[]
    for item_data in list_data:
        ctx=context.copy()
        ctx["data"]=item_data
        ctx["model"]=list_model
        items+=render_element(child,ctx)
    return items

def render_element(el,context):
    if el["type"]=="box":
        return render_box(el,context)
    elif el["type"]=="text":
        return render_text(el,context)
    elif el["type"]=="list":
        return render_list(el,context)
    else:
        raise Exception("Unsupported element type: %s"%el["type"])

def render_page_text(layout,props):
    context={}
    #context["show_grid"]=True # XXX
    if layout.get("date_format"):
        context["date_format"]=layout["date_format"]
    if props.get("form_data"):
        context["form_data"]=json.loads(props["form_data"])
    model=props.get("model")
    page_contexts=[]
    other_data={
        "print_date": time.strftime("%Y-%m-%d"),
    }
    if model:
        active_id=props.get("active_id")
        if active_id:
            active_id=int(active_id)
        ids=props.get("ids")
        if ids and isinstance(ids,str):
            ids=json.loads(ids)
        if not active_id and not ids:
            raise Exception("Missing active_id or ids")
        if not ids:
            ids=[active_id]
        if layout.get("fields"):
            fields=json.loads(layout["fields"])
        else:
            fields=[]
        res=get_model(model).read_path(ids,fields)
        context["data"]=res[0]
        context["data"].update(other_data)
        context["model"]=model
        for data in res:
            ctx=context.copy()
            ctx["data"]=data
            ctx["data"].update(other_data)
            page_contexts.append(ctx)
    else:
        page_contexts=[context]
    items=[]
    for (i,page_context) in enumerate(page_contexts):
        print("render page %s"%i)
        print("context",page_context)
        for el in layout["elements"]:
            items+=render_element(el,page_context)
    out="\n".join(items)
    filename="report.txt"
    if layout.get("filename"):
        data=context.get("data") or {}
        model=context.get("model")
        filename=replace_fields(layout["filename"],data,model)
    return {
        "data": out,
        "filename": filename,
    }
