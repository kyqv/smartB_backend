from netforce.model import fields,get_model
from netforce import utils
import json
from decimal import *
import re
try:
    import xlsxwriter
except:
    print("Warning: failed to import xlsxwriter")
try:
    from fpdf import FPDF
except:
    print("Warning: failed to import fpdf")
try:
    from colour import Color
except:
    print("Warning: failed to import colour")
import dateutil
try:
    from PIL import Image
except:
    print("Warning: failed to import PIL")
try:
    import pyqrcode
except:
    print("Warning: failed to import pyqrcode")
import os
try:
    from simpleeval import simple_eval
except:
    raise Exception("Failed to import simpleeval")

def get_fields_nfjson(layout_str,model):
    fields=[]
    layout=json.loads(layout_str)
    cells=layout.get("cells",[])
    rows=layout.get("rows",[])
    settings=layout.get("settings",{})
    for cell in cells:
        if cell.get("type")=="field":
            field=cell.get("value")
            if field:
                fields.append(field)
        elif cell.get("type")=="text":
            def _replace_expr(m):
                path=m.group(1)
                try:
                    f=get_field_by_path(model,path)
                except: # XXX
                    f=None
                if f:
                    fields.append(path)
            val=cell.get("value")
            if val:
                re.sub("\{(.*?)\}",_replace_expr,val) # XXX: don't use sub
    for row in rows:
        field=row.get("field")
        if field:
            fields.append(field)
    field=settings.get("field")
    if field:
        fields.append(field)
    fields=list(set(fields))
    return fields

def cell_name_to_coords(name):
    col_no=ord(name[0])-ord("A")
    row_no=int(name[1:])-1
    return [row_no,col_no]

# XXX: remove this
def nfjson_get_row(layout,row_no):
    name=str(row_no+1)
    for row in layout.get("rows"):
        if row.get("name")==name:
            return row
    return {
        "name": name,
    }

def get_path_val(data,path):
    n,_,rpath=path.partition(".")
    if not isinstance(data,dict):
        return None
    v=data.get(n)
    if not v or not rpath:
        return v
    return get_path_val(v,rpath)

def get_field_by_path(model,path):
    n,_,rpath=path.partition(".")
    m=get_model(model)
    f=m._fields.get(n)
    if not f:
        return None
    if not rpath:
        return f
    return get_field_by_path(f.relation,rpath)

def conv_float(s):
    print("conv_float",s)
    try:
         n=float(str(s).replace(",",""))
    except:
         n=0
    print("=>",n)
    return n

FUNCTIONS={
    "FLOAT": conv_float,
}

def eval_formula(formula, context={}):
    print("eval_formula",formula)
    try:
        val=simple_eval(formula,functions=FUNCTIONS,names=context)
    except Exception as e:
        val="Error: %s"%e
    print("=> val=%s"%val)
    return val

current_page=0

