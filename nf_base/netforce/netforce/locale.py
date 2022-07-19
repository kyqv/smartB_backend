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

from . import module
import os
import csv
import pkg_resources
from io import StringIO
import netforce

_active_locale = None
_translations = {}


def load_translations():
    loaded_modules = module.get_loaded_modules()
    for m in reversed(loaded_modules):
        try:
            if not pkg_resources.resource_exists(m, "i18n"):
                continue
            for csv_f in pkg_resources.resource_listdir(m, "i18n"):
                if not csv_f.endswith(".csv"):
                    continue
                locale, ext = csv_f.split(".")
                data = pkg_resources.resource_string(m, csv_f)
                f = StringIO(data)
                for i, row in enumerate(csv.reader(f)):
                    if not row or len(row) < 2:
                        continue
                    row = [c.decode("utf-8").strip() for c in row]
                    english, translation = row[:2]
                    _translations.setdefault(locale, {})[english] = translation
        except Exception as e:
            print("Failed to load translations of module %s: %s"%(m,e))

def get(code):
    return Locale.get(code)


class Locale(object):
    _cache = {}

    @classmethod
    def get(cls, code):
        if code in cls._cache:
            return cls._cache[code]
        loc = Locale(code)
        cls._cache[code] = loc
        return loc

    def __init__(self, code):
        self.code = code
        self.translations = _translations.get(code, {})

    def translate(self, message, context={}):
        if not message:
            return message
        if self.code == "en_US":
            return message
        val = netforce.model.get_model("translation").get_translation(message, self.code)
        if val:
            return val
        val = self.translations.get(message)
        if val is not None:
            return val
        return "?" + message


def set_active_locale(locale):
    global _active_locale
    _active_locale = get(locale)


def get_active_locale():
    if not _active_locale:
        return None
    return _active_locale.code


def translate(message):
    if not _active_locale:
        raise Exception("No active locale set")
    return _active_locale.translate(message)

_ = translate
