from seamless.highlevel import Context, Cell, DeepCell
from seamless.highlevel.stdlib import map

DICT_CHUNKSIZE = 100
ELISION_CHUNKSIZE = 10000

mapped_ctx = Context()
mapped_ctx.inp = Cell("mixed")
mapped_ctx.uniform = Cell("mixed")
def add(d, c):
    print("CHUNK", len(d))
    output = {}
    for k,v in d.items():
        result = v["a"] + v["b"] + c
        output[k] = result
    return output
mapped_ctx.add = add
mapped_ctx.add.pins.d.celltype = "plain"
mapped_ctx.add.d = mapped_ctx.inp
mapped_ctx.add.c = mapped_ctx.uniform
mapped_ctx.result = Cell("mixed")
mapped_ctx.result = mapped_ctx.add
mapped_ctx.subc = Context()
mapped_ctx.subc.blah = 1000
mapped_ctx.compute()

ctx = Context()
ctx.include(map.map_dict_chunk)

ctx.inp0 = DeepCell()
ctx.inp = DeepCell()
ctx.uniform = 1000
ctx.result = DeepCell()
ctx.mapped_ctx = Context()
ctx.keyorder = Cell("plain")
ctx.mapping = ctx.lib.map_dict_chunk(
    context_graph=ctx.mapped_ctx,
    inp=ctx.inp,
    uniform=ctx.uniform,
    result=ctx.result,
    keyorder=ctx.keyorder,
    chunksize=DICT_CHUNKSIZE,
    elision=True,
    elision_chunksize=ELISION_CHUNKSIZE,
)
ctx.result2 = Cell()
ctx.result2.hash_pattern = {"*": "#"}
ctx.result2 = ctx.result
ctx.compute()

import time
globcount = 0
def run(count):
    global globcount
    ctx.inp.checksum = None
    ctx.inp0.set({})
    old = globcount
    inp = {}
    for n in range(count):
        globcount += 1
        inp["k" + str(n+1)] = {"a": globcount, "b": globcount + 0.1}
    ctx.inp0.set(inp)
    ctx.compute(report=False)
    ctx.inp.checksum = ctx.inp0.checksum
    t = time.time()
    ctx.compute(report=False)
    t2 = time.time() - t
    if ctx.result.checksum is not None and ctx.result2.checksum is not None:
        print(len(ctx.result.data.keys()))
        print(sum(ctx.result2.value.values()), count * (2*old + 1000 + 0.1) + 2 * count * (count/2+0.5))
    return t2

ctx.mapped_ctx = mapped_ctx
ctx.translate()
for pcount in range(20):
    count = 2**pcount
    t=run(count)        
    print("TIME", count, t)
    if count < ELISION_CHUNKSIZE:
        print(str(ctx.mapping.ctx.m.ctx.top.ctx.subctx_1.add.logs)[-200:])
    else:
        print(str(ctx.mapping.ctx.m.ctx.top.ctx.m1.ctx.subctx_1.add.logs)[-200:])
    if t > 100:
        break

