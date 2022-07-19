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

from netforce.model import fields,get_model
from netforce import utils
from netforce import module
from netforce import database
from netforce import access
import requests
import pybars
from datetime import *
import time
from decimal import *
import pkg_resources
import os
import json
try:
    import rfc6266
except:
    print("Warning: failed to import rfc6266")
import shutil
from io import BytesIO
import zipfile
from lxml import etree
import re
from .report_nfjson import *
from .report_page_builder import *
from .report_page_builder_text import *
from .report_page_builder_html import *
from .report_page_builder_pos import *

def render_report_to_file(model,method,template,ids,context={}): # TODO: don't use http request, just call method
    print("render_report_to_file",model,method,template,ids)
    url="http://localhost:20999/report" # FIXME
    params={
        "model": model,
        "method": method,
        "template": template,
        "ids": json.dumps(ids),
        "context": json.dumps({
            "database": database.get_active_db(),
        }),
    }
    r=requests.get(url,params)
    v = r.headers['content-disposition']
    fname=rfc6266.parse_headers(v).filename_unsafe
    if not fname:
        raise Exception("Filename not found")
    path=utils.get_file_path(fname)
    f=open(path,"wb")
    f.write(r.content)
    f.close()
    return fname

def render_template_jsx(tmpl_body, data, orientation="portrait", header=None, footer=None):
    #print("report_render_jsx", data)
    tmpl_path="/tmp/template.jsx"
    f=open(tmpl_path,"wb")
    f.write(tmpl_body.encode("utf-8"))
    f.close()
    params = {
        "template": tmpl_path,
        "data": utils.json_dumps(data),
        "orientation": orientation,
    }
    if header:
        path="/tmp/header.html"
        f=open(path,"wb")
        f.write(header.encode("utf-8"))
        f.close()
        params["header"]=path
    if footer:
        path="/tmp/footer.html"
        f=open(path,"wb")
        f.write(footer.encode("utf-8"))
        f.close()
        params["footer"]=path
    url = "http://localhost:9991/"
    r = requests.post(url, data=params, timeout=15)
    if r.status_code != 200:
        raise Exception("Failed to render JSX report (%s)" % r.status_code)
    return r.content

def _replace(this,val,old,new):
    print("X"*80)
    print("_replace",val,old,new)
    return val.replace(old,new)

def _currency(this,val):
    return utils.format_money(val)

def _fmt_datetime(this,val,fmt="%Y-%m-%d %H:%M:%S"):
    if not val:
        return ""
    d=datetime.strptime(val,"%Y-%m-%d %H:%M:%S")
    return d.strftime(fmt)

def _esc(this,arg1=None,arg2=None,arg3=None):
    cmd="\x1b"
    if arg1 is not None:
        if isinstance(arg1,int):
            cmd+=chr(arg1)
        else:
            cmd+=arg1
    if arg2 is not None:
        if isinstance(arg2,int):
            cmd+=chr(arg2)
        else:
            cmd+=arg2
    if arg3 is not None:
        if isinstance(arg3,int):
            cmd+=chr(arg3)
        else:
            cmd+=arg3
    return cmd

def _pad(this,val,n,align="left"):
    val=str(val)[:n]
    l=utils.i18n_text_len(val)
    if align=="left":
        s=val+" "*(n-l)
    elif align=="right":
        s=" "*(n-l)+val
    elif align=="center":
        pl=int((n-l)/2)
        pr=n-l-pl
        s=" "*pl+val+" "*pr
    else:
        s=val
    return s

def _pad_int(this,val,n,align="right"):
    val=str(int(val))
    l=utils.i18n_text_len(val)
    if align=="left":
        s=val+" "*(n-l)
    elif align=="right":
        s=" "*(n-l)+val
    else:
        s=val
    return s

