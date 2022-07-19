from netforce.model import Model, fields, get_model
from netforce import config
from netforce import utils
from netforce import database
from netforce import tasks
import requests
import hashlib
import hmac
from datetime import *
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json


class SyncRecord(Model):
    _name = "sync.record"
    _fields = {
        "firebase_account_id": fields.Many2One("firebase.account","Account",required=True,on_delete="cascade"),
        "related_id": fields.Reference([],"Related To"),
        "path": fields.Char("Path"),
    }

SyncRecord.register()
