from netforce.model import fields,get_model
from netforce import utils
import json
import urllib.request
import re
from datetime import *
import time
import random
from pprint import pprint
try:
    from .prettytable import *
except:
    print("Failed to import prettytable")
try:
    import escpos
except:
    print("Failed to import python-escpos")

def replace_fields(s,data,model=None):
    #print("replace_fields",s,model)
    def _replace_money2(m):
        print("X"*80)
        print("_replace_money2")
        path=m.group(1)
        num_digits=int(m.group(2))
        print("path",path)
        print("num_digits",num_digits)
        val=utils.get_data_path(data,path)
        if val is None or val=="":
            return ""
        val=float(val)
        return utils.format_money(val,num_digits=num_digits)
    s=re.sub(r"\{fmt_money\(([a-z_\.]+),([0-9]+)\)\}",_replace_money2,s)
    def _replace_money(m):
        print("X"*80)
        print("_replace_money")
        path=m.group(1)
        print("path",path)
        val=utils.get_data_path(data,path)
        if val is None or val=="":
            return ""
        val=float(val)
        return utils.format_money(val)
    s=re.sub(r"\{fmt_money\(([a-z_\.]+)\)\}",_replace_money,s)
    def _replace_int(m):
        path=m.group(1)
        val=utils.get_data_path(data,path)
        if val is None or val=="":
            return ""
        val=int(val)
        return str(val)
    s=re.sub("\{fmt_int\((.*?)\)\}",_replace_int,s)
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
                        val=d.strftime("%Y-%m-%d %H:%M")
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
                insert_vals=replace_fields(insert,data,model)
                out+=insert_vals
    return out.encode("utf-8").split(b"\n")

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

def render_table(el,context):
    print("render_table")
    num_cols=el.get("num_cols") or 2
    num_rows=el.get("num_rows") or 2
    args={
        "header": False,
    }
    if el.get("table_bordered"):
        args["border"]=True
    else:
        args["border"]=False
    if el.get("width") and el["width"].endswith("c"):
        w=int(el["width"][:-1])
        args["min_table_width"]=w
        args["max_table_width"]=w
    args["padding_width"]=0 # XXX
    headers=[]
    for j in range(num_cols):
        h=str(j+1)
        headers.append(h)
    table=PrettyTable(headers,**args)
    for j in range(num_cols):
        h=str(j+1)
        table.align[h]="l"
    if el.get("col_widths"):
        widths=el["col_widths"]
        for j in range(num_cols):
            w=widths[j]
            h=str(j+1)
            table.min_width[h]=w
            table.max_width[h]=w
    if el.get("col_aligns"):
        aligns=el["col_aligns"]
        for j in range(num_cols):
            align=aligns[j]
            h=str(j+1)
            table.align[h]=align
    data=context.get("data",{})
    for i in range(num_rows):
        if el.get("field_rows") and i==1:
            list_data=utils.get_data_path(data,el["field_rows"]) or []
            for item_data in list_data:
                ctx=context.copy()
                ctx["data"]=item_data
                row=[]
                for j in range(num_cols):
                    try:
                        el2=el["elements"][i][j]
                    except:
                        continue
                    lines=render_element(el2,ctx)
                    row.append("\n".join(l.decode("utf-8") for l in lines))
                table.add_row(row)
        else:
            row=[]
            for j in range(num_cols):
                try:
                    el2=el["elements"][i][j]
                except:
                    continue
                lines=render_element(el2,context)
                row.append("\n".join(l.decode("utf-8") for l in lines))
            table.add_row(row)
    res=table.get_string()
    return res.encode("utf-8").split(b"\n")

def render_image(el,context):
    print("render_image")
    items=[]
    barcode_type=el.get("barcode_type")
    barcode_value=el.get("barcode_value") or ""
    if barcode_type=="qr":
        p=escpos.printer.Dummy()
        data=context.get("data") or {}
        val=replace_fields(barcode_value,data)
        p.qr(val)
        items.append(p.output)
    elif barcode_type=="code128":
        p=escpos.printer.Dummy()
        data=context.get("data") or {}
        val=replace_fields(barcode_value,data)
        p.barcode(val,"CODE128")
        items.append(p.output)
    return items

def render_element(el,context):
    if el["type"]=="box":
        return render_box(el,context)
    elif el["type"]=="text":
        return render_text(el,context)
    elif el["type"]=="list":
        return render_list(el,context)
    elif el["type"]=="table":
        return render_table(el,context)
    elif el["type"]=="image":
        return render_image(el,context)
    else:
        raise Exception("Unsupported element type: %s"%el["type"])

def render_page_pos(page_name,active_id,ids,layout):
    print("P"*80)
    print("render_page_pos",page_name,active_id,ids)
    res=get_model("page.layout").search([["path","=",page_name]])
    if not res:
        raise Exception("Page not found: %s"%page_name)
    page_id=res[0]
    page=get_model("page.layout").browse(page_id)
    try:
        layout=json.loads(page.layout)
    except:
        raise Exception("Invalid page layout")
    context={}
    #context["show_grid"]=True # XXX
    if layout.get("date_format"):
        context["date_format"]=layout["date_format"]
    page_contexts=[]
    other_data={
        "print_date": time.strftime("%Y-%m-%d"),
    }
    model=page.model_id.name
    if model:
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
    out=b"\n".join(items)
    filename="report.txt"
    if layout.get("filename"):
        data=context.get("data") or {}
        model=context.get("model")
        filename=replace_fields(layout["filename"],data,model)
    return {
        "data": out,
        "filename": filename,
    }
