from netforce.model import fields,get_model
from netforce import utils
from netforce import database
from netforce import access
import json
import urllib.request
import re
from datetime import *
import time
import random
from pprint import pprint
import os
import subprocess
import tempfile
import requests
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import ParagraphStyle,ListStyle
    from reportlab.lib.pagesizes import A4,mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Frame, Image, ListFlowable, ListItem
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT,TA_RIGHT,TA_CENTER,TA_JUSTIFY
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    from reportlab.graphics.barcode import code39, code128, code93
    from reportlab.graphics.barcode import eanbc, qr, usps
    from reportlab.graphics.shapes import Drawing
except Exception as e:
    print("Failed to import reportlab: %s"%e)
try:
    from PyPDF2 import PdfFileMerger
except:
    print("Failed to import PyPDF2")


class NFCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_number(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        text = "Page %s of %s" % (self._pageNumber, page_count)
        self.setFont("Helvetica", 9)
        self.drawRightString(112*mm, 10*mm, text)

def render_data(doc,el,context):
    print("render_data")
    model=el.get("model")
    if not model:
        raise Exception("Missing model")
    read_type=el.get("read_type")
    if not read_type:
        raise Exception("Missing read_type")
    fields_str=el.get("fields")
    if not fields_str:
        raise Exception("Missing fields")
    fields=json.loads(fields_str)
    cond=[]
    res=get_model(model).search_read_path(cond,fields)
    if read_type=="one":
        data=res[0]
    else:
        data=res
    print("=> data",data)
    ctx=context.copy()
    ctx["data"]=data
    ctx["model"]=model
    items=[]
    for el2 in el["children"]:
        items+=render_element(doc,el2,context)
    if not items:
        return []
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ]
    if context.get("show_grid"):
        style.append(("GRID",(0,0),(-1,-1),1,colors.black))
    return [Table([[i] for i in items],colWidths=["100%"],style=style,ident="data")]

def render_box(doc,el,context):
    print("render_box")
    items=[]
    for el2 in el["children"]:
        items+=render_element(doc,el2,context)
    return items

def render_columns(doc,el,context):
    print("render_columns")
    if el.get("visibility"):
        vis_name=el["visibility"]
        data=context.get("data") or {}
        visibility=utils.get_data_path(data,vis_name)
        if not visibility:
            return ""
    cols=[]
    for col in el["columns"]:
        if col.get("children"):
            items=[]
            for el2 in col["children"]:
                items+=render_element(doc,el2,context)
            if not items:
                cols.append("")
                continue
            style=[
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
                ("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),0),
                ]
            if context.get("show_grid"):
                style.append(("GRID",(0,0),(-1,-1),1,colors.black))
            cols.append(Table([[i] for i in items],colWidths=["100%"],style=style,ident="col"))
        else: 
            cols.append("")
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ]
    if el.get("border_width") or context.get("show_grid"):
        w=float(el.get("border_width",1))
        style.append(("GRID",(0,0),(-1,-1),w,colors.black))
    if el.get("background_color"):
        color=el["background_color"]
        style.append(("BACKGROUND",(0,0),(-1,-1),color))
    if el.get("vertical_align"):
        align=el["vertical_align"].upper()
    else:
        align="TOP"
    style.append(("VALIGN",(0,0),(-1,-1),align))
    col_widths=None
    if el.get("col_widths") and len(el["col_widths"])==len(el["columns"]):
        res=el["col_widths"]
        tot=sum(res)
        col_widths=[str(w*100/tot)+"%" for w in res]
    content=Table([cols],style=style,colWidths=col_widths,ident="columns")
    pad_left=(el.get("margin_left") or 0)/6*mm
    pad_right=(el.get("margin_right") or 0)/6*mm
    pad_top=(el.get("margin_top") or 0)/6*mm
    pad_bottom=(el.get("margin_bottom") or 0)/6*mm
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),pad_left),
        ("RIGHTPADDING",(0,0),(-1,-1),pad_right),
        ("TOPPADDING",(0,0),(-1,-1),pad_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad_bottom),
        ]
    return [Table([[content]],style=style,ident="columns_cont")]

