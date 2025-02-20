# Start this one before simple-communion-master

import sys, os, asyncio
os.environ["SEAMLESS_COMMUNION_ID"] = "simple-communion-slave"
os.environ["SEAMLESS_COMMUNION_OUTGOING_IP"] = "0.0.0.0"
os.environ["SEAMLESS_COMMUNION_OUTGOING_PORT"] = "8602"

from seamless import communion_server

communion_server.configure_servant(
    buffer=True,
    buffer_status=True
)
communion_server.start()

import seamless
from seamless.core import context, cell

ctx = context(toplevel=True)
ctx.c1 = cell("int").set(1)
ctx.c2 = cell("int").set(2)
ctx.c3 = cell("transformer").set("a + b")

ctx.compute(0.1)
print(ctx.c1, ctx.c1.checksum)
print(ctx.c2, ctx.c2.checksum)
print(ctx.c3, ctx.c3.checksum)

loop = asyncio.get_event_loop()
if len(sys.argv) > 1:
    run_time = float(sys.argv[1])
    loop.call_later(run_time, sys.exit)
loop.run_forever()