def render_template_nfjson_pdf(layout_str,data_list,model,convert_png=False):
    print("render_template_nfjson_pdf",data_list,model)
    if isinstance(data_list,dict):
        data_list=[data_list]
    layout=json.loads(layout_str)
    if layout.get("page_format"):
        fmt=layout["page_format"]
    else:
        fmt="A4"
    pdf=FPDF(format=fmt)
    pdf.add_font("Loma","","/usr/share/fonts/truetype/tlwg/Loma.ttf",uni=True)
    pdf.add_font("Loma","B","/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf",uni=True)
    pdf.add_font("DejaVu","","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",uni=True)
    pdf.add_font("DejaVu","B","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",uni=True)
    pdf.add_font("Droid","","/usr/share/fonts/truetype/droid/DroidSans.ttf",uni=True)
    pdf.add_font("Droid","B","/usr/share/fonts/truetype/droid/DroidSans-Bold.ttf",uni=True)
    settings=layout.get("settings") or {}
    cols=layout.get("cols")
    if not cols:
        raise Exception("Missing cols")
    rows=layout.get("rows")
    if not rows:
        raise Exception("Missing rows")
    cells=layout.get("cells") or []
    boxes=layout.get("boxes") or []
    pdf.set_margins(0,0,0)
    pdf.set_auto_page_break(False)
    line_width=0.2
    for report_data in data_list:
        field=settings.get("field")
        if field:
            page_data_list=get_path_val(report_data,field)
            page_prefix=field+"."
        else:
            page_data_list=[report_data]
            page_prefix=None
        global current_page
        current_page=1
        for page_data in page_data_list:
            pdf.add_page()
            bg_image=settings.get("bg_image")
            if bg_image:
                path=utils.get_file_path(bg_image)
                pdf.set_xy(0,0)
                pdf.image(path,w=pdf.w,h=pdf.h)
            def _get_row_height(data,model,tmpl_row_no,out_top,prefix=None):
                print("_get_row_height",model,tmpl_row_no,out_top,prefix)
                if tmpl_row_no>=len(rows):
                    return 0 # XXX
                row=rows[tmpl_row_no]
                def _get_text_num_lines(s,cell_w):
                    #print("text_num_lines",s,cell_w)
                    n=0
                    for l in s.split("\n"):
                        l=l.strip()
                        if not l:
                            continue
                        line_w=pdf.get_string_width(l)
                        if line_w<=cell_w:
                            n+=1
                        elif line_w<=2*cell_w:
                            n+=2 # XXX
                        elif line_w<=3*cell_w:
                            n+=3 # XXX
                        elif line_w<=4*cell_w:
                            n+=4 # XXX
                        elif line_w<=5*cell_w:
                            n+=5 # XXX
                        else:
                            n+=6# XXX
                    #print("n =>",n)
                    return n
                max_num_lines=1
                for cell in cells: # XXX: get row height
                    if not cell.get("expand"):
                        continue
                    if not cell.get("type"):
                        continue
                    name=cell["name"]
                    res=cell_name_to_coords(name)
                    row_no=res[0]
                    col_no=res[1]
                    if row_no!=tmpl_row_no:
                        continue
                    #print("cell name",name)
                    col=cols[col_no]
                    row=rows[row_no]
                    x0=col["left"]*pdf.w/1000
                    #print("x0",x0,"y0",y0)
                    colspan=cell.get("colspan") or 1
                    span_col_no=min(col_no+colspan-1,len(cols)-1)
                    if span_col_no < len(cols)-1:
                        x1=cols[span_col_no+1]["left"]*pdf.w/1000-line_width
                    else:
                        x1=(cols[span_col_no]["left"]+cols[span_col_no]["width"])*pdf.w/1000
                    rowspan=cell.get("rowspan") or 1
                    font_size=cell.get("font_size") or 7
                    font_name=cell.get("font_name") or "Loma"
                    if cell.get("bold"):
                        pdf.set_font(font_name, 'B', font_size)
                    else:
                        pdf.set_font(font_name, '', font_size)
                    cell_type=cell["type"]
                    if cell_type=="field":
                        field=cell.get("value")
                        if prefix and field:
                            field=field[len(prefix):]
                        val=get_path_val(data,field) if field else ""
                        if val is None:
                            val=""
                        elif isinstance(val,Decimal):
                            val=utils.format_money(val)
                        else:
                            val=str(val)
                        if val:
                            fmt=cell.get("format")
                            if fmt:
                                if fmt=="0,0": # XXX
                                    val=str(int(float(val.replace(",","")))) # XXX
                                elif fmt=="AMOUNT_WORDS": # XXX
                                    f=float(val.replace(",",""))
                                    val=utils.num2words_cents(f).upper()
                                elif fmt=="DD/MM/YYYY": # XXX
                                    val=dateutil.parser.parse(val).strftime("%d/%m/%Y")
                                else:
                                    raise Exception("Invalid format: %s"%fmt)
                        num_lines=_get_text_num_lines(val,x1-x0)
                        if num_lines>max_num_lines:
                            max_num_lines=num_lines
                print("max_num_lines",max_num_lines)
                h=row["height"]*max_num_lines
                if row.get("extend_to"):
                    h2=max(0,row["extend_to"]-out_top)
                    if h2>h:
                        h=h2
                return h
            def _render_row(data,model,tmpl_row_no,out_top,row_h,prefix=None):
                print("_render_row",model,tmpl_row_no,out_top,prefix) 
                if tmpl_row_no>=len(rows):
                    print("WARNING: row out of range: %s"%tmpl_row_no)
                    return
                row=rows[tmpl_row_no]
                for cell in cells:
                    if not cell.get("type"):
                        continue
                    name=cell["name"]
                    res=cell_name_to_coords(name)
                    row_no=res[0]
                    col_no=res[1]
                    if row_no!=tmpl_row_no:
                        continue
                    #print("cell name",name)
                    col=cols[col_no]
                    row=rows[row_no]
                    x0=col["left"]*pdf.w/1000
                    y0=out_top*pdf.h/1000
                    pdf.set_xy(x0,y0)
                    #print("x0",x0,"y0",y0)
                    colspan=cell.get("colspan") or 1
                    rowspan=cell.get("rowspan") or 1
                    span_col_no=min(col_no+colspan-1,len(cols)-1)
                    if span_col_no < len(cols)-1:
                        x1=cols[span_col_no+1]["left"]*pdf.w/1000-line_width
                    else:
                        x1=(cols[span_col_no]["left"]+cols[span_col_no]["width"])*pdf.w/1000
                    y1=(out_top+row_h)*pdf.h/1000-line_width
                    y1_line=(out_top+row["height"])*pdf.h/1000-line_width
                    print("  cell ",name,"x0",x0,"y0",y0,"x1",x1,"y1",y1,"w",pdf.w,"h",pdf.h)
                    border=""
                    if cell.get("border_left"):
                        border+="L"
                    if cell.get("border_right"):
                        border+="R"
                    if cell.get("border_top"):
                        border+="T"
                    if cell.get("border_bottom"):
                        border+="B"
                    align="L"
                    res=cell.get("align")
                    if res:
                        if res=="right":
                            align="R"
                        elif res=="center":
                            align="C"
                    font_size=cell.get("font_size") or 7
                    font_name=cell.get("font_name") or "Loma"
                    if cell.get("bold"):
                        pdf.set_font(font_name, 'B', font_size)
                    else:
                        pdf.set_font(font_name, '', font_size)
                    color=cell.get("color")
                    if color:
                        c=Color(color)
                        pdf.set_text_color(int(c.red*255),int(c.green*255),int(c.blue*255))
                    else:
                        pdf.set_text_color(0)
                    cell_type=cell["type"]
                    if cell_type=="text":
                        val=cell.get("value") or ""
                        def _replace_expr(m):
                            global current_page
                            path=m.group(1)
                            if prefix:
                                path=path[len(prefix):]
                            if path[0]=="_":
                                if path=="_current_page":
                                    v=current_page
                                elif path=="_total_pages":
                                    #v=total_pages
                                    v=current_page # XXX
                                else:
                                    raise Exception("Invalid variable: %s"%path)
                            else:
                                v=get_path_val(data,path)
                            return str(v)
                        val=re.sub("\{(.*?)\}",_replace_expr,val)
                        color=cell.get("bg_color")
                        if color:
                            c=Color(color)
                            pdf.set_fill_color(int(c.red*255),int(c.green*255),int(c.blue*255))
                        else:
                            pdf.set_fill_color(r=255,g=255,b=255)
                        pdf.cell(x1-x0, y1-y0, "", border=border, fill=True)
                        """
                        y=y0+1 # XXX
                        line_h=3 # XXX
                        for line in val.split("\n"):
                            pdf.set_xy(x0,y)
                            pdf.cell(x1-x0, line_h, line, align=align)
                            y+=line_h
                        """
                        fmt=cell.get("format")
                        if fmt:
                            if fmt=="0.00": # XXX
                                val=str("%.2f"%float(val.replace(",",""))) # XXX
                        if cell.get("expand"):
                            pdf.set_xy(x0,y0)
                            pdf.cell(x1-x0, y1-y0, "", border=border, align=align, fill=True)
                            pdf.set_xy(x0,y0)
                            #pdf.multi_cell(x1-x0, y1_line-y0, val, align=align)
                            pdf.multi_cell(x1-x0, 5, val, align=align) # XXX
                        else:
                            pdf.set_xy(x0,y0)
                            pdf.cell(x1-x0, y1-y0, val, border=border, align=align, fill=True)
                    elif cell_type=="field":
                        field=cell.get("value")
                        if prefix and field:
                            field=field[len(prefix):]
                        val=get_path_val(data,field) if field else ""
                        if val is None:
                            val=""
                        elif isinstance(val,Decimal):
                            val=utils.format_money(val)
                        else:
                            val=str(val)
                        if val:
                            fmt=cell.get("format")
                            if fmt:
                                if fmt=="0,0": # XXX
                                    val=str(int(float(val.replace(",","")))) # XXX
                                elif fmt=="0.0": # XXX
                                    val="%.1f"%float(val.replace(",","")) # XXX
                                elif fmt=="AMOUNT_WORDS": # XXX
                                    f=float(val.replace(",",""))
                                    val=utils.num2words_cents(f).upper()
                                elif fmt=="AMOUNT_WORDS_DOLLAR": # XXX
                                    f=float(val.replace(",",""))
                                    val=utils.num2words_cents(f,currency="Dollar").upper()
                                elif fmt=="DD/MM/YYYY": # XXX
                                    val=dateutil.parser.parse(val).strftime("%d/%m/%Y") # XXX
                                elif fmt=="QRCODE": # XXX
                                    pass
                                else:
                                    raise Exception("Invalid format: %s"%fmt)
                        color=cell.get("bg_color")
                        if color:
                            c=Color(color)
                            pdf.set_fill_color(int(c.red*255),int(c.green*255),int(c.blue*255))
                        else:
                            pdf.set_fill_color(r=255,g=255,b=255)
                        #pdf.cell(x1-x0, y1-y0, val, border=border, align=align, fill=True)
                        if cell.get("format")=="QRCODE":
                            pdf.set_xy(x0,y0)
                            val=str(val)
                            #val="1234" # XXX
                            qr=pyqrcode.create(val or "")
                            path="/tmp/qrcode.png"
                            #qr.png(path,quiet_zone=0,scale=8)
                            qr.png(path,scale=8)
                            pdf.image(path,w=x1-x0) # XXX
                        elif cell.get("expand"):
                            pdf.cell(x1-x0, y1-y0, "", border=border, align=align, fill=True)
                            pdf.set_xy(x0,y0)
                            pdf.multi_cell(x1-x0, y1_line-y0, val, align=align)
                        elif cell.get("wrap_text"):
                            pdf.cell(x1-x0, y1-y0, "", border=border, align=align, fill=True)
                            pdf.set_xy(x0,y0)
                            pdf.multi_cell(x1-x0, 3, val, align=align) # XXX: line height
                        else:
                            pdf.cell(x1-x0, y1-y0, val, border=border, align=align, fill=True)
                    elif cell_type=="image":
                        val=cell.get("value")
                        if not val:
                            raise Exception("Missing filename in image (cell %s)"%name)
                        path=utils.get_file_path(val)
                        if not os.path.exists(path):
                            raise Exception("Image not found: %s"%val)
                        #pdf.image(path,w=x1-x0,h=y1-y0)
                        if align=="C":
                            img=Image.open(path)
                            img_w,img_h=img.size
                            ratio=img_w/float(img_h)
                            img_w2=(y1-y0)*ratio
                            pdf.set_x((x1+x0)/2-img_w2/2)
                        elif align=="R":
                            img=Image.open(path)
                            img_w,img_h=img.size
                            ratio=img_w/float(img_h)
                            img_w2=(y1-y0)*ratio*rowspan # XXX
                            pdf.set_x(x1-img_w2)
                        pdf.image(path,h=(y1-y0)*rowspan) # XXX
                    elif cell_type=="formula":
                        formula=cell.get("value")
                        if formula:
                            val=str(eval_formula(formula,data))
                        else:
                            val="N/A"
                        if val:
                            fmt=cell.get("format")
                            if fmt:
                                if fmt=="0.0": # XXX
                                    val="%.1f"%float(val.replace(",","")) # XXX
                        pdf.cell(x1-x0, y1-y0, val, border=border, align=align, fill=True)
            def _add_row(data,model,tmpl_row_no,out_top,prefix=None):
                print("-"*80)
                print("_add_row",model,tmpl_row_no,out_top,prefix) 
                row_h=_get_row_height(data,model,tmpl_row_no,out_top,prefix)
                print("==> row height:",row_h)
                max_bottom=row.get("max_bottom")
                if max_bottom is None:
                    max_bottom=1000-layout["margin_bottom"]
                if out_top+row_h>max_bottom:
                    print("="*80)
                    print("new_page")
                    repeat_bottom_str=row.get("repeat_rows_bottom")
                    if repeat_bottom_str:
                        repeat_bottom=[int(x.strip())-1 for x in repeat_bottom_str.split(",")]
                        for repeat_row_no in repeat_bottom:
                            h=_get_row_height(report_data,model,repeat_row_no,out_top)
                            res=_render_row(report_data,model,repeat_row_no,out_top,h)
                            out_top+=h
                    pdf.add_page()
                    global current_page
                    current_page+=1
                    new_page_top=row.get("new_page_top")
                    if new_page_top is None:
                        new_page_top=layout["margin_top"]
                    out_top=new_page_top
                    repeat_rows_str=row.get("repeat_rows")
                    if repeat_rows_str:
                        repeat_rows=[int(x.strip())-1 for x in repeat_rows_str.split(",")]
                        print("repeat_rows",repeat_rows)
                        for repeat_row_no in repeat_rows:
                            h=_get_row_height(report_data,model,repeat_row_no,out_top)
                            res=_render_row(report_data,model,repeat_row_no,out_top,h)
                            out_top+=h
                _render_row(data,model,tmpl_row_no,out_top,row_h,prefix)
                out_top+=row_h
                return out_top
            out_top=layout["margin_top"]
            for tmpl_row_no in range(len(rows)):
                row=rows[tmpl_row_no]
                if row.get("field"):
                    field=row["field"]
                    val=get_path_val(page_data,field) or ""
                    try:
                        f=get_field_by_path(model,field)
                        rmodel=f.relation if f else None
                    except: # XXX
                        rmodel=None
                    for rdata in val:
                        out_top=_add_row(rdata,rmodel,tmpl_row_no,out_top,field+".")
                else:
                    out_top=_add_row(page_data,model,tmpl_row_no,out_top)
            for box in boxes:
                x0=box["x"]*pdf.w/1000
                y0=box["y"]*pdf.h/1000
                x1=(box["x"]+box["w"])*pdf.w/1000
                y1=(box["y"]+box["h"])*pdf.h/1000
                border=""
                if box.get("border_left"):
                    border+="L"
                if box.get("border_right"):
                    border+="R"
                if box.get("border_top"):
                    border+="T"
                if box.get("border_bottom"):
                    border+="B"
                align="L"
                res=box.get("align")
                if res:
                    if res=="right":
                        align="R"
                    elif res=="center":
                        align="C"
                font_size=box.get("font_size") or 7
                if box.get("bold"):
                    pdf.set_font('Loma', 'B', font_size)
                else:
                    pdf.set_font('Loma', '', font_size)
                box_type=box.get("type")
                if box_type=="text":
                    val=box.get("value") or ""
                    def _replace_expr(m):
                        global current_page
                        path=m.group(1)
                        if path[0]=="_":
                            if path=="_current_page":
                                v=current_page
                            elif path=="_total_pages":
                                #v=total_pages
                                v=current_page # XXX
                            else:
                                raise Exception("Invalid variable: %s"%path)
                        else:
                            if page_prefix and path:
                                path=path[len(page_prefix):]
                            print("get_path_val",path,page_data)
                            v=get_path_val(page_data,path)
                        return str(v)
                    val=re.sub("\{(.*?)\}",_replace_expr,val)
                    if val:
                        fmt=box.get("format")
                        if fmt:
                            if fmt=="0,0": # XXX
                                val=str(int(float(val.replace(",","")))) # XXX
                            elif fmt=="AMOUNT_WORDS": # XXX
                                f=float(val.replace(",",""))
                                val=utils.num2words_cents(f).upper()
                            elif fmt=="DD/MM/YYYY": # XXX
                                val=dateutil.parser.parse(val).strftime("%d/%m/%Y")
                            else:
                                raise Exception("Invalid format: %s"%fmt)
                    pdf.set_xy(x0,y0)
                    pdf.cell(x1-x0, y1-y0, val, border=border, align=align)
                elif box_type=="field":
                    field=box.get("value")
                    if page_prefix and field:
                        field=field[len(page_prefix):]
                    val=get_path_val(page_data,field) if field else ""
                    if val is None:
                        val=""
                    elif isinstance(val,Decimal):
                        val=utils.format_money(val)
                    else:
                        val=str(val)
                    if val:
                        fmt=box.get("format")
                        if fmt:
                            if fmt=="0,0": # XXX
                                val=str(int(float(val.replace(",","")))) # XXX
                            elif fmt=="AMOUNT_WORDS": # XXX
                                f=float(val.replace(",",""))
                                val=utils.num2words_cents(f).upper()
                            elif fmt=="DD/MM/YYYY": # XXX
                                val=dateutil.parser.parse(val).strftime("%d/%m/%Y")
                            else:
                                raise Exception("Invalid format: %s"%fmt)
                    pdf.cell(x1-x0, y1-y0, val, border=border, align=align)
                elif box_type=="image":
                    val=box.get("value")
                    path=utils.get_file_path(val)
                    pdf.image(path,h=y1-y0)
    pdf.output("/tmp/report.pdf","F")
    if convert_png:
        #os.system("convert -density 150 /tmp/report.pdf -monochrome /tmp/report.png")
        os.system("convert -density 300 /tmp/report.pdf -threshold 50% /tmp/report.png")
        out=open("/tmp/report.png","rb").read()
        return out
    out=open("/tmp/report.pdf","rb").read()
    return out

