from copy import deepcopy
import sys
import textwrap
from silk.mixed import MixedBase
import inspect, asyncio

from ..core.cache.buffer_cache import buffer_cache
from ..core.protocol.deserialize import deserialize_sync as deserialize
from ..core.protocol.serialize import serialize_sync as serialize
from ..core.protocol.get_buffer import get_buffer
from ..core.protocol.calculate_checksum import calculate_checksum_sync as calculate_checksum
from ..core.protocol.deep_structure import apply_hash_pattern_sync, deep_structure_to_checksums

def get_checksums(nodes, connections, *, with_annotations):
    def add_checksum(node, dependent, checksum, subpath=None):
        if checksum is None:
            return
        if with_annotations:
            checksums.add((checksum, dependent))
        else:
            checksums.add(checksum)
        hash_pattern = None
        if node["type"] == "cell" and subpath != "schema":
            hash_pattern = node.get("hash_pattern")
        elif node["type"] == "foldercell" and subpath != "schema":
            hash_pattern = {"*": "##"}
        elif node["type"] == "deepcell" and subpath == "origin":
            hash_pattern = {"*": "#"}
        elif node["type"] == "deepfoldercell" and subpath == "origin":
            hash_pattern = {"*": "##"}
        elif node["type"] == "transformer":
            if subpath is not None and subpath.startswith("input") and not subpath.endswith("schema"):
                hash_pattern = node.get("hash_pattern")
        elif node["type"] == "macro":
            if subpath is not None and subpath.startswith("param") and not subpath.endswith("schema"):
                hash_pattern = {"*": "#"}
        else:
            pass
        if hash_pattern is not None:
            buffer = get_buffer(bytes.fromhex(checksum), remote=True, deep=True)
            if buffer is None:
                print("WARNING: could not get checksums for deep structures in {}".format(node["path"]))
                return
            deep_structure = deserialize(buffer, bytes.fromhex(checksum), "plain", copy=False)
            deep_checksums = deep_structure_to_checksums(deep_structure, hash_pattern)
            if with_annotations:
                deep_checksums = [(c, dependent) for c in deep_checksums]
            checksums.update(deep_checksums)
    checksums = set()
    for node in nodes:
        if node["type"] in ("link", "context"):
            continue
        untranslated = node.get("UNTRANSLATED")
        if untranslated:
            continue
        checksum = node.get("checksum")
        if checksum is None:
            continue
        checksum = deepcopy(checksum)
        for connection in connections:
            if connection["type"] == "link":
                continue
            p = connection["target"]
            if p == node["path"]:
                dependent = True
                break
        else:
            dependent = False
        if isinstance(checksum, str):
            add_checksum(node, dependent, checksum)
        else:
            for k,v in checksum.items():
                dependent2 = dependent
                if node["type"] == "transformer":
                    if k.startswith("result"):
                        dependent2 = True
                elif node["type"] == "cell":
                    if node["celltype"] == "structured":
                        if k in ("buffer", "value"):
                            dependent2 = True
                if v is not None:
                    add_checksum(node, dependent2, v, k)
    return checksums

async def get_buffer_dict(manager, checksums):
    from ..core.protocol.get_buffer import get_buffer
    result = {}
    cachemanager = manager.cachemanager
    coros = []
    checksums = list(checksums)
    async def get_buf(checksum):
        return await cachemanager.fingertip(checksum)
    for checksum in checksums:
        coro = get_buf(checksum)
        coros.append(coro)
    buffers = await asyncio.gather(*coros, return_exceptions=True)
    for checksum, buffer in zip(checksums, buffers):
        if not isinstance(buffer, Exception):
            result[checksum] = buffer
    return result

def get_buffer_dict_sync(manager, checksums):
    """This function can be executed if the asyncio event loop is already running"""

    from ..core.protocol.get_buffer import get_buffer
    if not asyncio.get_event_loop().is_running():
        coro = get_buffer_dict(
            manager, checksums
        )
        fut = asyncio.ensure_future(coro)
        asyncio.get_event_loop().run_until_complete(fut)
        return fut.result()

    result = {}
    checksums = list(checksums)
    for checksum in checksums:
        buffer = get_buffer(bytes.fromhex(checksum),remote=True)
        if buffer is not None:
            result[checksum] = buffer
    return result

