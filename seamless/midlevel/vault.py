import os

SMALL_BIG_THRESHOLD = 100000  # for now, the same as buffer_cache.SMALL_BUFFER_LIMIT

def save_vault(dirname, annotated_checksums, buffer_dict):
    dirs = {}
    for dep in ("independent", "dependent"):
        for size in ("small", "big"):
            dirn = os.path.join(dirname, dep, size)
            os.makedirs(dirn, exist_ok=True)
            with open(os.path.join(dirn, ".gitkeep"), "w") as f:
                pass
            dirs[dep, size] = dirn

    for checksum, is_dependent in annotated_checksums:
        buffer = buffer_dict[checksum]
        size = "small" if len(buffer) <= SMALL_BIG_THRESHOLD else "big"
        dep = "dependent" if is_dependent else "independent"
        dirn = dirs[dep, size]
        filename = os.path.join(dirn, checksum)
        with open(filename, "wb") as f:
            f.write(buffer)

def load_vault(dirname, incref=False):
    if not os.path.exists(dirname):
        raise ValueError(dirname)
    result = []
    ok = False
    for dep in ("independent", "dependent"):
        for size in ("small", "big"):
            dirn = os.path.join(dirname, dep, size)
            if not os.path.exists(dirn):
                continue
            ok = True
            for _, _, files in os.walk(dirn):
                for filename in files:
                    if filename.startswith("."):
                        continue
                    checksum = filename
                    checksum2 = bytes.fromhex(checksum)
                    with open(os.path.join(dirn, filename), "rb") as f:
                        buffer = f.read()
                    buffer_cache.cache_buffer(checksum2, buffer)
                    if incref:
                        buffer_cache.incref(checksum2, authoritative=False)
                    result.append(checksum)
    if not ok:
        raise ValueError("{} does seem to be a Seamless vault".format(dirname))
    return result

from ..core.cache.buffer_cache import buffer_cache