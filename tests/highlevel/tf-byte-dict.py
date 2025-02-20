from seamless.highlevel import Context

ctx = Context()
def code():
    import numpy as np
    a = np.arange(20,80).astype(np.int8)
    return {
        "a": a
    }

ctx.tf = code
ctx.result = ctx.tf
ctx.result2 = ctx.result
ctx.result2.celltype = "mixed"
ctx.a = ctx.result.a
ctx.a.celltype = "bytes"
ctx.compute()
print(ctx.tf.status)
print(ctx.tf.exception)
print(ctx.result.value)
print(ctx.result2.value)
print(ctx.a.value)