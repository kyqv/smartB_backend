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
from netforce.database import get_connection, get_active_db
import os
import csv
from netforce import access
from netforce import static
from netforce.locale import get_active_locale
from netforce import ipc
from netforce import utils
try:
    from google.cloud import translate
except:
    print("Failed to import google translate")

_cache = {}


def _clear_cache():
    pid = os.getpid()
    print("translation _clear_cache pid=%s" % pid)
    _cache.clear()

ipc.set_signal_handler("clear_translation_cache", _clear_cache)


class Translation(Model):
    _name = "translation"
    _string = "Translation"
    #_key = ["lang_id", "original"]
    _fields = {
        "lang_id": fields.Many2One("language", "Language", required=True, search=True),
        "original": fields.Char("Original String", required=True, search=True),
        "translation": fields.Char("Translation", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }
    _order = "lang_id,original"

    def change_lang(self, context={}):
        locale = context["set_locale"]
        return {
            "cookies": {
                "locale": locale,
            },
            "next": {
                "type": "reload",
            }
        }

    def create(self, *a, **kw):
        new_id = super().create(*a, **kw)
        static.clear_translations()
        ipc.send_signal("clear_translation_cache")
        ipc.send_signal("clear_ui_params_cache")
        return new_id

    def write(self, *a, **kw):
        res = super().write(*a, **kw)
        static.clear_translations()
        ipc.send_signal("clear_translation_cache")
        ipc.send_signal("clear_ui_params_cache")

    def delete(self, *a, **kw):
        res = super().delete(*a, **kw)
        static.clear_translations()
        ipc.send_signal("clear_translation_cache")
        ipc.send_signal("clear_ui_params_cache")

    def get_translation(self, original, lang):
        cache = self._get_cache()
        return cache.get((original, lang))

    def translate(self, original):
        lang = get_active_locale()
        cache = self._get_cache()
        return cache.get((original, lang))

    def _get_cache(self):
        global _cache
        dbname = get_active_db()
        cache = _cache.get(dbname)
        if cache is None:
            cache = self._load_cache()
        return cache

    def _load_cache(self):
        global _cache
        dbname = get_active_db()
        print("Loading translations (%s)" % dbname)
        db = get_connection()
        res = db.query(
            "SELECT t.original,l.code AS lang,t.translation FROM translation t, language l WHERE t.lang_id=l.id")
        cache = {}
        for r in res:
            cache[(r.original, r.lang)] = r.translation
        _cache[dbname] = cache
        return cache

    def translations_to_json(self,context={}):
        access.set_active_user(1)
        translations={}
        translations_regex={}
        for obj in self.search_browse([]):
            if not obj.original:
                continue
            if obj.original.find(".*")!=-1:
                translations_regex.setdefault(obj.lang_id.code,[]).append([obj.original,obj.translation])
            else:
                translations.setdefault(obj.lang_id.code,{})[obj.original]=obj.translation
        return {
            "translations": translations,
            "translations_regex": translations_regex,
        }

    def update_translation(self, lang, original, val, context={}):
        res=self.search([["lang_id.code","=",lang],["original","=",original]])
        if res:
            trans_id=res[0]
            self.write([trans_id],{"translation": val})
        else:
            res=get_model("language").search([["code","=",lang]])
            if not res:
                raise Exception("Language not found: %s"%lang)
            lang_id=res[0]
            vals={
                "lang_id": lang_id,
                "original": original,
                "translation": val,
            }
            trans_id=self.create(vals)
        return trans_id

    def add_missing(self,miss_trans,context={}):
        n=0
        for lang,trans in miss_trans.items():
            for orig in trans:
                res=self.search([["lang_id.code","=",lang],["original","=",orig]])
                if res:
                    continue
                res=get_model("language").search([["code","=",lang]])
                if not res:
                    raise Exception("Language not found: %s"%lang)
                lang_id=res[0]
                vals={
                    "lang_id": lang_id,
                    "original": orig,
                }
                trans_id=self.create(vals)
                n+=1
        return {
            "flash": "%d translations added"%n,
        }

    def translate_google(self,ids,context={}):
        print("translate_google",ids)
        lang=None
        inputs=[]
        for obj in self.browse(ids):
            if obj.translation:
                continue
            if not obj.original:
                continue
            if lang is None:
                lang=obj.lang_id.code
            else:
                if obj.lang_id.code!=lang:
                    raise Exception("Different target languages selected")
            inputs.append(obj.original)
        if not inputs:
            raise Exception("Nothing to translated")
        print("inputs",inputs)
        target=lang[:2]
        print("target",target)
        print("sending request...")
        #settings=get_model("settings").browse(1)
        #if not settings.google_api_key:
        #    raise Exception("Missing Google API key")
        #client=translate.Client(settings.google_api_key)
        client=translate.Client()
        n=0
        for query in utils.chunks(inputs,100):
            translations=client.translate(query,target)
            print("received response")
            for trans in translations:
                #print(trans)
                res=self.search([["lang_id.code","=",lang],["original","=",trans["input"]]])
                if not res:
                    raise Exception("Original not found: %s"%trans["input"])
                trans_id=res[0]
                self.write([trans_id],{"translation": trans["translatedText"]})
                n+=1
        return {
            "flash": "%d items translated"%n,
        }

Translation.register()