def render_table(doc,el,context):
    print("render_table")
    num_cols=el.get("num_cols") or 1
    num_rows=el.get("num_rows") or 1
    padding_left=el.get("padding_left") or 0
    padding_right=el.get("padding_right") or 0
    padding_top=el.get("padding_top") or 0
    padding_bottom=el.get("padding_bottom") or 0
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),padding_left),
        ("RIGHTPADDING",(0,0),(-1,-1),padding_right),
        ("TOPPADDING",(0,0),(-1,-1),padding_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),padding_bottom),
        ]
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
                        cell_items=render_element(doc,el2,ctx)
                        if el2.get("background_color"):
                            col=HexColor(el2["background_color"])
                            style.append(("BACKGROUND",(j,row_no),(j,row_no),col))
                    else:
                        cell_items=[]
                    row_items.append(cell_items)
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
                    cell_items=render_element(doc,el2,context)
                    if el2.get("background_color"):
                        col=HexColor(el2["background_color"])
                        style.append(("BACKGROUND",(j,row_no),(j,row_no),col))
                else:
                    cell_items=[]
                row_items.append(cell_items)
            if row_items:
                items.append(row_items)
                row_no+=1
    if not items:
        return []
    if el.get("table_bordered") or context.get("show_grid"):
        w=0.5
        style.append(("GRID",(0,0),(-1,-1),w,colors.black))
    col_widths=None
    if el.get("col_widths") and len(el["col_widths"])==num_cols:
        res=el["col_widths"]
        tot=sum(res)
        col_widths=[str(int(w*100/tot))+"%" for w in res]
    print("col_widths",col_widths)
    content=Table(items,style=style,colWidths=col_widths,ident="table")
    pad_left=(el.get("margin_left") or 0)/6*mm
    pad_right=(el.get("margin_right") or 0)/6*mm
    pad_top=(el.get("margin_top") or 0)/6*mm
    pad_bottom=(el.get("margin_bottom") or 0)/6*mm
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),pad_left),
        ("RIGHTPADDING",(0,0),(-1,-1),pad_right),
        ("TOPPADDING",(0,0),(-1,-1),pad_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad_bottom),
        ]
    return [Table([[content]],style=style,ident="table_cont")]

def replace_fields(s,data,model=None):
    #print("replace_fields",s,model)
    def _replace_expr_fmt_money(m):
        path=m.group(1)
        val=utils.get_data_path(data,path)
        if val is None:
            return ""
        return utils.format_money(val)
    def _replace_expr_fmt_hours(m):
        path=m.group(1)
        val=utils.get_data_path(data,path)
        if val is None:
            return ""
        return utils.format_hours(val)
    def _replace_expr_fmt_date(m):
        path=m.group(1)
        fmt=m.group(2)
        val=utils.get_data_path(data,path)
        if val is None:
            return ""
        return utils.format_date(val,fmt)
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
    s=re.sub("\{fmt_money\((.*?)\)\}",_replace_expr_fmt_money,s) # XXX
    s=re.sub("\{fmt_hours\((.*?)\)\}",_replace_expr_fmt_hours,s) # XXX
    s=re.sub("\{fmt_date\((.*?),\"(.*?)\"\)\}",_replace_expr_fmt_date,s) # XXX
    s=re.sub("\{(.*?)\}",_replace_expr,s)
    #print("replace_fields => %s"%res)
    return s 

