"""Throwaway HTTP helpers for the Part A spike. Stdlib only, so the spike
needs no install step and nothing here can leak into the real backend."""
import json, time, urllib.error, urllib.request

UA = "blocklens-spike/0.1"


class Stats:
    """Counts calls and wall time per host so the spike can report cost."""

    def __init__(self):
        self.calls = {}
        self.seconds = {}
        self.errors = {}

    def add(self, host, dt, err=None):
        self.calls[host] = self.calls.get(host, 0) + 1
        self.seconds[host] = self.seconds.get(host, 0.0) + dt
        if err:
            self.errors.setdefault(host, []).append(str(err)[:200])

    def report(self):
        return {
            h: {
                "calls": c,
                "seconds": round(self.seconds[h], 2),
                "errors": len(self.errors.get(h, [])),
            }
            for h, c in sorted(self.calls.items())
        }


STATS = Stats()


def _host(url):
    return url.split("/")[2]


def get_json(url, timeout=25, retries=3, pause=0.25):
    last = None
    for attempt in range(retries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            STATS.add(_host(url), time.time() - t0)
            return json.loads(body)
        except Exception as e:  # noqa: BLE001 - spike
            last = e
            STATS.add(_host(url), time.time() - t0, e)
            time.sleep(pause * (2 ** attempt))
    raise RuntimeError(f"GET failed after {retries}: {url}: {last}")


def rpc(url, method, params, timeout=35, retries=3, pause=0.3, allow_error=False):
    """A JSON-RPC call. Returns (result, error_dict). Errors are returned,
    not raised, when allow_error — probing limits means expecting errors."""
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for attempt in range(retries):
        t0 = time.time()
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"User-Agent": UA, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read())
            STATS.add(_host(url), time.time() - t0)
            if "error" in body:
                if allow_error:
                    return None, body["error"]
                last = RuntimeError(body["error"])
                time.sleep(pause * (2 ** attempt))
                continue
            return body.get("result"), None
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read()[:300].decode("utf8", "replace")
            except Exception:
                pass
            err = {"http": e.code, "body": detail}
            STATS.add(_host(url), time.time() - t0, err)
            if allow_error:
                return None, err
            last = err
            time.sleep(pause * (2 ** attempt))
        except Exception as e:  # noqa: BLE001 - spike
            last = e
            STATS.add(_host(url), time.time() - t0, e)
            time.sleep(pause * (2 ** attempt))
    if allow_error:
        return None, {"failed": str(last)[:200]}
    raise RuntimeError(f"RPC {method} failed: {last}")


def save(name, obj):
    with open(name, "w", encoding="utf8") as f:
        json.dump(obj, f, indent=2)
    print(f"  wrote {name}")


def load(name):
    with open(name, encoding="utf8") as f:
        return json.load(f)
