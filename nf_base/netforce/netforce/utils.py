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

import urllib.parse
import pkg_resources
import tempfile
from netforce import database
import os
import random
import string
import json
import hmac
import hashlib
import base64
from datetime import *
from dateutil.relativedelta import relativedelta
import time
import sys
from struct import Struct
from operator import xor
from itertools import starmap
import binascii
import signal
import platform
import re
import math
import decimal
try:
    import dns.resolver
    HAS_DNS = True
except:
    HAS_DNS = False
from . import config
import xmlrpc.client
from pprint import pprint
import requests


def get_data_path(data, path, default=None, parent=False):
    if not path:
        return data
    val = data
    fields = path.split(".")
    if parent:
        fields = fields[:-1]
    for field in fields:
        if not field.isdigit():
            if not isinstance(val, dict):
                return default
            val = val.get(field, default)
        else:
            ind = int(field)
            if not isinstance(val, list) or ind >= len(val):
                return default
            val = val[ind]
    return val


def set_data_path(data, path, val):
    fields = path.split(".")
    if data is None:
        if not fields[0].isdigit() and fields[0] != "[]":
            data = {}
        else:
            data = []
    obj = data
    for i, field in enumerate(fields):
        if i < len(fields) - 1:
            next_field = fields[i + 1]
            if not next_field.isdigit() and next_field != "[]":
                v = {}
            else:
                v = []
            last = False
        else:
            v = val
            last = True
        if not field.isdigit() and field != "[]":
            if last:
                obj[field] = v
            else:
                obj = obj.setdefault(field, v)
        else:
            if field == "[]":
                obj.append(v)
            else:
                ind = int(field)
                while len(obj) <= ind:
                    obj.append(None)
                if last:
                    obj[ind] = v
                else:
                    if obj[ind] is None:
                        obj[ind] = v
                    obj = obj[ind]
    return data


def is_sub_url(url, base_url):
    o1 = urllib.parse.urlparse(base_url)
    o2 = urllib.parse.urlparse(url)
    if o2.path != o1.path:
        return False
    q1 = urllib.parse.parse_qs(o1.query)
    q2 = urllib.parse.parse_qs(o2.query)
    for k, v1 in q1.items():
        v2 = q2.get(k)
        if v2 != v1:
            return False
    return True

def get_ip_country(ip): # TODO: remove this
    return None

def rmdup(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if x not in seen and not seen_add(x)]


def get_file_path(fname):
    if not fname:
        return None
    dbname = database.get_active_db()
    if not dbname:
        return None
    static_dir=config.get("static_dir") or "static"
    if fname[0]=="/":
        path = os.path.join(static_dir, fname[1:])
    else:
        path = os.path.join(static_dir, "db", dbname, "files", fname)
    return path

def get_static_path():
    dbname = database.get_active_db()
    if not dbname:
        return None
    static_dir=config.get("static_dir") or "static"
    path = os.path.join(static_dir, "db", dbname)
    return path

def gen_passwd(n=8, numeric=False):
    if numeric:
        chars = string.digits
    else:
        chars = string.ascii_letters + string.digits
    return "".join([random.choice(chars) for i in range(n)])


def eval_json(expr, ctx):
    def _eval_var(name):
        if name in ("true", "false", "null"):
            return name
        comps = name.split(".")
        v = ctx
        for n in comps:
            v = v.get(n)
            if not isinstance(v, dict):
                return v
        return v
    chunks = []
    state = "other"
    start = 0
    for i, c in enumerate(expr):
        if state == "other":
            if c == "\"":
                state = "string"
            elif c.isalpha() or c == "_":
                chunks.append(expr[start:i])
                state = "var"
                start = i
        elif state == "string":
            if c == "\"":
                state = "other"
            elif c == "\\":
                state = "escape"
        elif state == "escape":
            state = "string"
        elif state == "var":
            if not c.isalnum() and c != "_" and c != ".":
                n = expr[start:i].strip()
                v = _eval_var(n)
                if v is None:
                    s="null"
                else:
                    s=str(v)
                chunks.append(s)
                state = "other"
                start = i
    chunks.append(expr[start:])
    data = "".join(chunks)
    return json.loads(data)