def render_text(doc,el,context):
    print("render_text",el.get("name"),el)
    name=el.get("name")
    contents=el.get("contents")
    form_data=context.get("form_data") or {}
    if name and form_data.get(name):
        contents=form_data[name]
    align=el.get("align") or "left"
    font_size=int(context.get("font_size") or 8)
    if el.get("font_size"):
        font_size=int(el["font_size"])
    line_height=int(context.get("line_height") or 8)
    if el.get("line_height"):
        line_height=int(el["line_height"])
    bg_color=el.get("background_color")
    style = ParagraphStyle(
        name="Normal",
        fontSize=font_size,
        backColor=bg_color,
        leading=line_height,
        alignment={"left":TA_LEFT,"center":TA_CENTER,"right":TA_RIGHT,"justify":TA_JUSTIFY}[align],
    )
    if el.get("visibility"):
        vis_name=el["visibility"]
        data=context.get("data") or {}
        visibility=utils.get_data_path(data,vis_name)
        if not visibility:
            return ""
    if False:#name: XXX
        print("name",name)
        data=context.get("data") or {}
        val=utils.get_data_path(data,name)
        if val is None:
            val=""
        if name.find("date")!=-1: # FIXME
            try:
                d=datetime.strptime(val,"%Y-%m-%d")
                val=d.strftime("%d/%m/%Y")
            except Exception as e:
                print("ERROR: %s"%e)
        text=str(val)
        p=Paragraph(text,style)
        lines=[p]
    elif contents:
        data=context.get("data") or {}
        model=context.get("model")
        ops=contents.get("ops",[])
        print("ops",ops)
        indent_lines={}
        list_types={}
        def _finish_lists(indent_level):
            print("_finish_lists",indent_level)
            #print("BEFORE",indent_lines)
            if not indent_lines:
                return
            max_level=max(indent_lines.keys())
            for i in range(max_level,indent_level-1,-1):
                lines=indent_lines.setdefault(i,[])
                up_lines=indent_lines.get(i+1)
                if up_lines:
                    kw={}
                    indent_lines[i+1]=[]
                    list_type=list_types.get(i+1)
                    if list_type=="bullet":
                        bullet_type="bullet"
                        kw["start"]=u"\u2022"
                    elif list_type=="ordered":
                        bullet_type="1"
                    else:
                        bullet_type=None
                    print("  create list level %s (%s lines, list_type=%s)"%(i+1,len(up_lines),list_type))
                    if bullet_type:
                        kw["bulletType"]=bullet_type
                    if el.get("bullet_text"):
                        kw["start"]=el["bullet_text"]
                    list_flow=ListFlowable(up_lines,bulletFontSize=10,**kw)
                    lines.append(list_flow)
            #print("AFTER",indent_lines)
        def _add_line(html,style,list_type=None,indent=0):
            print("_add_line list_type=%s indent=%s '%s'"%(list_type,indent,html))
            if html.strip()=="":
                html="&nbsp;"
            _finish_lists(indent)
            p=Paragraph(html,style)
            lines=indent_lines.setdefault(indent,[])
            lines.append(p)
            list_types[indent]=list_type
        def _add_content(content,style,list_type=None,indent=0):
            print("_add_content list_type=%s indent=%s '%s'"%(list_type,indent,content))
            if list_type:
                indent+=1
            content=content.replace("<b></b>","") # XXX
            lines=content.split("\n")
            for line in lines[:-1]:
                _add_line(line,style)
            #if lines[-1].strip(): # XXX
            #    _add_line(lines[-1],style,list_type,indent)
            if lines[-1]: # XXX
                _add_line(lines[-1],style,list_type,indent)
        html=""
        for op in ops:
            print("-"*80)
            print("op",op)
            insert=op.get("insert")
            attrs=op.get("attributes",{})
            if insert:
                if insert=="\n":
                    align=attrs.get("align","left")
                    style = ParagraphStyle(
                        name="Normal",
                        fontSize=font_size,
                        leading=line_height,
                        alignment={"left":TA_LEFT,"center":TA_CENTER,"right":TA_RIGHT,"justify":TA_JUSTIFY}[align],
                    )
                    html=replace_fields(html,data,model)
                    html=html.replace("<b></b>","") # XXX
                    if html:
                        list_type=attrs.get("list")
                        indent=attrs.get("indent") or 0
                        _add_content(html,style,list_type,indent)
                    html=""
                elif insert:
                    if attrs.get("bold"):
                        insert="<b>"+insert+"</b>"
                    if attrs.get("color"):
                        color=attrs["color"]
                        insert="<font color=\"%s\">%s</font>"%(color,insert)
                    html+=insert
        _finish_lists(0)
        style = ParagraphStyle(
            name="Normal",
            fontSize=font_size,
            leading=line_height,
        )
        html=replace_fields(html,data,model)
        if html:
            _add_content(html,style)
        lines=indent_lines.get(0,[])
    else:
        text="N/A"
        p=Paragraph(text,style)
        lines=[p]
    if not lines:
        return []
    #return lines # XXX
    pad_top=(el.get("padding_top") or 0)/6*mm
    pad_right=(el.get("padding_right") or 0)/6*mm
    pad_bottom=(el.get("padding_bottom") or 0)/6*mm
    pad_left=(el.get("padding_left") or 0)/6*mm
    content_style=[
        ("LEFTPADDING",(0,0),(-1,-1),pad_left),
        ("RIGHTPADDING",(0,0),(-1,-1),pad_right),
        ("TOPPADDING",(0,0),(-1,-1),pad_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad_bottom),
        ]
    if el.get("border_width") or context.get("show_grid"):
        w=float(el.get("border_width",1))
        content_style.append(("GRID",(0,0),(-1,-1),w,colors.black))
    if el.get("border_top_width"):
        w=float(el.get("border_top_width",1))
        content_style.append(("LINEABOVE",(0,0),(-1,-0),w,colors.black))
    if el.get("border_bottom_width"):
        w=float(el.get("border_bottom_width",1))
        content_style.append(("LINEBELOW",(0,0),(-1,0),w,colors.black))
    if el.get("background_color"):
        col=HexColor(el["background_color"])
        content_style.append(("BACKGROUND",(0,0),(-1,-1),col))
    content=[Table([[lines]],colWidths=["100%"],style=content_style,ident="text")]

    margin_top=(el.get("margin_top") or 0)/6*mm
    margin_right=(el.get("margin_right") or 0)/6*mm
    margin_bottom=(el.get("margin_bottom") or 0)/6*mm
    margin_left=(el.get("margin_left") or 0)/6*mm
    container_style=[
        ("LEFTPADDING",(0,0),(-1,-1),margin_left),
        ("RIGHTPADDING",(0,0),(-1,-1),margin_right),
        ("TOPPADDING",(0,0),(-1,-1),margin_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),margin_bottom),
        ]
    return [Table([[content]],colWidths=["100%"],style=container_style,ident="text_container")]

