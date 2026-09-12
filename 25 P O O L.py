import json
import time
import socket
import struct
import queue
import hashlib
import threading
import multiprocessing as mp
import urllib.request
import os
import sys
from fractions import Fraction

PREVHASH_MODE = "word"
DIFF1 = 0x0000FFFF << 224
WORKERS = None
NONCE_BATCH = 512

POOL_HOST = ""
POOL_PORT = 0
USER = ""
PASSWORD = ""

sock = None
msg_id = 0
sub_id = None
auth_id = None
pending = {}

en1 = ""
en2_size = 4
job = None
share_target = None

accepted = 0
rejected = 0


def get_height():
    try:
        with urllib.request.urlopen("https://blockbook.flocard.app/api/v2/", timeout=10) as r:
            res = json.loads(r.read().decode("utf-8", "replace"))
            return res.get("blockbook", {}).get("bestHeight", "Unknown")
    except Exception:
        return "Unknown"


def dsha256(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def pow_hash(header80):
    return hashlib.scrypt(header80, salt=header80, n=1024, r=1, p=1, dklen=32, maxmem=2**22)


def prevhash_wire(prevhex):
    b = bytes.fromhex(prevhex)
    if PREVHASH_MODE == "word":
        return b"".join(b[i:i + 4][::-1] for i in range(0, 32, 4))
    return b[::-1]


def bits_to_target(bits):
    exponent = (bits >> 24) & 0xFF
    mantissa = bits & 0x007FFFFF
    if exponent <= 3:
        return mantissa >> (8 * (3 - exponent))
    return mantissa << (8 * (exponent - 3))


def diff_to_target(diff):
    if diff is None:
        return None
    return int(Fraction(DIFF1) / Fraction(str(diff)))


def send_msg(method, params):
    global msg_id
    msg_id += 1
    message = {"id": msg_id, "method": method, "params": params}
    sock.sendall((json.dumps(message) + "\n").encode())
    return msg_id


def reader(s, q):
    buf = b""
    while True:
        try:
            data = s.recv(4096)
        except Exception:
            q.put(None)
            return
        if not data:
            q.put(None)
            return
        buf += data
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                q.put(json.loads(line))
            except ValueError:
                pass


def handle(msg):
    global en1, en2_size, share_target, job, accepted, rejected, sub_id, auth_id

    method = msg.get("method")

    if method == "mining.set_difficulty":
        try:
            share_target = diff_to_target(msg["params"][0])
            return {"type": "difficulty", "target": share_target}
        except Exception as exc:
            print(f"Error: invalid difficulty: {exc}")
        return None

    if method == "mining.notify":
        try:
            p = msg["params"]
            new_job = {
                "id": p[0], "coinb1": p[2], "coinb2": p[3], "branches": p[4],
                "prevhex": p[1], "verhex": p[5], "bitshex": p[6], "ntime_hex": p[7],
                "target": bits_to_target(int(p[6], 16))
            }
            job = new_job
            return {
                "type": "job", "job": new_job, "en1": en1,
                "en2_size": en2_size, "share_target": share_target
            }
        except Exception as exc:
            print(f"Error: invalid job: {exc}")
        return None

    if sub_id is not None and msg.get("id") == sub_id:
        result = msg.get("result")
        if isinstance(result, list) and len(result) >= 3:
            try:
                en1 = result[1]
                en2_size = int(result[2])
                return {
                    "type": "subscription", "en1": en1, "en2_size": en2_size,
                    "share_target": share_target, "job": job
                }
            except Exception as exc:
                print(f"Error: bad subscription response: {exc}")
        return None

    if auth_id is not None and msg.get("id") == auth_id:
        if not msg.get("result"):
            print(f"Error: authorization failed: {msg.get('error')}")
        return None

    if msg.get("id") in pending:
        pending.pop(msg["id"], None)
        if msg.get("result"):
            accepted += 1
        else:
            rejected += 1
            print(f"Error: share rejected: {msg.get('error')}")
    return None


def build_base(job_data, extranonce1, extranonce2, extranonce2_size):
    if extranonce2 < 0:
        raise ValueError("extranonce2 cannot be negative")

    max_en2 = 1 << (8 * extranonce2_size)
    if extranonce2 >= max_en2:
        raise ValueError("extranonce2 does not fit in requested size")

    en2_hex = extranonce2.to_bytes(extranonce2_size, "little").hex()
    coinbase_hex = job_data["coinb1"] + extranonce1 + en2_hex + job_data["coinb2"]
    coinbase = bytes.fromhex(coinbase_hex)

    root = dsha256(coinbase)
    for branch in job_data["branches"]:
        root = dsha256(root + bytes.fromhex(branch))

    base = (
        struct.pack("<I", int(job_data["verhex"], 16)) +
        prevhash_wire(job_data["prevhex"]) +
        root +
        struct.pack("<I", int(job_data["ntime_hex"], 16)) +
        struct.pack("<I", int(job_data["bitshex"], 16))
    )

    if len(base) != 76:
        raise ValueError(f"block header base is {len(base)} bytes, expected 76")

    return base, en2_hex, job_data["ntime_hex"], job_data["target"]


def mining_worker(worker_id, work_q, result_q, shared_hashes, stop_event):
    local_job = None
    local_en1 = ""
    local_en2_size = 4
    local_share_target = None
    local_worker_count = 1
    en2 = worker_id
    nonce = 0
    header_buf = None
    en2_hex = ""
    nt_hex = ""
    block_target = 0
    local_job_id = None
    local_hashes = 0
    last_report = time.monotonic()

    _pow_hash = pow_hash
    _pack_nonce_into = struct.pack_into
    _from_bytes = int.from_bytes
    _monotonic = time.monotonic

    while not stop_event.is_set():
        try:
            while True:
                item = work_q.get_nowait()
                item_type = item.get("type")

                if item_type == "shutdown":
                    if local_hashes:
                        with shared_hashes.get_lock():
                            shared_hashes.value += local_hashes
                    return
                elif item_type == "config":
                    local_worker_count = max(1, int(item["worker_count"]))
                    en2 = worker_id
                    header_buf = None
                    local_job_id = None
                elif item_type == "subscription":
                    if local_hashes:
                        with shared_hashes.get_lock():
                            shared_hashes.value += local_hashes
                        local_hashes = 0
                    local_en1 = item["en1"]
                    local_en2_size = int(item["en2_size"])
                    local_share_target = item.get("share_target")
                    local_job = item.get("job")
                    header_buf = None
                    local_job_id = None
                    en2 = worker_id
                elif item_type == "difficulty":
                    local_share_target = item["target"]
                elif item_type == "job":
                    if local_hashes:
                        with shared_hashes.get_lock():
                            shared_hashes.value += local_hashes
                        local_hashes = 0
                    local_job = item["job"]
                    local_en1 = item["en1"]
                    local_en2_size = int(item["en2_size"])
                    local_share_target = item.get("share_target")
                    header_buf = None
                    local_job_id = None
                    en2 = worker_id
        except queue.Empty:
            pass

        if local_job is None or local_share_target is None:
            time.sleep(0.01)
            continue

        key = (local_job["id"], en2)

        if key != local_job_id:
            try:
                base, en2_hex, nt_hex, block_target = build_base(local_job, local_en1, en2, local_en2_size)
            except Exception as exc:
                result_q.put({"type": "error", "worker": worker_id, "error": repr(exc)})
                local_job = None
                time.sleep(0.1)
                continue

            local_job_id = key
            nonce = 0
            header_buf = bytearray(base + b"\x00\x00\x00\x00")

        for i in range(NONCE_BATCH):
            if stop_event.is_set():
                if local_hashes:
                    with shared_hashes.get_lock():
                        shared_hashes.value += local_hashes
                return

            _pack_nonce_into("<I", header_buf, 76, nonce)
            h = _pow_hash(header_buf)
            local_hashes += 1
            value = _from_bytes(h, "little")

            if value < local_share_target:
                result_q.put({
                    "type": "share", "worker": worker_id, "job_id": local_job["id"],
                    "en2_hex": en2_hex, "ntime_hex": nt_hex, "nonce": nonce,
                    "block": value < block_target
                })

            if (i & 1023) == 0:
                now = _monotonic()
                if now - last_report >= 1.0 and local_hashes > 0:
                    with shared_hashes.get_lock():
                        shared_hashes.value += local_hashes
                    local_hashes = 0
                    last_report = now

            nonce = (nonce + 1) & 0xFFFFFFFF
            if nonce == 0:
                en2 += local_worker_count
                local_job_id = None
                break


def start_workers(count):
    main_mod = sys.modules.get("__main__")
    if main_mod is not None:
        if not hasattr(main_mod, "__spec__"):
            main_mod.__spec__ = None

    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    ctx = mp.get_context("spawn")
    stop_event = ctx.Event()
    work_queues = []
    processes = []
    result_q = ctx.Queue()
    shared_hashes = ctx.Value("Q", 0)

    for worker_id in range(count):
        q = ctx.Queue()
        p = ctx.Process(
            target=mining_worker,
            args=(worker_id, q, result_q, shared_hashes, stop_event),
            name=f"FLO-Miner-{worker_id}"
        )
        p.daemon = True
        p.start()
        work_queues.append(q)
        processes.append(p)

    for q in work_queues:
        q.put({"type": "config", "worker_count": count})

    return stop_event, work_queues, processes, result_q, shared_hashes


def stop_workers(stop_event, work_queues, processes):
    if stop_event is None:
        return

    stop_event.set()

    for q in work_queues:
        try:
            q.put({"type": "shutdown"})
        except Exception:
            pass

    for p in processes:
        try:
            p.join(timeout=2)
        except Exception:
            pass

    for p in processes:
        if p.is_alive():
            try:
                p.terminate()
                p.join(timeout=1)
            except Exception:
                pass


def submit_loop(result_q, submit_stop):
    while not submit_stop.is_set():
        try:
            result = result_q.get(timeout=0.2)
        except queue.Empty:
            continue

        if result["type"] == "share":
            try:
                sid = send_msg("mining.submit", [
                    USER, result["job_id"], result["en2_hex"],
                    result["ntime_hex"], "%08x" % result["nonce"]
                ])
                pending[sid] = result["nonce"]

                if result["block"]:
                    print("·" * 44)
                    print("Block found")
                    print("·" * 44)
            except Exception as exc:
                print(f"Error: {exc}")

        elif result["type"] == "error":
            print(f"Error: {result['error']}")


def format_hashrate(hps):
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s"]
    i = 0
    while hps >= 1000 and i < len(units) - 1:
        hps /= 1000.0
        i += 1
    return f"{hps:.2f} {units[i]}"


def stats_loop(shared_hashes, stats_stop):
    last_time = time.monotonic()
    last_value = 0

    while not stats_stop.wait(5.0):
        with shared_hashes.get_lock():
            current = shared_hashes.value

        now = time.monotonic()
        rate = (current - last_value) / max(now - last_time, 0.001)

        print(f"{format_hashrate(rate)} | {accepted}/{rejected}")

        last_value = current
        last_time = now


def run():
    global sock, sub_id, auth_id, msg_id, pending
    global job, share_target, en1, en2_size

    worker_count = WORKERS if WORKERS is not None else (os.cpu_count() or 1)
    worker_count = max(1, int(worker_count))

    print(f"CPUs: {os.cpu_count() or 1}")
    print(f"Workers: {worker_count}")
    print("-" * 44)

    while True:
        control_q = queue.Queue()
        s = None
        stop_event = None
        submit_stop = stats_stop = None
        work_queues = []
        processes = []

        pending = {}
        msg_id = 0
        sub_id = auth_id = None
        en1 = ""
        en2_size = 4
        job = share_target = None

        try:
            s = socket.create_connection((POOL_HOST, POOL_PORT), timeout=30)
            s.settimeout(180)
            sock = s

            print("Mining")
            print("-" * 44)

            stop_event, work_queues, processes, result_q, shared_hashes = start_workers(worker_count)

            submit_stop = threading.Event()
            stats_stop = threading.Event()

            threading.Thread(target=submit_loop, args=(result_q, submit_stop), daemon=True).start()
            threading.Thread(target=stats_loop, args=(shared_hashes, stats_stop), daemon=True).start()

            sub_id = send_msg("mining.subscribe", ["pyflo-multi/2.0", None])
            auth_id = send_msg("mining.authorize", [USER, PASSWORD])

            threading.Thread(target=reader, args=(s, control_q), daemon=True).start()

            while True:
                try:
                    m = control_q.get(timeout=1.0)
                except queue.Empty:
                    continue

                if m is None:
                    raise ConnectionError("Connection lost")

                worker_message = handle(m)

                if worker_message is not None:
                    for wq in work_queues:
                        try:
                            wq.put(worker_message)
                        except Exception:
                            pass

        except KeyboardInterrupt:
            return
        except Exception as exc:
            print(f"Error: {exc}")
        finally:
            if submit_stop is not None:
                submit_stop.set()
            if stats_stop is not None:
                stats_stop.set()
            if stop_event is not None:
                stop_workers(stop_event, work_queues, processes)
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
            sock = None

        print("Reconnecting")

        try:
            time.sleep(5)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    mp.freeze_support()

    print("--- P O O L ---")
    print(f"Height: {get_height()}\n")
    print("=" * 44)

    POOL_HOST = input("Host: ").strip()
    port_in = input("Port: ").strip()
    print("·" * 44)

    wallet = input("Address: ").strip()
    worker = input("Worker: ").strip()
    PASSWORD = input("Password: ").strip()
    print("-" * 44)

    if not POOL_HOST:
        print("No host given")
        raise SystemExit

    try:
        POOL_PORT = int(port_in)
    except ValueError:
        print("Port must be a number")
        raise SystemExit

    if not wallet:
        print("No address given")
        raise SystemExit

    if not PASSWORD:
        print("No password given")
        raise SystemExit

    USER = f"{wallet}.{worker}" if worker else wallet

    run()