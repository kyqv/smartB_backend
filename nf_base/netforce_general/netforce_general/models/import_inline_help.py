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
import requests
import json

CLIENT_ID = "702491289059-n8l95ggji87ugprscg0c2neuvhohaf7a.apps.googleusercontent.com"
CLIENT_SECRET = "t0Sq4WNRV0vLK_9kg83uAh0H"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


def get_help_info(doc_id, token):
    url = "https://www.googleapis.com/drive/v2/files/%s?access_token=%s" % (doc_id, token)
    r = requests.get(url)
    res = json.loads(r.text)
    if res["labels"]["trashed"]:
        return None
    if res["title"].find("-") == -1:
        return None
    info = {
        "action": res["title"].split("-")[0].strip(),
        "title": res["title"].split("-")[1].strip(),
        "create_date": res["createdDate"][:-5].replace("T", " "),
        "modif_date": res["modifiedDate"][:-5].replace("T", " "),
    }
    return info


def get_help_content(doc_id, token):
    url = "https://docs.google.com/feeds/download/documents/export/Export?id=%s&format=html&access_token=%s" % (
        doc_id, token)
    r = requests.get(url)
    html = r.text
    html = html.replace("background-color:#ffffff;padding:72pt 72pt 72pt 72pt", "")
    html = html.replace("max-width:468pt", "")
    html = '<base target="_parent" />' + html
    return html


class Import(Model):
    _name = "import.inline.help"
    _transient = True
    _fields = {
        "folder_id": fields.Char("Folder ID"),
        "auth_code": fields.Char("Authorization Code"),
    }

    def request_auth(self, ids, context={}):
        obj = self.browse(ids)[0]
        scope = "https://www.googleapis.com/auth/drive.readonly"
        url = "https://accounts.google.com/o/oauth2/auth?scope=%s&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&client_id=%s&access_type=offline" % (
            scope, CLIENT_ID)
        return {
            "next": {
                "type": "url",
                "url": url,
            }
        }

    def do_import(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.folder_id:
            raise Exception("Missing folder ID")
        if not obj.auth_code:
            raise Exception("Missing authorization code")
        url = "https://accounts.google.com/o/oauth2/token"
        data = {
            "code": obj.auth_code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "authorization_code",
        }
        print("data", data)
        r = requests.post(url, data=data)
        res = json.loads(r.text)
        if res.get("error"):
            raise Exception(res["error_description"])
        token = res["access_token"]
        url = "https://www.googleapis.com/drive/v2/files/%s/children?access_token=%s" % (obj.folder_id, token)
        r = requests.get(url)
        res = json.loads(r.text)
        print("res", res)
        if res.get("error"):
            raise Exception(res["error"]["message"])
        for item in res["items"]:
            info = get_help_info(item["id"], token)
            if not info:
                continue
            res = get_model("inline.help").search([["action", "=", info["action"]]])
            if res:
                page_id = res[0]
                page = get_model("inline.help").browse(page_id)
                if page.modif_date < info["modif_date"]:
                    info["content"] = get_help_content(item["id"], token)
                    print("update existing help", page.action)
                    page.write(info)
            else:
                info["content"] = get_help_content(item["id"], token)
                print("create new help", info["action"])
                get_model("inline.help").create(info)
        return {
            "next": {
                "name": "inline_help",
            },
            "flash": "Inline help imported successfully",
        }

Import.register()