def render_image(doc,el,context):
    print("render_image")
    image_file=el.get("image_file")
    barcode_type=el.get("barcode_type")
    if not image_file and not barcode_type:
        raise Exception("Missing image file or barcode type")
    if image_file:
        if image_file.startswith("https://"):
            url=image_file
            r=random.randint(0,100)
            path="/tmp/image-%s.png"%r # XXX
            try:
                urllib.request.urlretrieve(url,path)
            except:
                raise Exception("Failed to retrieve image: %s"%url)
        else:
            path=utils.get_file_path(image_file)
        rd = ImageReader(path)
        iw,ih=rd.getSize()
        ratio=iw/ih
        if el.get("height"):
            height=int(el.get("height"))
        else:
            height=60
        w=height*ratio/6
        h=height/6
        img=Image(path,width=w*mm,height=h*mm)
        align=el.get("align","left").upper()
        style=[
            ("ALIGN",(0,0),(-1,-1),align),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ]
        if context.get("show_grid"):
            style.append(("GRID",(0,0),(-1,-1),1,colors.black))
        content=Table([[img]],colWidths=["100%"],style=style,ident="image")
    elif barcode_type: 
        barcode_value=el.get("barcode_value")
        if barcode_value:
            data=context.get("data") or {}
            val=replace_fields(barcode_value,data)
        else:
            val=""
        if barcode_type=="qr":
            barcode=qr.QrCodeWidget(val)
        elif barcode_type=="code128":
            barcode=code128.Code128(val,barHeight=12*mm)
        else:
            raise Exception("Unsupported barcode type: %s"%barcode_type)
        if barcode_type=="qr":
            bounds = barcode.getBounds()
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            dw=int(el["width"])*mm if el.get("width") else 40*mm
            dh=int(el["height"])*mm if el.get("height") else 40*mm
            d=Drawing(dw, dh, transform=[dw/width,0,0,dh/height,0,0])
            d.add(barcode)
        else:
            d=barcode
        align=el.get("align","left").upper()
        style=[
            ("ALIGN",(0,0),(-1,-1),align),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ]
        if context.get("show_grid"):
            style.append(("GRID",(0,0),(-1,-1),1,colors.black))
        content=Table([[d]],colWidths=["100%"],style=style,ident="image")
    pad_left=(el.get("margin_left") or 0)/6*mm
    pad_right=(el.get("margin_right") or 0)/6*mm
    pad_top=(el.get("margin_top") or 0)/6*mm
    pad_bottom=(el.get("margin_bottom") or 0)/6*mm
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),pad_left),
        ("RIGHTPADDING",(0,0),(-1,-1),pad_right),
        ("TOPPADDING",(0,0),(-1,-1),pad_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad_bottom),
        ]
    return [Table([[content]],style=style,ident="image_cont")]

