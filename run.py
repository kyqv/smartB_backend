#!/usr/bin/env python
import netforce
import os

modules=[
    "netforce_jsonrpc",
    #"netforce_xmlrpc",
    "netforce_report",
    "netforce_messaging",
    "netforce_general",
    "netforce_contact",
    "netforce_support",
    "netforce_product",
    "netforce_account",
    "netforce_account_report",
    "netforce_service",
    "netforce_stock",
    "netforce_stock_cost",
    "netforce_sale",
    "netforce_purchase",
    "netforce_mfg",
    "netforce_marketing",
    "netforce_hr",
    "netforce_document",
    "netforce_cms",
    "netforce_ecom2",
    #"netforce_addon",
    #"netforce_mobile",
    #"netforce_pos",
    #"netforce_delivery",
    #"netforce_job_control",
    #"netforce_kff",
    #"netforce_shopee",
]
netforce.load_modules(modules)
netforce.run_server()