"""
def render_template_nfjson_xlsx(layout_str,data,model):
    workbook=xlsxwriter.Workbook("/tmp/report.xlsx")
    sheet=workbook.add_worksheet()
    layout=json.loads(layout_str)
    num_cols=layout.get("num_cols") or 1
    num_rows=layout.get("num_rows") or 1
    def _render_row(data,model,tmpl_row_no,out_row_no,prefix=None):
        sheet.set_column(0,num_cols-1,15)
        cells=layout.get("cells") or []
        for cell in cells:
            name=cell["name"]
            print("cell name",name)
            res=cell_name_to_coords(name)
            row_no=res[0]
            col_no=res[1]
            if row_no!=tmpl_row_no:
                continue
            colspan=cell.get("colspan") or 1
            rowspan=cell.get("rowspan") or 1
            fmt=workbook.add_format()
            if cell.get("bold"):
                fmt.set_bold()
            if cell.get("align"):
                fmt.set_align(cell["align"])
            if cell.get("border_top"):
                fmt.set_top()
            if cell.get("border_bottom"):
                fmt.set_bottom()
            if cell.get("border_left"):
                fmt.set_left()
            if cell.get("border_right"):
                fmt.set_right()
            if colspan>1 or rowspan>1:
                sheet.merge_range(out_row_no,col_no,out_row_no+rowspan-1,col_no+colspan-1,"",fmt)
            cell_type=cell.get("type") or "text"
            if cell_type=="text":
                val=cell.get("value")
                sheet.write(out_row_no,col_no,val,fmt)
            elif cell_type=="field":
                field=cell.get("value")
                if prefix:
                    field=field[len(prefix):]
                val=get_path_val(data,field)
                val=str(val)
                sheet.write(out_row_no,col_no,val,fmt)
            elif cell_type=="image":
                val=cell.get("value")
                path=utils.get_file_path(val)
                sheet.insert_image(out_row_no,col_no,path)
    out_row_no=0
    for tmpl_row_no in range(num_rows):
        row=nfjson_get_row(layout,tmpl_row_no)
        if row.get("field"):
            field=row["field"]
            val=get_path_val(data,field) or ""
            f=get_field_by_path(model,field)
            if not isinstance(f,(fields.One2Many,fields.Many2Many)):
                raise Exception("Can not loop on field: %s"%field)
            rmodel=f.relation
            for rdata in val:
                _render_row(rdata,rmodel,tmpl_row_no,out_row_no,field+".")
                out_row_no+=1
        else:
            _render_row(data,model,tmpl_row_no,out_row_no)
            out_row_no+=1
    workbook.close()
    out=open("/tmp/report.xlsx","rb").read()
    return out
"""