def _pad_currency(this,amt,n,align="right"):
    val=utils.format_money(amt)
    l=utils.i18n_text_len(val)
    if align=="left":
        s=val+" "*(n-l)
    elif align=="right":
        s=" "*(n-l)+val
    else:
        s=val
    return s

hbs_helpers={
    "replace": _replace,
    "currency": _currency,
    "fmt_datetime": _fmt_datetime,
    "esc": _esc,
    "pad": _pad,
    "pad_int": _pad_int,
    "pad_currency": _pad_currency,
}

def render_template_hbs(tmpl_body, data):
    compiler=pybars.Compiler()
    tmpl=compiler.compile(tmpl_body)
    out=tmpl(data,helpers=hbs_helpers)
    return out

def render_template_odt(tmpl_path, data, convert_pdf=False):
    if not tmpl_path:
        raise Exception("Missing template path")
    params = {
        "template_path": tmpl_path,
        "data": utils.json_dumps(data),
    }
    if convert_pdf:
        params["convert_pdf"]="1"
    url = "http://localhost:9990/"
    r = requests.post(url, data=params, timeout=15)
    if r.status_code != 200:
        raise Exception("Failed to render ODT report (%s)" % r.status_code)
    return r.content

def render_template_docx(tmpl_path, data, convert_pdf=False):
    if not tmpl_path:
        raise Exception("Missing template path")
    params = {
        "template_path": tmpl_path,
        "data": utils.json_dumps(data),
    }
    if convert_pdf:
        params["convert_pdf"]="1"
    url = "http://localhost:9990/"
    r = requests.post(url, data=params, timeout=15)
    if r.status_code != 200:
        raise Exception("Failed to render DOCX report (%s): %s" % (r.status_code,r.text))
    return r.content

def render_template_xlsx(tmpl_path, data, convert_pdf=False):
    if not tmpl_path:
        raise Exception("Missing template path")
    params = {
        "template_path": tmpl_path,
        "data": utils.json_dumps(data),
    }
    url = "http://localhost:9990/"
    r = requests.post(url, data=params, timeout=15)
    if r.status_code != 200:
        raise Exception("Failed to render XLSX report (%s)" % r.status_code)
    if convert_pdf:
        open("/tmp/report.xlsx","wb").write(r.content)
        dbname=database.get_active_db()
        os.system("jodconverter /tmp/report.xlsx /tmp/report_%s.pdf"%dbname)
        return open("/tmp/report_%s.pdf"%dbname,"rb").read()
    return r.content

def format_report_data(vals, model, date_only=False):
    print("format_report_data",model)
    #print("vals",vals)
    if not isinstance(vals,dict):
        return vals
    fmt_vals={}
    for n,v in vals.items():
        if n=="id":
            continue
        m=get_model(model)
        f=m._fields.get(n)
        if not f:
            raise Exception("Invalid field: %s (%s)"%(n,model))
        if v is not None:
            if isinstance(f,fields.Decimal) and not date_only:
                fmt_v=utils.format_money(v)
            elif isinstance(f,fields.Date):
                fmt_v=utils.format_date(v)
            elif isinstance(f,fields.DateTime):
                fmt_v=utils.format_datetime(v)
            elif isinstance(f,fields.Selection):
                fmt_v=""
                for k,s in f.selection:
                    if v==k:
                        fmt_v=s
                        break
            elif isinstance(f,fields.Many2One):
                fmt_v=format_report_data(v,f.relation)
            elif isinstance(f,fields.One2Many):
                fmt_v=[format_report_data(x,f.relation) for x in v]
            else:
                fmt_v=v
        else:
            fmt_v=""
        fmt_vals[n]=fmt_v
    return fmt_vals

def get_module_report_template(name):
    modules=module.get_loaded_modules()
    for m in modules:
        if not pkg_resources.resource_exists(m, "reports"):
            continue
        for fname in pkg_resources.resource_listdir(m, "reports"):
            base_name = os.path.splitext(fname)[0]
            if base_name!=name:
                continue
            data=pkg_resources.resource_string(m, "reports/" + fname)
            path="/tmp/"+fname # XXX
            f=open(path,"wb")
            f.write(data)
            f.close()
            return path
    return None