def render_field(doc,el,context):
    print("render_field")
    name=el.get("name")
    if not name:
        raise Exception("Missing field name")
    form_data=context.get("form_data") or {}
    val=utils.get_data_path(form_data,name)
    if val is None:
        val_str=""
    else:
        val_str=str(val)
    align=el.get("align") or "left"
    font_size=int(context.get("font_size") or 8)
    if el.get("font_size"):
        font_size=int(el["font_size"])
    style = ParagraphStyle(
        name="Normal",
        fontSize=font_size,
        alignment={"left":TA_LEFT,"center":TA_CENTER,"right":TA_RIGHT,"justify":TA_JUSTIFY}[align],
    )
    content=Paragraph(val_str,style)
    pad_left=(el.get("margin_left") or 0)/6*mm
    pad_right=(el.get("margin_right") or 0)/6*mm
    pad_top=(el.get("margin_top") or 0)/6*mm
    pad_bottom=(el.get("margin_bottom") or 0)/6*mm
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),pad_left),
        ("RIGHTPADDING",(0,0),(-1,-1),pad_right),
        ("TOPPADDING",(0,0),(-1,-1),pad_top),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad_bottom),
        ]
    return [Table([[content]],style=style,ident="field_cont")]

def render_list(doc,el,context):
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
        items+=render_element(doc,child,ctx)
    if not items:
        return []
    style=[
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ]
    if context.get("show_grid"):
        style.append(("GRID",(0,0),(-1,-1),1,colors.black))
    return [Table([[i] for i in items],colWidths=["100%"],style=style,ident="list_%s"%name)]

def render_element(doc,el,context):
    if el["type"]=="data":
        return render_data(doc,el,context)
    elif el["type"]=="box":
        return render_box(doc,el,context)
    elif el["type"]=="columns":
        return render_columns(doc,el,context)
    elif el["type"]=="table":
        return render_table(doc,el,context)
    elif el["type"]=="text":
        return render_text(doc,el,context)
    elif el["type"]=="image":
        return render_image(doc,el,context)
    elif el["type"]=="field":
        return render_field(doc,el,context)
    elif el["type"]=="list":
        return render_list(doc,el,context)
    else:
        raise Exception("Unsupported element type: %s"%el["type"])

