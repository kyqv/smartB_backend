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

from multiprocessing import Value, Queue, Manager
import os

_handlers = {}
_sig_count = None
_signals = None
_last_handled_signal = 0


def set_signal_handler(sig, handler):
    _handlers[sig] = handler


def init():
    global _signals, _sig_count
    manager = Manager()
    _signals = manager.dict()
    _sig_count = Value("i", 0)


def check_signals():
    try:
        global _last_handled_signal
        i = _last_handled_signal
        while i < _sig_count.value:
            i += 1
            sig = _signals.get(i)
            if sig:
                f = _handlers.get(sig)
                if f:
                    f()
        _last_handled_signal = i
    except Exception as e:
        print("!"*80)
        print("WARNING: failed to check signals: %s"%e)

def send_signal(sig):
    print("send_signal", sig)
    _sig_count.value += 1
    sig_id = _sig_count.value
    print("sig_id", sig_id)
    if sig_id % 100 == 0:  # XXX
        _signals.clear()
    _signals[sig_id] = sig
