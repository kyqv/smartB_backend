#!/usr/bin/env python3
import curses
import os
import sys
from netforce_terminal.view import make_view,set_stdscr
import netforce
from netforce import config
from netforce import database
from netforce import access
import netforce_general
import netforce_contact
import netforce_product
import netforce_account
import netforce_stock
import netforce_stock_cost
import netforce_sale
import netforce_purchase
import netforce_mfg

config.load_config()
access.set_active_user(1)
database.set_active_db("thailandbest_test")
os.environ["ESCDELAY"]="25"
f = open(os.devnull, 'w')
sys.stdout = f
sys.stderr = f

def main(stdscr):
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
    set_stdscr(stdscr)
    opts={
        "win": stdscr,
    }
    v=make_view("menu",opts)
    v.render()
    v.focus()

curses.wrapper(main)