def render_template_nfjson_xlsx(layout_str,data_list,model):
    print("render_template_nfjson_xlsx",data_list,model)
    workbook=xlsxwriter.Workbook("/tmp/report.xlsx")
    sheet=workbook.add_worksheet()
    if isinstance(data_list,dict):
        data_list=[data_list]
    layout=json.loads(layout_str)
    settings=layout.get("settings") or {}
    cols=layout.get("cols")
    if not cols:
        raise Exception("Missing cols")
    num_cols=len(cols)
    rows=layout.get("rows")
    if not rows:
        raise Exception("Missing rows")
    cells=layout.get("cells") or []
    boxes=layout.get("boxes") or []
    for report_data in data_list:
        field=settings.get("field")
        if field:
            page_data_list=get_path_val(report_data,field)
            page_prefix=field+"."
        else:
            page_data_list=[report_data]
            page_prefix=None
        global current_page
        current_page=1
        for page_data in page_data_list:
            def _render_row(data,model,tmpl_row_no,out_row_no,prefix=None):
                print("_render_row",data,model,tmpl_row_no,out_row_no,prefix)
                sheet.set_column(0,num_cols-1,15)
                cells=layout.get("cells") or []
                for cell in cells:
                    name=cell["name"]
                    #print("cell name",name)
                    res=cell_name_to_coords(name)
                    row_no=res[0]
                    col_no=res[1]
                    if row_no!=tmpl_row_no:
                        continue
                    colspan=cell.get("colspan") or 1
                    rowspan=cell.get("rowspan") or 1
                    fmt=workbook.add_format()
                    if cell.get("bold"):
                        fmt.set_bold()
                    if cell.get("italic"):
                        fmt.set_italic()
                    if cell.get("font_name"):
                        fmt.set_font_name(cell["font_name"])
                    if cell.get("align"):
                        fmt.set_align(cell["align"])
                    if cell.get("border_top"):
                        fmt.set_top()
                    if cell.get("border_bottom"):
                        fmt.set_bottom()
                    if cell.get("border_left"):
                        fmt.set_left()
                    if cell.get("border_right"):
                        fmt.set_right()
                    if colspan>1 or rowspan>1:
                        sheet.merge_range(out_row_no,col_no,out_row_no+rowspan-1,col_no+colspan-1,"",fmt)
                    cell_type=cell.get("type") or "text"
                    if cell_type=="text":
                        val=cell.get("value") or ""
                        def _replace_expr(m):
                            global current_page
                            field=m.group(1)
                            if prefix:
                                field=field[len(prefix):]
                            v=get_path_val(data,field)
                            return str(v)
                        val=re.sub("\{(.*?)\}",_replace_expr,val)
                        sheet.write(out_row_no,col_no,val,fmt)
                    elif cell_type=="field":
                        field=cell.get("value")
                        if prefix:
                            field=field[len(prefix):]
                        val=get_path_val(data,field)
                        val=str(val)
                        sheet.write(out_row_no,col_no,val,fmt)
                    elif cell_type=="image":
                        val=cell.get("value")
                        path=utils.get_file_path(val)
                        if not path.endswith(".gif"): # XXX
                            sheet.insert_image(out_row_no,col_no,path)
            out_row_no=0
            for tmpl_row_no in range(len(rows)):
                row=rows[tmpl_row_no]
                if row.get("field"):
                    field=row["field"]
                    val=get_path_val(page_data,field) or ""
                    try:
                        f=get_field_by_path(model,field)
                        rmodel=f.relation if f else None
                    except: # XXX
                        rmodel=None
                    for rdata in val:
                        _render_row(rdata,rmodel,tmpl_row_no,out_row_no,field+".")
                        out_row_no+=1
                else:
                    _render_row(page_data,model,tmpl_row_no,out_row_no)
                    out_row_no+=1
    workbook.close()
    out=open("/tmp/report.xlsx","rb").read()
    return out
