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

from netforce.model import Model, fields, get_model
from netforce.database import get_active_db
from PIL import Image
import io
import os
import base64
import json
import time
import urllib
from netforce import utils
import random
#from netforce_report import get_report_jasper # deprecated
from pprint import pprint
from decimal import *
from netforce import access
import requests
import urllib.parse
from lxml import etree
from decimal import *
from . import th_utils
import math


class ShopeeApp(Model):
    _name = "shopee.app"
    _string = "Shopee App"
    _name_field="name"
    _fields = {
        "name": fields.Char("Name",required=True,search=True),
        "partner_id": fields.Char("Partner ID", required=True),
        "partner_key": fields.Char("Partner Key",required=True),
    }
    _order = "name"


ShopeeApp.register()