def add_zip(manager, zipfile, incref=False):
    """
    Caches all checksum-to-buffer entries in zipfile
    All "file names" in the zipfile must be checksum hexes

    Note that caching is temporary and entries will be removed after some time
     if no element (cell, expression, or high-level library) holds their checksum
    This can be overridden with "incref=True" (not recommended for long-living contexts)
    """
    result = []
    for checksum in zipfile.namelist():
        checksum2 = bytes.fromhex(checksum)
        buffer = zipfile.read(checksum)
        buffer_cache.cache_buffer(checksum2, buffer)
        if incref:
            buffer_cache.incref(checksum2, authoritative=False)
        result.append(checksum)
    return result

def fill_checksum(manager, node, temp_path, composite=True):
    from ..core.cell import celltypes
    checksum = None
    subcelltype = None
    hash_pattern = None
    if node["type"] == "cell":
        celltype = node["celltype"]
        hash_pattern = node.get("hash_pattern")
    elif node["type"] == "foldercell":
        celltype = "structured"
        hash_pattern = {"*": "##"}
    elif node["type"] == "deepcell":
        celltype = "structured"
        hash_pattern = {"*": "#"}
    elif node["type"] == "deepfoldercell":
        celltype = "structured"
        hash_pattern = {"*": "##"}
    elif node["type"] == "module":
        celltype = "plain"
    elif node["type"] == "transformer":
        if temp_path == "code":
            datatype = "code"
            if node["language"] == "python":
                celltype = "python"
                subcelltype = "transformer"
            else:
                celltype = "text"
        elif temp_path == "_main_module":
            celltype = "plain"
        else:
            celltype = "structured"
            if temp_path.startswith("input") and not temp_path.endswith("schema"):
                hash_pattern = node.get("hash_pattern")
    elif node["type"] == "macro":
        if temp_path == "code":
            datatype = "code"
            if node["language"] == "python":
                celltype = "python"
                subcelltype = "macro"
            else:
                celltype = "text"
        else:
            celltype = "structured"
            if temp_path.startswith("param") and not temp_path.endswith("schema"):
                hash_pattern = {"*": "#"}
    else:
        raise TypeError(node["type"])
    if celltype == "structured":
        if node["type"] in ("transformer", "macro", "deepcell", "deepfoldercell", "foldercell"):
            datatype = "mixed"
        else:
            datatype = node["datatype"]
            if datatype not in celltypes:
                datatype = "text"
    else:
        datatype = celltype
        if datatype == "code":
            if node["language"] == "python":
                datatype = "python"
            else:
                datatype = "text"
    temp_value = node.get("TEMP")
    if composite:
        if isinstance(temp_value, dict):
            temp_value = temp_value.get(temp_path)
        elif temp_value is None:
            pass
        else:
            raise TypeError(temp_value)
    if temp_value is None:
        return

    if datatype == "python":
        if inspect.isfunction(temp_value):
            code = inspect.getsource(temp_value)
            code = textwrap.dedent(code)
            temp_value = code
    try:
        buf = serialize(temp_value, datatype, use_cache=False)
    except Exception:
        try:
            str_temp_value = str(temp_value)
            if len(str_temp_value) > 100:
                str_temp_value = str_temp_value[:75] + "..." + str_temp_value[-20:]
            str_temp_value = "'" + str_temp_value + "'"
        except Exception:
            str_temp_value = ""
        print(".{}: cannot serialize temporary value {} to {}".format("".join(node["path"]), str_temp_value, datatype))
        return
    checksum = calculate_checksum(buf)

    if checksum is None:
        return
    buffer_cache.cache_buffer(checksum, buf)
    buffer_cache.guarantee_buffer_info(checksum, datatype)
    if hash_pattern is not None:
        try:
            checksum = apply_hash_pattern_sync(
                checksum, hash_pattern
            )
        except:
            msg = "WARNING {}:{} : hash pattern encoding expected, not found (legacy Seamless version?)"
            print(msg.format(node["path"], temp_path), file=sys.stderr)
    checksum = checksum.hex()
    if temp_path is None:
        node["checksum"] = checksum
    else:
        if "checksum" not in node:
            node["checksum"] = {}
        temp_path = temp_path.lstrip("_")
        node["checksum"][temp_path] = checksum