def render_page_pdf_reportlab(layout,props):
    context={}
    #context["show_grid"]=True # XXX
    if layout.get("date_format"):
        context["date_format"]=layout["date_format"]
    if layout.get("font_size"):
        context["font_size"]=layout["font_size"]
    if layout.get("line_height"):
        context["line_height"]=int(layout["line_height"])
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
    #pdfmetrics.registerFont(TTFont('Noto','/home/aln/fonts/NotoSansCJKtc-Regular.ttf'))
    #pdfmetrics.registerFont(TTFont('Noto-Bold','/home/aln/fonts/NotoSansCJKtc-Bold.ttf'))
    pdf_merger = PdfFileMerger()
    for (i,page_context) in enumerate(page_contexts):
        print("render page %s"%i)
        print("context",page_context)
        out_path="/tmp/report_%s.pdf"%i
        margin_top=layout.get("page_margin_top",10) or 0
        margin_right=layout.get("page_margin_right",10) or 0
        margin_bottom=layout.get("page_margin_bottom",10) or 0
        margin_left=layout.get("page_margin_left",10) or 0
        if layout.get("width") and layout.get("height"):
            page_size=(int(layout["width"])*mm,int(layout["height"])*mm)
        else:
            page_size=A4
        doc = SimpleDocTemplate(out_path,pagesize=page_size,topMargin=margin_top*mm,rightMargin=margin_right*mm,leftMargin=margin_left*mm,bottomMargin=margin_bottom*mm)
        #doc = SimpleDocTemplate(out_path,pagesize=page_size,topMargin=0,leftMargin=0,bottomMargin=0,rightMargin=0)
        items=[]
        for el in layout["elements"]:
            if el.get("footer"):
                continue
            items+=render_element(doc,el,page_context)

        def draw_page(canvas,doc):
            items=[]
            for el in layout["elements"]:
                if not el.get("footer"):
                    continue
                items+=render_element(doc,el,page_context)
            Frame(0, 0, doc.width+doc.leftMargin+doc.rightMargin, 25*mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0).addFromList(items, canvas)

        if layout.get("show_page_no"):
            doc.build(items,canvasmaker=NFCanvas,onFirstPage=draw_page,onLaterPages=draw_page)
        else:
            doc.build(items,onFirstPage=draw_page,onLaterPages=draw_page)
        pdf_merger.append(out_path)
    report_path="/tmp/report.pdf"
    pdf_merger.write(report_path)
    out=open(report_path,"rb").read()
    filename="report.pdf"
    print("XXX filename",layout.get("filename"))
    if layout.get("filename"):
        data=context.get("data") or {}
        model=context.get("model")
        filename=replace_fields(layout["filename"],data,model)
    return {
        "data": out,
        "filename": filename,
    }

def render_page_pdf_web_old(page,active_id,ids,layout):
    print("P"*80)
    print("render_page_pdf_web",page,active_id,ids)
    dbname=database.get_active_db()
    #url="https://pages.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    #url="http://pages.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    if active_id:
        url="http://pages-prod2.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    elif ids:
        url="http://pages-prod2.netforce.com/?db=%s&page=%s&ids=%s"%(dbname,page,json.dumps(ids))
    else:
        raise Exception("Missing active_id or ids")
    user_id=access.get_active_user()
    company_id=access.get_active_company()
    token=access.get_access_token()
    url+="&user_id=%s&company_id=%s&token=%s"%(user_id,company_id,token)
    print("report url",url)
    tmp_f=tempfile.NamedTemporaryFile(suffix=".pdf",delete=False)
    path=tmp_f.name
    tmp_f.close()
    print("path",path)
    #res=os.system("wkhtmltopdf \"%s\" %s"%(url,path)) #XXX
    #res=os.system("chromium-browser --headless --disable-gpu --print-to-pdf=%s \"%s\""%(path,url))
    cmd=["/home/nf/nf_base/netforce_report/netforce_report/web_to_pdf/web_to_pdf.js",url,path]
    if layout.get("width") and layout.get("height"):
        size="%sx%s"%(layout["width"],layout["height"])
        cmd.append(size)
    p=subprocess.Popen(cmd)
    try:
        p.wait(60)
    except Exception as e:
        p.kill()
        raise Exception("Report time-out: %s"%e)
    data=open(path,"rb").read()
    os.unlink(path)
    try:
        title=open("/tmp/report_web_title.txt","r").read() # XXX
        if not title:
            raise Exception("Missing title")
        filename=title.replace(".pdf","")+".pdf"
    except:
        filename="report.pdf"
    return {
        "data": data,
        "filename": filename,
    }

