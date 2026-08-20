"""Downloading and caching install media. Nothing is fetched until asked."""

import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import catalog
from .constants import ISO_DIR
from .errors import NotFound, BladWirtualki
from .util import human_bytes

CHUNK = 1024 * 256


def cached():
    if not ISO_DIR.is_dir():
        return []
    return sorted(path for path in ISO_DIR.glob("*.iso") if path.is_file())


def path_for(url):
    name = Path(urllib.parse.urlparse(url).path).name
    return ISO_DIR / name


def find_cached(text):
    """Accept a real path, an exact cached name, or a fragment of one."""
    direct = Path(text).expanduser()
    if direct.is_file():
        return direct.resolve()
    matches = [iso for iso in cached() if text in iso.name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(iso.name for iso in matches)
        raise BladWirtualki(f"'{text}' pasuje do kilku plikow: {names}")
    raise NotFound(f"nie ma takiego ISO: {text}")


def _progress(done, total, started):
    elapsed = max(time.time() - started, 0.001)
    speed = human_bytes(done / elapsed)
    if total:
        percent = done * 100 // total
        bar = "#" * (percent // 4) + "." * (25 - percent // 4)
        line = f"\r  [{bar}] {percent:3d}%  {human_bytes(done)}/{human_bytes(total)}  {speed}/s"
    else:
        line = f"\r  {human_bytes(done)}  {speed}/s"
    sys.stderr.write(line)
    sys.stderr.flush()


def download(url, quiet=False, on_progress=None):
    ISO_DIR.mkdir(parents=True, exist_ok=True)
    dest = path_for(url)
    if dest.exists():
        return dest

    part = dest.with_suffix(dest.suffix + ".part")
    offset = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": catalog.USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=catalog.TIMEOUT) as response:
        resuming = response.status == 206
        if offset and not resuming:
            offset = 0
        total = int(response.headers.get("Content-Length") or 0) + offset
        started = time.time()
        done = offset
        with open(part, "ab" if resuming else "wb") as handle:
            if not resuming:
                handle.truncate(0)
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                handle.write(block)
                done += len(block)
                if on_progress:
                    on_progress(done, total)
                elif not quiet:
                    _progress(done, total, started)
    if not quiet and not on_progress:
        sys.stderr.write("\n")
    part.rename(dest)
    return dest


def ensure(slug, quiet=False, on_progress=None):
    """Give back a local ISO for a catalog slug, downloading it if needed."""
    distro = catalog.get(slug)
    url = catalog.resolve(distro)
    dest = path_for(url)
    if dest.exists():
        return dest
    if not quiet:
        print(f"pobieram {distro.name}: {url}")
    return download(url, quiet=quiet, on_progress=on_progress)


def remove(text):
    iso = find_cached(text)
    if iso.parent != ISO_DIR:
        raise BladWirtualki(f"{iso} nie lezy w cache, nie kasuje")
    iso.unlink()
    return iso