def get_graph_checksums(graph, with_libraries, *, with_annotations):
    nodes0 = graph["nodes"]
    nodes = [node for node in nodes0 if "scratch" not in node]
    connections = graph.get("connections", [])
    checksums = get_checksums(
        nodes, connections,
        with_annotations=with_annotations
    )
    if with_libraries:
        for lib in graph["lib"]:
            lib_checksums = get_graph_checksums(
                lib["graph"],
                with_libraries=True,
                with_annotations=with_annotations
            )
            checksums.update(lib_checksums)
    if with_annotations:
        checksums0 = checksums
        checksums = set()
        for c, dependent in checksums0:
            if not dependent:
                checksums.add((c, False))
        for c, dependent in checksums0:
            if dependent:
                if (c, True) not in checksums:
                    checksums.add((c, True))
    return checksums

def fill_checksums(mgr, nodes, *, path=None):
    """Fills checksums in the nodes from TEMP, if untranslated
    """
    from ..core.structured_cell import StructuredCell
    first_exc = None
    for p in nodes:
        node, old_checksum = None, None
        try:
            pp = path + p if path is not None else p
            node = nodes[p]
            if node["type"] in ("link", "context"):
                continue
            untranslated = node.get("UNTRANSLATED")
            if not untranslated:
                assert "TEMP" not in node, (node["path"], str(node["TEMP"])[:80])
                continue
            old_checksum = node.pop("checksum", None)
            if node["type"] == "transformer":
                fill_checksum(mgr, node, "input_auth")
                node2 = node.copy()
                node2.pop("hash_pattern", None)
                fill_checksum(mgr, node2, "code")
                if "checksum" in node2:
                    node["checksum"] = node2["checksum"]
                fill_checksum(mgr, node2, "result")
                if node["compiled"]:
                    fill_checksum(mgr, node2, "_main_module")
                if "checksum" in node2 and "checksum" not in node:
                    node["checksum"] = node2["checksum"]
            elif node["type"] == "macro":
                fill_checksum(mgr, node, "param_auth")
                fill_checksum(mgr, node, "code")
            elif node["type"] in ("cell", "foldercell"):
                if node["type"] == "foldercell" or node["celltype"] == "structured":
                    temp_path = "auth"
                else:
                    temp_path = "value"
                fill_checksum(mgr, node, temp_path, composite=False)
            elif node["type"] in ("deepcell", "deepfoldercell"):
                fill_checksum(mgr, node, "origin", composite=False)
                fill_checksum(mgr, node, "keyorder", composite=False)
                fill_checksum(mgr, node, "blacklist", composite=False)
                fill_checksum(mgr, node, "whitelist", composite=False)
            elif node["type"] == "module":
                fill_checksum(mgr, node, None, composite=False)
            else:
                raise TypeError(p, node["type"])
            node.pop("TEMP", None)
            if "checksum" not in node:
                if old_checksum is not None:
                    node["checksum"] = old_checksum
            else:
                if old_checksum is not None:
                    if isinstance(node["checksum"], dict):
                        if isinstance(old_checksum, dict):
                            for k in old_checksum:
                                if k not in node["checksum"]:
                                    node["checksum"][k] = old_checksum[k]
        except Exception as exc:
            if first_exc is None:
                first_exc = exc
            else:
                import traceback
                traceback.print_exc()
            if node is not None and old_checksum is not None:
                node["checksum"] = old_checksum
    if first_exc is not None:
        raise first_exc from None