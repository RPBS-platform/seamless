"""Defines a dummy server that does transformations and gives back preliminary and progress results"""

import asyncio
import seamless
import json
from seamless.core import context, cell, transformer, macro_mode_on
from seamless import calculate_checksum

def h(value):
    return calculate_checksum(json.dumps(value)+"\n")

seamless.set_ncores(0)

class DummyClient:
    def __init__(self):
        self.st = 1
        self.progress = 0
        self.prelim = None
        self.job = None
        self.queue = asyncio.Queue()
    async def _server(self):
        print("Server")
        for n in range(10):
            await asyncio.sleep(1)
            self.progress = 10 * (n+1)
            print("Server PROGRESS", self.progress)
            prelim = 0.1 * (n+1)
            print("Server PRELIM", prelim)
            self.prelim = h(prelim)
            await self.queue.put(None)
        self.st = 3        
        self.result = h(1.0)        
        await self.queue.put(None)
    async def submit(self, checksum):
        self.checksum = checksum
        self.job = asyncio.ensure_future(self._server())
        self.st = 2
    async def wait(self, checksum):
        await self.queue.get()
        while 1:
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    async def status(self, checksum):
        if self.st == 2:
            return self.st, self.progress, self.prelim
        elif self.st == 3:
            return self.st, self.result
        else:
            return self.st, None

from seamless.communion_client import communion_client_manager
m = communion_client_manager
m.clients["transformation"] = [
    DummyClient(),
] # dirty hack

with macro_mode_on():
    ctx = context(toplevel=True)
    ctx.cell1 = cell().set(2)
    ctx.cell2 = cell().set(3)
    ctx.code = cell("python").set("c = a + b")
    ctx.result = cell()
    ctx.tf = transformer({
        "a": "input",
        "b": "input",
        "c": "output"
    })
    ctx.cell1.connect(ctx.tf.a)
    ctx.cell2.connect(ctx.tf.b)
    ctx.tf.c.connect(ctx.result)
    ctx.code.connect(ctx.tf.code)
    ctx.hashcell = cell()

for n in range(10):
    ctx.hashcell.set(0.1 * (n+1) )
    ctx.compute(0.05)

for n in range(25):
    print("STEP", n+1)
    print(ctx.tf.status)
    print(ctx.tf.value)
    print(ctx.result.status)
    print(ctx.result.value)
    print()
    ctx.compute(0.5)
    
ctx.compute()
print(ctx.status)
print(ctx.result.value)
print("STOP")