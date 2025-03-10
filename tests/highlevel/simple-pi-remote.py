#use with jobslave.py

import os
os.environ["SEAMLESS_COMMUNION_ID"] = "simple-pi-remote"
os.environ["SEAMLESS_COMMUNION_PORT"] = "8602"

import seamless
seamless.set_ncores(0)
from seamless import communion_server

communion_server.configure_master(
    buffer=True,
    transformation_job=True,
    transformation_status=True,
)

communion_server.start()

import math
from seamless.highlevel import Context, Cell
import json
ctx = Context()
ctx.pi = math.pi
ctx.doubleit = lambda a: 2 * a
ctx.doubleit.a = ctx.pi
ctx.twopi = ctx.doubleit
ctx.translate()

ctx.compute()
print(ctx.pi.value)
print(ctx.twopi.value)

ctx.doubleit.code = lambda a: 42
ctx.compute()
print(ctx.pi.value)
print(ctx.twopi.value)

ctx.translate(force=True)
ctx.compute()
print(ctx.pi.value)
print(ctx.twopi.value)
print()

ctx.doubleit.code = lambda a: 2 * a
ctx.compute()
print(ctx.pi.value)
print(ctx.twopi.value)