def conv_jasper_data(data, report_path):  # XXX: improve this
    print("conv_jasper_data")
    print("ORIG_DATA:")
    pprint(data)
    jrxml = open(report_path).read()
    tree = etree.fromstring(jrxml)
    ns = "http://jasperreports.sourceforge.net/jasperreports"
    el = tree.findall(".//ns:queryString", namespaces={"ns": ns})
    if not el:
        raise Exception("Query string not found")
    query = el[0].text.strip()
    print("QUERY", query)
    fields = []
    for el in tree.findall(".//ns:field", namespaces={"ns": ns}):
        name = el.attrib["name"]
        fields.append(name)
    print("FIELDS", fields)
    out_data = {}
    for f in fields:
        val = data_get_path(data, f)
        data_set_path(out_data, f, val)
    items = data_get_path(data, query) or []
    out_items = []
    for item in items:
        out_item = {}
        for f in fields:
            val = data_get_path(item, f)
            if val is None:
                val = data_get_path(data, f)
            data_set_path(out_item, f, val)
        out_items.append(out_item)
    data_set_path(out_data, query, out_items)
    print("CONV_DATA:")
    pprint(out_data)
    return out_data

def render_template_jasper(tmpl_path,data):
    print("!"*80)
    print("render_template_jasper",tmpl_path)
    if not tmpl_path:
        raise Exception("Missing template path")
    transform_jrxml(tmpl_path,data)
    #data2 = conv_jasper_data(data, report_path)
    params = {
        "report": tmpl_path,
        "format": "pdf",
        "data": utils.json_dumps(data),
    }
    url = "http://localhost:9993/"
    r = requests.post(url, data=params)
    report_dir = os.path.dirname(tmpl_path)
    print("report_dir",report_dir)
    #shutil.rmtree(report_dir)
    if r.status_code != 200:
        raise Exception("Failed to download report (%s)" % r.status_code)
    return r.content

def _extract_report_file(fname, report_dir):
    print("_extract_report_file", fname)
    return  # XXX

def transform_jrxml(report_path, params={}):
    report_dir="/tmp"
    tree = etree.parse(report_path)
    for el in tree.iterfind(".//ns:imageExpression", {"ns": "http://jasperreports.sourceforge.net/jasperreports"}):
        expr = el.text
        m = re.match("^\"(.*)\"$", expr)
        if m:
            img_fname = m.group(1)
            img_path = utils.get_file_path(img_fname)
            if os.path.exists(img_path):
                img_path2 = os.path.join(report_dir, img_fname)
                shutil.copyfile(img_path, img_path2)
            else:
                _extract_report_file(img_fname, report_dir)
            el.text = '"' + os.path.join(report_dir, img_fname) + '"'
        p = re.match("^\{(.*)\}$", expr)
        if p: #for detect {settings.logo}
            img_fname_obj = p.group(1)
            char_replace = ["{","}"]
            for c in char_replace:
                img_fname_obj.replace(c,"")
            img_fname_objs = img_fname_obj.split(".")
            obj = []
            if isinstance(params,list):
                obj = params[0] #FIXME
            else:
                obj = params
            for k in img_fname_objs:
                obj = obj[k]
            if obj:
                img_fname = obj
                img_path = utils.get_file_path(img_fname)
                if os.path.exists(img_path):
                    img_path2 = os.path.join(report_dir, img_fname)
                    shutil.copyfile(img_path, img_path2)
                else:
                    _extract_report_file(img_fname, report_dir)
                el.text = '"' + os.path.join(report_dir, img_fname) + '"'
            else:
                el.text = ''
    report_xml = etree.tostring(tree, pretty_print=True).decode()
    f = open(report_path, "w")
    f.write(report_xml)
    f.close()