_UTF8_TYPES = (bytes, type(None))


def utf8(value):
    if isinstance(value, _UTF8_TYPES):
        return value
    assert isinstance(value, str)
    return value.encode("utf-8")

_TO_UNICODE_TYPES = (str, type(None))


def to_unicode(value):
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    assert isinstance(value, bytes)
    return value.decode("utf-8")


def _create_signature(secret, *parts):
    hash = hmac.new(utf8(secret), digestmod=hashlib.sha1)
    for part in parts:
        hash.update(utf8(part))
    return utf8(hash.hexdigest())


def _time_independent_equals(a, b):
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def _decode_signed_value(secret, name, value, max_age_days=31):
    if not value:
        return None
    parts = utf8(value).split(b"|")
    if len(parts) != 3:
        return None
    signature = _create_signature(secret, name, parts[0], parts[1])
    if not _time_independent_equals(parts[2], signature):
        print("WARNING: Invalid cookie signature %r" % value)
        return None
    timestamp = int(parts[1])
    """ XXX: never expire
    if timestamp < time.time() - max_age_days * 86400:
        print("WARNING: Expired cookie %r" % value)
        return None
    if timestamp > time.time() + 31 * 86400:
        # _cookie_signature does not hash a delimiter between the
        # parts of the cookie, so an attacker could transfer trailing
        # digits from the payload to the timestamp without altering the
        # signature.  For backwards compatibility, sanity-check timestamp
        # here instead of modifying _cookie_signature.
        print("WARNING: Cookie timestamp in future; possible tampering %r" % value)
        return None
    """
    if parts[1].startswith(b"0"):
        print("WARNING: Tampered cookie %r" % value)
    try:
        return base64.b64decode(parts[0])
    except Exception:
        return None


def _create_signed_value(secret, name, value):
    timestamp = utf8(str(int(time.time())))
    value = base64.b64encode(utf8(value))
    signature = _create_signature(secret, name, value, timestamp)
    value = b"|".join([value, timestamp, signature])
    return value

_token_secret=None

def get_token_secret():
    global _token_secret
    if _token_secret is not None:
        return _token_secret
    path=".token_secret"
    if os.path.exists(path):
        _token_secret=open(path).read()
    else:
        _token_secret=gen_passwd(20)
        open(path,"w").write(_token_secret)
    return _token_secret

def new_token(dbname, user_id):
    user = "%s %s" % (dbname, user_id)
    secret=get_token_secret()
    token = to_unicode(_create_signed_value(secret, "user", user))
    return token


def check_token(dbname, user_id, token):
    # print("check_token",dbname,user_id,token)
    user = "%s %s" % (dbname, user_id)
    secret=get_token_secret()
    val = to_unicode(_decode_signed_value(secret, "user", token))
    return val == user


def url_escape(value):
    return urllib.parse.quote_plus(utf8(value))


def url_unescape(value, encoding='utf-8'):  # XXX: check tornado
    return urllib.parse.unquote_plus(value, encoding=encoding)


def format_color(msg, color=None, bright=False):
    color_codes = {
        "black": 0,
        "red": 1,
        "green": 2,
        "yellow": 3,
        "blue": 4,
        "magenta": 5,
        "cyan": 6,
        "white": 7,
    }
    code = color_codes.get(color, 7)
    head = "\x1b[3%dm" % code
    if bright:
        head += "\x1b[1m"
    foot = "\x1b[39;49m"
    if bright:
        foot += "\x1b[22m"
    return head + msg + foot


def print_color(msg, color=None, bright=False):
    if sys.stdout.isatty():
        msg = format_color(msg, color=color, bright=bright)
    print(msg)


