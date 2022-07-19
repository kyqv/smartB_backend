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
    def _replace_expr_fmt_money(m):
        path=m.group(1)
        val=utils.get_data_path(data,path)
        if val is None:
            return ""
        return utils.format_money(val)
    def _replace_expr_fmt_int(m):
        path=m.group(1)
        val=utils.get_data_path(data,path)
        if val is None:
            return ""
        return "%d"%val
    def _replace_expr_fmt_hours(m):
        path=m.group(1)
        val=utils.get_data_path(data,path)
        if val is None:
            return ""
        return utils.format_hours(val)
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
                        val=d.strftime("%Y-%m-%d %I:%M %p")
                    except Exception as e:
                        print("ERROR: %s"%e)
            except Exception as e:
                print("Failed to format field %s %s"%(model,path))
        return str(val)
    s=re.sub("\{fmt_money\((.*?)\)\}",_replace_expr_fmt_money,s) # XXX
    s=re.sub("\{fmt_int\((.*?)\)\}",_replace_expr_fmt_int,s) # XXX
    s=re.sub("\{fmt_hours\((.*?)\)\}",_replace_expr_fmt_hours,s) # XXX
    s=re.sub("\{(.*?)\}",_replace_expr,s)
    #print("replace_fields => %s"%res)
    return s 

def render_box(el,context):
    print("render_box")
    items=[]
    for el2 in el["children"]:
        items.append(render_element(el2,context))
    html="<div>\n"
    html+="\n".join(items)
    html+="</div>\n"
    return html

def render_text(el,context):
    print("render_text",el.get("name"),el)
    contents=el.get("contents")
    data=context.get("data") or {}
    model=context.get("model")
    ops=contents.get("ops",[])
    html=""
    out=""
    for op in ops:
        insert=op.get("insert")
        attrs=op.get("attributes",{})
        if insert:
            if insert=="\n":
                style=""
                align=attrs.get("align")
                if align:
                    style+="text-align:%s;"%align
                html+="<p style=\"%s\">%s</p>\n"%(style,out.replace("\n","<br/>\n"))
                out=""
            else:
                insert=insert.strip()
                insert_vals=replace_fields(insert,data,model)
                out+=insert_vals
    if out:
        html+=out.replace("\n","<br/>\n")
    return html

def render_table(el,context):
    print("render_table")
    num_cols=el.get("num_cols") or 1
    num_rows=el.get("num_rows") or 1
    padding_left=el.get("padding_left") or 0
    padding_right=el.get("padding_right") or 0
    padding_top=el.get("padding_top") or 0
    padding_bottom=el.get("padding_bottom") or 0
    field_rows=el.get("field_rows")
    items=[]
    row_no=0
    for i in range(num_rows):
        if i==1 and field_rows:
            data=context.get("data") or {}
            lines=utils.get_data_path(data,field_rows) or []
            for line_data in lines:
                row_items=[]
                for j in range(num_cols):
                    if i<len(el["elements"]) and j<len(el["elements"][i]):
                        el2=el["elements"][i][j]
                    else:
                        continue
                    if el2:
                        ctx=context.copy()
                        ctx["data"]=line_data
                        cell_html=render_element(el2,ctx)
                    else:
                        cell_html=""
                    row_items.append(cell_html)
                if row_items:
                    items.append(row_items)
                    row_no+=1
        else:
            row_items=[]
            for j in range(num_cols):
                if i<len(el["elements"]) and j<len(el["elements"][i]):
                    el2=el["elements"][i][j]
                else:
                    continue
                if el2:
                    cell_html=render_element(el2,context)
                else:
                    cell_html=""
                row_items.append(cell_html)
            if row_items:
                items.append(row_items)
                row_no+=1
    if not items:
        return ""
    style="width:100%;"
    html="<table style=\"%s\">\n"%style
    for row in items:
        html+="<tr>\n"
        for cell_html in row:
            html+="<td>\n"
            html+=cell_html
            html+="</td>\n"
        html+="</tr>\n"
    html+="</table>\n"
    return html

def render_image(el,context):
    print("render_image")
    barcode_field=el.get("barcode_field")
    image_file=el.get("image_file")
    if barcode_field:
        data=context.get("data") or {}
        val=utils.get_data_path(data,barcode_field) or ""
        url="https://barcode.tec-it.com/barcode.ashx?data=%s&code=Code128&dpi=96&imagetype=Png"%val
    elif image_file:
        url="https://backend.netforce.com/static/db/nfo_tsj1932/files/"+image_file
    else:
        return ""
    style=""
    if el.get("height"):
        style+="max-height:%spx;"%el["height"]
    html="<img style=\"%s\" src=\"%s\"/>"%(style,url)
    align=el.get("align")
    if align=="center": # XXX
        html="<center>"+html+"</center>"
    return html

def render_element(el,context):
    if el["type"]=="box":
        return render_box(el,context)
    elif el["type"]=="text":
        return render_text(el,context)
    elif el["type"]=="table":
        return render_table(el,context)
    elif el["type"]=="image":
        return render_image(el,context)
    else:
        raise Exception("Unsupported element type: %s"%el["type"])

def render_page_html(layout,props):
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
    out="<html>\n"
    style=""
    if layout.get("width"): 
        style+="width:%spx;"%layout["width"]
    #style+="border:1px solid #ccc;"
    out+="<body style=\"%s\">\n"%style
    for html in items:
        out+=html
    out+="</body>\n"
    out+="</html>\n"
    filename="report.html"
    if layout.get("filename"):
        data=context.get("data") or {}
        model=context.get("model")
        filename=replace_fields(layout["filename"],data,model)
    return {
        "data": out,
        "filename": filename,
    }