def render_page_html_web(page,active_id=None,ids=None,layout=None,params=None):
    print("P"*80)
    print("render_page_html_web",page,active_id,ids,params)
    dbname=database.get_active_db()
    user_id=access.get_active_user()
    token=access.get_access_token()
    company_id=access.get_active_company()
    #url="https://pages.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    #url="http://pages.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    if active_id:
        url="https://pages-prod2.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    elif ids:
        url="https://pages-prod2.netforce.com/?db=%s&page=%s&ids=%s"%(dbname,page,json.dumps(ids))
    elif params:
        url="https://pages-prod2.netforce.com/?db=%s&page=%s&user_id=%s&company_id=%s&token=%s&%s"%(dbname,page,user_id,company_id,urllib.parse.quote_plus(token),urllib.parse.urlencode(params))
    else:
        raise Exception("Missing url")
    print("$"*80)
    print("$"*80)
    print("$"*80)
    print("html report url",url)
    #path="/tmp/report_web_%s.html"%company_id # XXX
    #res=os.system("wkhtmltopdf \"%s\" %s"%(url,path)) #XXX
    #res=os.system("chromium-browser --headless --disable-gpu --print-to-pdf=%s \"%s\""%(path,url))
    fd,path=tempfile.mkstemp(suffix=".html")
    try:
        print("path",path)
        cmd=["/home/nf/nf_base/netforce_report/netforce_report/web_to_pdf/web_to_html.js",url,path]
        print("cmd",cmd)
        if layout.get("width") and layout.get("height"):
            size="%sx%s"%(layout["width"],layout["height"])
            cmd.append(size)
        p=subprocess.Popen(cmd)
        try:
            return_code=p.wait(15)
        except Exception as e:
            p.kill()
            raise Exception("Report time-out: %s"%e)
        if return_code!=0:
            raise Exception("Invalid return code: %s"%return_code)
        data=open(path,"rb").read()
    finally:
        os.unlink(path)
    data=data.decode("utf-8")
    return {
        "data": data,
    }

def render_page_txt(page,active_id,ids,layout):
    print("P"*80)
    print("render_page_txt",page,active_id,ids)
    dbname=database.get_active_db()
    if active_id:
        url="http://pages-test.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    elif ids:
        url="http://pages-test.netforce.com/?db=%s&page=%s&ids=%s"%(dbname,page,json.dumps(ids))
    else:
        raise Exception("Missing active_id or ids")
    print("report url",url)
    path="/tmp/report_web.txt"
    cmd="links -dump \"%s\" > %s"%(url,path)
    print("cmd",cmd)
    os.system(cmd)
    data=open(path,"rb").read().decode("utf-8")
    data=data.replace("Link: preload\n","") # XXX
    filename="report.txt"
    return {
        "data": data,
        "filename": filename,
    }

def render_page_pdf_web(page,active_id,ids,layout):
    print("P"*80)
    print("render_page_pdf_web",page,active_id,ids)
    dbname=database.get_active_db()
    #url="https://pages.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    #url="http://pages.netforce.com/?db=%s&page=%s&active_id=%s"%(dbname,page,active_id)
    company_id=access.get_active_company()
    if active_id:
        url="http://pages-prod2.netforce.com/?db=%s&page=%s&active_id=%s&company_id=%s"%(dbname,page,active_id,company_id)
    elif ids:
        url="http://pages-prod2.netforce.com/?db=%s&page=%s&ids=%s&company_id=%s"%(dbname,page,json.dumps(ids),company_id)
    else:
        raise Exception("Missing active_id or ids")
    print("report url",url)
    params={
        "url": url,
    }
    if layout.get("width") and layout.get("height"):
        params["size"]="%sx%s"%(layout["width"],layout["height"])
    req=requests.get("http://localhost:8200/web_to_pdf",params=params)
    data=req.content
    try:
        h = req.headers.get('content-disposition')
        if h:
            filename = re.findall("filename=(.+)", h)[0]
            filename=filename.replace(".pdf","")+".pdf"
        else:
            filename="report.pdf"
    except:
        filename="report.pdf"
    return {
        "data": data,
        "filename": filename,
    }
