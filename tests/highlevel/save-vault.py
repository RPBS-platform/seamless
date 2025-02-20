import json
import seamless
from seamless.highlevel import load_graph, Context

graph = json.load(open("twopi-result.seamless"))
zipfile = "twopi-result.zip"

ctx = Context()
ctx.add_zip(zipfile) # for now, should be before set_graph to avoid glitches
ctx.set_graph(graph)
ctx.translate()

ctx.save_vault("/tmp/seamless-vault")