def compare_version(v1, v2):
    v1_ = [int(d) for d in v1.split(".")]
    v2_ = [int(d) for d in v2.split(".")]
    if v1_ < v2_:
        return -1
    if v1_ > v2_:
        return 1
    return 0


def get_db_version():
    db = database.get_connection()
    res = db.get("SELECT * FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname='settings'")
    if not res:
        return None
    res = db.get("SELECT * FROM settings WHERE id=1")
    if not res:
        return None
    return res.version


def set_db_version(version):
    db = database.get_connection()
    res = db.get("SELECT * FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname='settings'")
    if not res:
        raise Exception("Missing settings table")
    res = db.get("SELECT * FROM settings WHERE id=1")
    if not res:
        raise Exception("Missing settings record")
    db.execute("UPDATE settings SET version=%s WHERE id=1", version)


def is_empty_db():
    db = database.get_connection()
    res = db.get("SELECT * FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname='settings'")
    if not res:
        return True
    res = db.get("SELECT * FROM settings WHERE id=1")
    if not res:
        return True
    return False

def init_db():
    db = database.get_connection()
    db.execute("INSERT INTO profile (id,name,default_model_perms) VALUES (1,'System Admin','full')")
    db.execute("INSERT INTO settings (id,anon_profile_id) VALUES (1,1)")
    enc_pass=encrypt_password('1234')
    db.execute("INSERT INTO base_user (id,login,password,name,profile_id,active) VALUES (1,'admin',%s,'Admin',1,true)",enc_pass)
    db.execute("INSERT INTO company (id,name) VALUES (1,'Test Company')")

_pack_int = Struct('>I').pack


def pbkdf2_hex(data, salt, iterations=1000, keylen=24, hashfunc=None):
    return binascii.hexlify(pbkdf2_bin(data, salt, iterations, keylen, hashfunc)).decode()


def pbkdf2_bin(data, salt, iterations=1000, keylen=24, hashfunc=None):
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(salt, str):
        salt = salt.encode("utf-8")
    hashfunc = hashfunc or hashlib.sha1
    mac = hmac.new(data, None, hashfunc)

    def _pseudorandom(x, mac=mac):
        h = mac.copy()
        h.update(x)
        return h.digest()
    buf = []
    for block in range(1, -(-keylen // mac.digest_size) + 1):
        rv = u = _pseudorandom(salt + _pack_int(block))
        for i in range(iterations - 1):
            u = _pseudorandom(u)
            rv = starmap(xor, zip(rv, u))
        buf.extend(rv)
    return bytes(buf[:keylen])


def encrypt_password(password):
    algo = "pbkdf2"
    salt = binascii.hexlify(os.urandom(8)).decode()
    hsh = pbkdf2_hex(password, salt)
    return "%s$%s$%s" % (algo, salt, hsh)


def check_password(password, enc_password):
    master_pwd = config.get("master_password")
    if master_pwd and password == master_pwd:
        return True
    if not password or not enc_password:
        return False
    algo, salt, hsh = enc_password.split("$")
    if algo != "pbkdf2":
        raise Exception("Unknown password encryption algorithm")
    hsh2 = pbkdf2_hex(password, salt)
    return hsh2 == hsh


class timeout:  # XXX: doesn't seem to work yet... (some jsonrpc requests take more than 5min)

    def __init__(self, seconds=None):
        self.seconds = seconds

    def handle_timeout(self, signum, frame):
        raise Exception("Timeout!")

    def __enter__(self):
        if self.seconds and platform.system() != "Windows":
            signal.signal(signal.SIGALRM, self.handle_timeout)
            signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        if self.seconds and platform.system() != "Windows":
            signal.alarm(0)


def get_email_domain(email_addr):
    s = email_addr.strip()
    domain = s[s.find('@') + 1:].lower()
    return domain


def get_mx_records(domain):
    if not HAS_DNS:
        raise Exception("dnspython library not installed")
    try:
        res = dns.resolver.query(domain, "MX")
    except:
        return None
    records = sorted([(int(r.preference), str(r.exchange)) for r in res])
    return records

WSP = r'[ \t]'                                       # see 2.2.2. Structured Header Field Bodies
CRLF = r'(?:\r\n)'                                   # see 2.2.3. Long Header Fields
NO_WS_CTL = r'\x01-\x08\x0b\x0c\x0f-\x1f\x7f'        # see 3.2.1. Primitive Tokens
QUOTED_PAIR = r'(?:\\.)'                             # see 3.2.2. Quoted characters
FWS = r'(?:(?:' + WSP + r'*' + CRLF + r')?' + \
      WSP + r'+)'                                    # see 3.2.3. Folding white space and comments
CTEXT = r'[' + NO_WS_CTL + \
        r'\x21-\x27\x2a-\x5b\x5d-\x7e]'              # see 3.2.3
CCONTENT = r'(?:' + CTEXT + r'|' + \
           QUOTED_PAIR + r')'                        # see 3.2.3 (NB: The RFC includes COMMENT here
# as well, but that would be circular.)
COMMENT = r'\((?:' + FWS + r'?' + CCONTENT + \
          r')*' + FWS + r'?\)'                       # see 3.2.3
CFWS = r'(?:' + FWS + r'?' + COMMENT + ')*(?:' + \
       FWS + '?' + COMMENT + '|' + FWS + ')'         # see 3.2.3
ATEXT = r'[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]'           # see 3.2.4. Atom
ATOM = CFWS + r'?' + ATEXT + r'+' + CFWS + r'?'      # see 3.2.4
DOT_ATOM_TEXT = ATEXT + r'+(?:\.' + ATEXT + r'+)*'   # see 3.2.4
DOT_ATOM = CFWS + r'?' + DOT_ATOM_TEXT + CFWS + r'?'  # see 3.2.4
QTEXT = r'[' + NO_WS_CTL + \
        r'\x21\x23-\x5b\x5d-\x7e]'                   # see 3.2.5. Quoted strings
QCONTENT = r'(?:' + QTEXT + r'|' + \
           QUOTED_PAIR + r')'                        # see 3.2.5
QUOTED_STRING = CFWS + r'?' + r'"(?:' + FWS + \
    r'?' + QCONTENT + r')*' + FWS + \
    r'?' + r'"' + CFWS + r'?'
LOCAL_PART = r'(?:' + DOT_ATOM + r'|' + \
             QUOTED_STRING + r')'                    # see 3.4.1. Addr-spec specification
DTEXT = r'[' + NO_WS_CTL + r'\x21-\x5a\x5e-\x7e]'    # see 3.4.1
DCONTENT = r'(?:' + DTEXT + r'|' + \
           QUOTED_PAIR + r')'                        # see 3.4.1
DOMAIN_LITERAL = CFWS + r'?' + r'\[' + \
    r'(?:' + FWS + r'?' + DCONTENT + \
    r')*' + FWS + r'?\]' + CFWS + r'?'  # see 3.4.1
DOMAIN = r'(?:' + DOT_ATOM + r'|' + \
         DOMAIN_LITERAL + r')'                       # see 3.4.1
ADDR_SPEC = LOCAL_PART + r'@' + DOMAIN               # see 3.4.1

# A valid address will match exactly the 3.4.1 addr-spec.
VALID_ADDRESS_REGEXP = '^' + ADDR_SPEC + '$'


def check_email_syntax(email_addr):
    m = re.match(VALID_ADDRESS_REGEXP, email_addr)
    if not m:
        return False
    return True


def round_amount(amt, rounding, method="nearest"):
    if not rounding:
        return amt
    if method == "nearest":
        i = round((amt + 0.000001) / rounding)
    elif method == "lower":
        i = math.floor(amt / rounding)
    elif method == "upper":
        i = math.ceil(amt / rounding)
    else:
        raise Exception("Invalid rounding method")
    return i * rounding

def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    try:
        obj[0]
        return [x for x in obj]
    except:
        return {x:obj[x] for x in obj}
    #raise TypeError

def json_dumps(val):
    s=json.dumps(val, default=decimal_default)
    s=s.replace("NaN","null") # XXX
    return s

def json_loads(s):
    return json.loads(s, parse_float=decimal.Decimal)

class XmlRpcCookieTransport(xmlrpc.client.Transport):
    def __init__(self):
        super().__init__()
        self._cookies = []

    def send_headers(self, connection, headers):
        if self._cookies:
            connection.putheader("Cookie", "; ".join(self._cookies))
        print("cookies",self._cookies)
        super().send_headers(connection, headers)

    def parse_response(self, response):
        for header in response.msg.get_all("Set-Cookie") or []:
            cookie = header.split(";", 1)[0]
            self._cookies.append(cookie)
        return super().parse_response(response)

def create_thumbnails(fname):
    print("create_thumbnails",fname)
    dbname = database.get_active_db()
    if not dbname:
        return None
    static_dir=config.get("static_dir") or "static"
    fdir = os.path.join(static_dir, "db", dbname, "files")
    path=os.path.join(fdir,fname)
    basename,ext=os.path.splitext(fname)
    fname,rand = basename.split(",")
    for s in [512,256,128,64,32]:
        fname_thumb =fname+ "-resize-%s"%s+"," +rand + ext
        path_thumb = os.path.join(fdir, fname_thumb)
        os.system(r"convert -resize %sx%s\> '%s' '%s'" % (s,s,path, path_thumb))

def check_domain_syntax(domain):
    if not re.match("^[a-z0-9]+(-[a-z0-9]+)*$",domain):
        return False
    return True

def format_money(val,remove_zero=False,num_digits=2):
    if val is None:
        return ""
    s=("{:0,."+str(num_digits)+"f}").format(val)
    if remove_zero: # XXX
        s=s.replace(".00","")
    return s

def format_hours(val):
    if val is None:
        return ""
    h=math.floor(val)
    m=math.floor((val-h)*60)
    res="%s h"%h
    if m:
        res+=" %s m"%m
    return res

def parse_date(val,fmt=None,use_be_date=False):
    if val is None:
        return ""
    if fmt:
        fmt2=fmt.replace("YYYY","%Y").replace("YY","%y").replace("MM","%m").replace("DD","%d") # XXX
    else:
        fmt2="%Y-%m-%d"
    try:
        d=datetime.strptime(val,fmt2)
        if use_be_date:
            d=d-relativedelta(years=543)
    except:
        raise Exception("Date is in wrong format: %s (format should be %s)"%(val,fmt or "YYYY-MM-DD"))
    return d.strftime("%Y-%m-%d")

def parse_datetime(val,fmt=None,use_be_date=False):
    if val is None:
        return ""
    if fmt:
        fmt2=fmt.replace("YYYY","%Y").replace("YY","%y").replace("MM","%m").replace("DD","%d").replace("HH","%H").replace("mm","%M").replace("ss","%S") # XXX
    else:
        fmt2="%Y-%m-%d"
    try:
        d=datetime.strptime(val,fmt2)
        if use_be_date:
            d=d-relativedelta(years=543)
    except:
        raise Exception("Date is in wrong format: %s (format should be %s, %s)"%(val,fmt or "YYYY-MM-DD",fmt2))
    return d.strftime("%Y-%m-%d %H:%M:%S")

def format_date(val,fmt=None):
    print("format_date",val,fmt)
    if val is None:
        return ""
    d=datetime.strptime(val,"%Y-%m-%d")
    if not fmt:
        fmt="%d %B %Y"
    elif fmt=="DD MMM YYYY":
        fmt="%d %b %Y"
    else:
        fmt="%Y-%m-%d"
    s=d.strftime(fmt)
    return s

def format_datetime(val):
    if val is None:
        return ""
    d=datetime.strptime(val,"%Y-%m-%d %H:%M:%S")
    s=d.strftime("%d %B %Y %H:%M:%S")
    return s

def download_remote_image(url):
    print("download_remote_image",url)
    r=requests.get(url,stream=True)
    if r.status_code!=200:
        raise Exception("Invalid status code: %s"%r.status_code)
    data=r.raw.read()
    if not data:
        raise Exception("Empty file")
    p=urllib.parse.urlparse(url)
    fname=os.path.basename(p.path)
    path=get_file_path(fname)
    f=open(path,"wb")
    f.write(data)
    f.close()
    return fname

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

def i18n_filter_line(line):
    line1=[]
    line2=[]
    has_line2=False
    for c in line:
        b=ord(c)
        if b==0xe31 or (b>=0xe34 and b<=0xe3a) or (b>=0xe47 and b<=0xe4e):
            line2[-1]=c
            has_line2=True
        else:
            line1.append(c)
            line2.append(" ")
    filt_lines=["".join(line1)]
    if has_line2:
        filt_lines.append("".join(line2))
    return filt_lines

def i18n_text_len(line):
    return len(i18n_filter_line(line)[0])

#################

ONES = [
    None, 'one', 'two', 'three', 'four',
    'five', 'six', 'seven', 'eight', 'nine'
]

TEENS = [
    'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
    'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'
]

TENS = [
    None, None, 'twenty', 'thirty', 'forty',
    'fifty', 'sixty', 'seventy', 'eighty', 'ninety'
]

POWERS_OF_1000 = [
    None, 'thousand', 'million', 'billion', 'trillion',
    'quadrillion', 'quintillion', 'sextillion', 'septillion', 'octillion'
]


def number_to_chunks(number):
    """
    Split an integer into little-endian base-1000 chunks.

    >>> list(number_to_chunks(1234))
    [234, 1]
    >>> list(number_to_chunks(31415000))
    [0, 415, 31]
    >>> list(number_to_chunks(0))
    []
    """
    while number:
        number, n = divmod(number, 1000)
        yield n

def chunk_to_words(chunk, scale):
    """
    Generate English words given a chunk (an integer less than 1000) and its
    scale (power of 1000).

    >>> list(chunk_to_words(31, 1))
    ['thirty', 'one', 'thousand']
    >>> list(chunk_to_words(50, 2))
    ['fifty', 'million']
    >>> list(chunk_to_words(0, 0))
    []
    >>> list(chunk_to_words(12, 3))
    ['twelve', 'billion']
    """
    assert 0 <= chunk < 1000
    hundreds, tens, ones = chunk // 100, chunk // 10 % 10, chunk % 10

    if hundreds:
        yield ONES[hundreds]
        yield 'hundred'

    if tens == 1:
        yield TEENS[ones]
    else:
        if tens:
            yield TENS[tens]
        if ones:
            yield ONES[ones]

    if chunk and scale:
        yield POWERS_OF_1000[scale]

def num2words(number):
    """
    Convert a nonnegative integer less than 10**30 to an English phrase.

    >>> number_to_words(103)
    'one hundred three'
    >>> number_to_words(0)
    'zero'
    >>> number_to_words(1_000_001)
    'one million one'
    >>> number_to_words(31_415_926_535)
    'thirty one billion four hundred fifteen million nine hundred twenty six thousand five hundred thirty five'
    """
    chunks = [
        ' '.join(chunk_to_words(chunk, i))
        for i, chunk in enumerate(number_to_chunks(number))
    ]
    return ' '.join(c for c in chunks[::-1] if c) or 'zero'

def num2words_cents(amt,currency=None):
    words=num2words(int(amt))
    cents=round(amt*100)%100
    if cents:
        if currency:
            words+=" %s"%currency
        word_cents=num2words(cents)
        cents_name="cents" # XXX
        words+=", %s %s"%(word_cents,cents_name)
    return words

from .exception import *

def get_field_path(model, path):
    print("get_field_path",model,path)
    from netforce.model import get_model,fields
    field_model=model
    comps = path.split(".")
    for field in comps[:-1]:
        if field.isdigit():
            continue
        m=get_model(field_model)
        f=m._fields.get(field)
        if not f:
            raise Exception("Invalid field: %s %s"%(field_model,field))
        if not isinstance(f,(fields.Many2One,fields.One2Many,fields.Many2Many)):
            raise Exception("Invalid path: %s %s"%(model,path))
        field_model=f.relation
    field_name=comps[-1]
    print("=>",field_model,field_name)
    return field_model,field_name

def clean_filename(fname):
    allowed_chars=[" ","-","_","."]
    fname2="".join([c for c in fname if c.isalnum() or c in allowed_chars]).strip()
    return fname2

def get_random_filename(fname):
    rand = base64.urlsafe_b64encode(os.urandom(8)).decode()
    res = os.path.splitext(fname)
    basename, ext = res
    fname2 = basename + "," + rand + ext
    return fname2

def remove_filename_random(fname):
    basename,ext = os.path.splitext(fname)
    basename2,_,rand=basename.rpartition(",")
    fname2 = basename2+ext
    return fname2

def format_file_size(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)

def clean_cond(cond,depth=0):
    #print("  "*depth+"clean_cond",cond)
    if isinstance(cond,list):
        if not cond:
            return True
        if isinstance(cond[0],str) and cond[0] not in ("and","or","not"):
            return cond
        cond2=[]
        for c in cond:
            if isinstance(c,list):
                c2=clean_cond(c,depth+1)
                cond2.append(c2)
            elif isinstance(c,tuple):
                cond2.append(list(c))
            elif isinstance(c,dict): # XXX
                pass
            else:
                cond2.append(c)
        if len(cond2)==1 and cond2[0] not in ("and","or","not"):
            cond2=cond2[0]
        elif len(cond2)==2 and cond2[0] in ("and","or"):
            cond2=cond2[1]
        elif len(cond2)==1 and cond2[0]=="and":
            cond2=True
        elif len(cond2)==1 and cond2[0]=="or":
            cond2=False
        elif len(cond2)==0:
            cond2=True
    else:
        cond2=cond
    #print("  "*depth+"=>",cond2)
    return cond2

def cond_distrib_or(cond):
    #print("distrib_or",cond)
    if not isinstance(cond,list):
        return cond
    if not cond:
        return []
    if isinstance(cond[0],str):
        return cond
    other_clauses=[]
    or_clause=None
    for clause in cond:
        if isinstance(clause,list) and clause[0]=="or" and or_clause is None:
            or_clause=clause
        else:
            other_clauses.append(clause)
    if not or_clause:
        return cond
    cond2=["or"]
    for clause in or_clause[1:]:
        cond2.append([clause]+other_clauses)
    #print("=>",cond2)
    return cond2

def render_page_pdf(page_id,active_id):
    from netforce.model import get_model
    from netforce_report import render_page_pdf_web
    page=get_model("page.layout").browse(page_id)
    try:
        layout=json.loads(page.layout)
    except:
        raise Exception("Invalid layout")
    res=render_page_pdf_web(page.path,active_id,None,layout)
    data=res["data"]
    filename=res["filename"]
    return {
        "data": data,
        "filename": filename,
    }

def render_page_html(page_id=None,page_name=None,active_id=None,params=None):
    print("render_page_html",page_id,active_id,params)
    from netforce.model import get_model
    from netforce_report import render_page_html_web
    if page_name:
        res=get_model("page.layout").search([["path","=",page_name]])
        if not res:
            raise Exception("Page not found: %s"%page_name)
        page_id=res[0]
    page=get_model("page.layout").browse(page_id)
    try:
        layout=json.loads(page.layout)
    except:
        raise Exception("Invalid layout")
    res=render_page_html_web(page.path,active_id,None,layout,params)
    data=res["data"]
    #print("=> html data")
    #print(data)
    filename=res.get("filename")
    return {
        "data": data,
        "filename": filename,
    }
