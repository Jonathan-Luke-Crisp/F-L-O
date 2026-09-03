import base64
import hashlib
import requests
import base58
from datetime import datetime

API_URL = "https://blockbook.flocard.app/api/v2"

BASE_FEE_SATS = 1000
STEP_BASE_SATS = 1000
FLO_ADDRESS_VERSION = 0x23

DEST_BOARD = {
    "a": ("F6jDhqNmmxpdy2jhD3sivryBH6eXXhiMVt"),
    "b": ("FEoS8PfkfUzPGanjoHBscLRbQb3s2aFjJv"),
    "c": ("FV8aSfZQRtQccse8ADdRvhDNwvBzAkEYU8"),
    "d": ("FTzsFTAy9cvmKok3Y5hmy15vXGYiKWvxHm"),
    "e": ("FShUu9vLRM2cjXqFweS1hxZRU96KHKB5CH"),
    "f": ("FCfPQnM85PQVCg3UoJR8krS2Tf8qArm9SK"),
    "g": ("FEfsowkonFF9wvmBkQAC7zegkdYiC1vZnB"),
    "h": ("FABoPkzTQfxRrUMKR4dneN1CzktxVdywmH"),
    "i": ("FPq6LL7MXnYsyyH8rkCERnaQ7ezJec8byP"),
    "j": ("FV7taErVL41jnGdhLbm3UJoXT4itz5DdMR"),
    "k": ("F62SkR7iSLa2dKpVpCodKueArvQ3QLJWb4"),
    "l": ("FCWgxqE1ig4GqbohLhCn5rJRzV2v19pwda"),
    "m": ("FAkuNFTMTdyxwn9dx48n6Z7JdQzf6pJ6uj"),
    "n": ("FMQfCcJFui3PNDiFTHAbvpDWLXuFhLjzHx"),
    "o": ("FTrZkyDp6WxsscRTn3AJgeoFLThWSB1PMi"),
    "p": ("FPbeY2VfApLDnMsErdQNCZmR112mBe3yWu"),
    "q": ("FChL1r2eXiju8H824723uHY3KJQwBED369"),
    "r": ("FTYGpDLS2z5C2Ren43G6sJ4a45uAjoM49P"),
    "s": ("FQgj2yEMj26pZVsEWw61TfjAyeYQaWsFNx"),
    "t": ("F8mccKDhDG74gzmry7DkLmo9yhsbaLHbMs"),
    "u": ("FEtW4BsoyBh7AzDQpvSYCoCAWLguQ9Jy2G"),
    "v": ("F9TPQPwCCchbJ3h7Dch6LUAg5KVftT4TA5"),
    "w": ("FQs69AXTXxMiqtB2ryLmzkgsNM17bNfYhf"),
    "x": ("FDitKcjKfvaL6bHecSeY4Qqm9DydQZCcKy"),
    "y": ("FFDYa6C6G2qHVtvtPk3uVZ1ZYQ1nUaTrYK"),
    "z": ("FFiksUuC4zR482Dt51bGyoAiwvBgWmPf7V"),
    "A": ("FF13Grp5oY29TNpQwwmoUeMuBbuQ57TABV"),
    "B": ("FDuqt4iwhnP3waWCfo2nUgYg2m7LjYYUpc"),
    "C": ("FF46SWJY99gqGQKDBagnRoFqQBxbd3sgSa"),
    "D": ("FUWmgjJfRPY619DuZa6sePCSx2CuPNZNmo"),
    "E": ("FJ4UK6pKE2R6L5V8toRYJsXZk4e17iSauY"),
    "F": ("FU18Cteyo8DFvLZ9yKCkfYoT3Ka8ux3vZd"),
    "G": ("F8suqBt1SUeMW96whsWe3PRw3FnJoQArCg"),
    "H": ("FRtiDMS5uj1Um9cotcFCJ6icHxKKgS8QZR"),
    "I": ("FD7PVpwK7CEb9FAaf1CCyMz3G389bHj5Md"),
    "J": ("FNP2hCJoFXvkYC6yAwC4RW5CYKWAhpQKxS"),
    "K": ("FR84i5ekaQvi7Kmd9aDQxP3C3dXhsfSULf"),
    "L": ("FEE4hoiAUEUAu968kRp8gdsLomHVEeisiG"),
    "M": ("FCaqVXQg72BXv4MapsxiKobChxmkd5iyHM"),
    "N": ("FMxjzQQ46pkeVciLPCjGhE9cQNr7FXctrN"),
    "O": ("FJwutKVgSevJX8XVpsTJJxgM57t6KxnY1z"),
    "P": ("FGfbpMMkr3F7nubkYaJYRGmahTynMfBGYk"),
    "Q": ("FTXxtqaafXwJqRsqKSogrUfDFwHqeTEcEa"),
    "R": ("FQNVQZp6JPeLimdJDZbmHADomEDJwFHsKu"),
    "S": ("FUu3s4Hn5R8YC1mUTPeSC8ztKvaWzFw88a"),
    "T": ("FSuCxwhP8UHg24hzfEuwg83nzabX7ALCc7"),
    "U": ("FJv3B6d9EP5mEHXQAD5p69C9MDZ1LczGok"),
    "V": ("FGmbWTyfswg6zXgtBUc3CakTQsu961iBRL"),
    "W": ("F7UKWSLcSpKRHhS97sgkRtxm2dN4XdtmHd"),
    "X": ("FAwTyeuJVeGQx61KXEPzYcFxGhQywHehZ2"),
    "Y": ("FLaVVFWqz612exEnbq6dUvrKURmeK1HKeP"),
    "Z": ("FKPz5PsQQXUu1UHYNtnQcv75MpJBFkdqhi"),
    "0": ("FDBRhHSPSZjWmZwL9yYz4Xp2AYMq5c8ioC"),
    "1": ("FAJUN5oAuySQ3kyYkq2USm3YP3YJgbnViq"),
    "2": ("FQ1BstRjCe4d9GnGoj7mVYeFY5NVSJdRmH"),
    "3": ("FR8sha4PCgFo5LbAabKa6Aitm4goaeZmNw"),
    "4": ("FQ9U91L9b3yoJKTqZ6h7o352UzGSUG6Qs3"),
    "5": ("F8AaRRGvqrQ7wSHg3qx1pFa9hweCtL3VWU"),
    "6": ("FHeXsbYsrB64zqp5K2mRQhEYsq8wyjZDMN"),
    "7": ("FTSAfAd3t5FS2eLJ8KG1pYAFavekvpu6Tq"),
    "8": ("FRcnAtrpyxUNWVs9yJDsdDxHJMfvJ2E5je"),
    "9": ("F6ASdhgCKdEiUJXZ7Sf764VGK4kS2dzuij"),
    "+": ("F6CXhH7tBpforeBnWniBcAboWkYHEnBUx6"),
    "/": ("FK7ecLx44TwtMjXjZozjDuFK4JukRm7kTJ"),
    "=": ("FUXesV1sstjUrsCPSq77Brh8qQGyB4ECYX"),
}

CHANGE_BOARD = {
    "a": ("FCTRsMiRYGiujsf3HLyfTgRK8zjFtBzAGt"),
    "b": ("FQZhry1vHXJkGRZeTH4NBJMPun1tnmunRF"),
    "c": ("FV1dLSdksQUZdxqsJ2Y4JjgarL54aqsUtE"),
    "d": ("FTy3kXhLWQmJ5Ax1HdzfPMkiBwTsqQWN31"),
    "e": ("FDHE7FYZns8dtrYkaXUXVxgRDwcQB1X7gw"),
    "f": ("FG4d5jpqvCQxQdhA3YDfAAVY8wWiMLcX4x"),
    "g": ("FTd5bSBkSaoXvdfCsYoN15Gv6PRpb9oQRm"),
    "h": ("FAdGuBr8AJbAsqeAMDePAm47UwRiuESz97"),
    "i": ("F6NkPt9M65tj8RpLkwqQX8CJWJgTUsiKPy"),
    "j": ("FMQKfpMSNa7qVJoogDzthgaEU4HaLSZCn6"),
    "k": ("FSTv71ZsQtVmkNUYnJ68xe5qmXyXhNJm99"),
    "l": ("FGqrtA53oGnxpAGhvkf6hgCrrNtp7aftQT"),
    "m": ("FJfpV61gNqZ7NyV82ixe6N4rfN15mmPVLP"),
    "n": ("FPu511JBUwRukYpp7L9oRwKHNoFTCBxi84"),
    "o": ("F83rKXqdo83yfziJk4xpGe7u74d1FnA1XT"),
    "p": ("FKnDvaq4koy4kosSfPVsihHMv3oDQZ4bmM"),
    "q": ("F6mNAo558qXGJ5rDEBNb51bYZgVtjLEVL3"),
    "r": ("FDBWwMGZakeFy85HfesL45C31DPqP3JmQm"),
    "s": ("FGHKLRQLCcgCAYWcsRwzLsHWSZvEwiyH5V"),
    "t": ("F79TDPeGTG8K2wuAmJU3YJPyd7KsZwjSgW"),
    "u": ("F8HiXikbNMEt7HxtiKegz51ph8CuLwfaAt"),
    "v": ("FR5JhzEz4kHtCxiGFnNrpa1BRNAQwgDcRY"),
    "w": ("FFLTbUhDqxKuUEkr9HfdrnaVHgVXL3WFp3"),
    "x": ("FPoPM8NWaxkKRTMVQMFNVMGui7guBbgUC2"),
    "y": ("FJDj9Uqkzn8un68hHas5s9aVksKP3CUyS6"),
    "z": ("FNjZyX1F424VAZCCpg7PqZgNHxtBxq5NNG"),
    "A": ("FUHKM8pUTdE6bSmFFbqQKSXNGfMNhHU6qh"),
    "B": ("FDiuzr6nhEtnBEPJuf6kdrddkAibtHCTD4"),
    "C": ("F8NiSE5rYypft9BJh55p6ewmTqAisSkoXq"),
    "D": ("FRdTuE4qjjWsX4a8pjSJ8KAbrkcyqrx2La"),
    "E": ("FUchbzuMby1wWtfwjVAXJeVSahQTH7Z3tN"),
    "F": ("FG5gnkzsheeJAiRcrAadwoKovEnqAggQgL"),
    "G": ("FPFftEdeaRhq3GZr6Jrv23st9MWRpJpDfT"),
    "H": ("FQES7JYwuDxAZfJTAPb4pBRjxctkU8SbgK"),
    "I": ("FKqASSMgS8YbNt3e8yaiAYVRVrHfQmHLHk"),
    "J": ("FAc9xFVbp3s2y68u4Lfr9nLLdbX3jUDLj8"),
    "K": ("FCgSWoTaTP7awaS8KDhxsW8MifgeLjTurk"),
    "L": ("FNSMHAp9AEPDGN2bUdNAy5d6rHAhjUQ7zC"),
    "M": ("FKGU7ZJNzkpRg4nHwR4BNYMngNEFKjVcDL"),
    "N": ("FENp19UFZbe7JNbkv3t41TU2JrCkLgB3AL"),
    "O": ("F8yM4CLLyCvt4XQCofk9RtVMkJviW6HMKH"),
    "P": ("FH5611arnMGBFHxLMz4wao9rSoNoXPzmVF"),
    "Q": ("FTs4sJi3iPUqFmkU4DbvwRTT2dauH8KHrh"),
    "R": ("FL6vqRk6qw3eTUimVhRtgrRwfZDmjMVq4m"),
    "S": ("FKoAYuF66hdtqYxwvjJXAWggFF2GFrCxWT"),
    "T": ("F7Rkj1iiH9538K4wBCKK2EbpcZJnzJeLVo"),
    "U": ("F6GsqmwCe93mRiUMNZD629ZycMvndKN4XK"),
    "V": ("FLDdWPrP8geXCSp1vBFajnvzSj7G1QZGps"),
    "W": ("F8XxutMTGazc5V7xWG2MGk32cQCHBBK5a2"),
    "X": ("FAacRDm2VCa6DaiJ5L6uFZ6JgXXDMCgjAA"),
    "Y": ("FKFKM1M4Z6vCZV2W2bnc1e2GXesVEFYZ2V"),
    "Z": ("FAUZUPxUffVEiJbMQ8haQFYycF7nNQ9nfC"),
    "0": ("FDARfsjSwvEJ9gRgqjpb1BXJyNNwcYPrGd"),
    "1": ("FNEh9oTLwghftEhJoCwS1dJj2yLvRSnkKy"),
    "2": ("FSoFWQdQcS9YiJykTWvhfUz9FFQvDS4Bc1"),
    "3": ("FBhmqHKYe44yiX1eg1apBgm9zt661gTwZu"),
    "4": ("F6R7M1gpusvfZiCgNvrEVtnVfPVJ3k8gZg"),
    "5": ("FK5ZtZXATpzYHdbeeZcRxdLgMXi1S6vKQy"),
    "6": ("FU4j1BRBhR5XjYb5WSDeX4pjX5t1Uvz32g"),
    "7": ("FGrJuH9zaVHx1feScX6req9WnFMxtrxaxT"),
    "8": ("FUNpiDH3wM1t7qtzFP5LR1gbvSod5dUgzJ"),
    "9": ("FAGyarRhkCLtrFepkymfzE3pMkMWXqe3qJ"),
    "+": ("FSyGFrsPtLTeR6s2Xpx8hkXfiv28jwsBjg"),
    "/": ("FQnFbofByb3ZrcsBmkDoGqDkcghz9NsSrd"),
    "=": ("FLdX6zAiysQjpi9y7Ze83pFAaqWbAjqrrP"),
}

DEST_LOOKUP = {addr: ch for ch, addr in DEST_BOARD.items()}
CHANGE_LOOKUP = {addr: ch for ch, addr in CHANGE_BOARD.items()}

def to_sats(value):
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer() and 0 < value < 1e8:
            return int(value)
        return int(round(value * 1e8))
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return 0
        try:
            return int(s)
        except ValueError:
            pass
        try:
            f = float(s)
            if f.is_integer() and 0 < f < 1e8:
                return int(f)
            return int(round(f * 1e8))
        except ValueError:
            return 0
    return 0


def script_to_address(script_hex):
    if not script_hex or not isinstance(script_hex, str):
        return None
    s = script_hex.lower().strip()
    if len(s) == 50 and s[:6] == "76a914" and s[-6:] == "88ac":
        try:
            pkh = bytes.fromhex(s[6:-6])
            payload = bytes([FLO_ADDRESS_VERSION]) + pkh
            checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            return base58.b58encode(payload + checksum).decode("utf-8")
        except Exception:
            return None
    return None


def get_vout_address(vout_item):
    if not vout_item or not isinstance(vout_item, dict):
        return None
    spk = vout_item.get("scriptPubKey")
    if not isinstance(spk, dict):
        spk = {}
    addrs = spk.get("addresses")
    if isinstance(addrs, list) and addrs:
        return addrs[0]
    if isinstance(addrs, str) and addrs:
        return addrs
    addr = spk.get("address")
    if isinstance(addr, str) and addr:
        return addr
    addrs_top = vout_item.get("addresses")
    if isinstance(addrs_top, list) and addrs_top:
        return addrs_top[0]
    if isinstance(addrs_top, str) and addrs_top:
        return addrs_top
    addr_top = vout_item.get("address")
    if isinstance(addr_top, str) and addr_top:
        return addr_top
    script_hex = (spk.get("hex") or spk.get("script")
                  or vout_item.get("hex") or vout_item.get("script"))
    if script_hex:
        return script_to_address(script_hex)
    return None


def get_vout_sats(vout_item):
    if not vout_item or not isinstance(vout_item, dict):
        return 0
    value_sat = vout_item.get("valueSat")
    if value_sat is not None:
        return to_sats(value_sat)
    return to_sats(vout_item.get("value"))


def offset_to_char(offset):
    if 0 <= offset <= 25:
        return chr(ord("a") + offset)
    if 26 <= offset <= 51:
        return chr(ord("A") + offset - 26)
    if 52 <= offset <= 61:
        return str(offset - 52)
    if offset == 62:
        return "+"
    if offset == 63:
        return "/"
    if offset == 64:
        return "="
    return None

def decode_tx_chunk(tx):
    vout = tx.get("vout", [])
    if len(vout) < 2:
        return None
    sats_out = get_vout_sats(vout[0])
    c1 = offset_to_char(sats_out - STEP_BASE_SATS)
    fee_field = tx.get("fees")
    if fee_field is None:
        fee_field = tx.get("fee", 0)
    fee_sats = to_sats(fee_field)
    c2 = offset_to_char(fee_sats - BASE_FEE_SATS)
    dest_addr = get_vout_address(vout[0])
    c3 = DEST_LOOKUP.get(dest_addr) if dest_addr else None
    change_addr = get_vout_address(vout[1])
    c4 = CHANGE_LOOKUP.get(change_addr) if change_addr else None
    if c1 and c2 and c3 and c4:
        return c1 + c2 + c3 + c4
    return None


def get_tx_sender(tx):
    vin = tx.get("vin", [])
    if not vin:
        return None
    first = vin[0]
    if not isinstance(first, dict):
        return None
    addrs = first.get("addresses")
    if isinstance(addrs, list) and addrs:
        return addrs[0]
    if isinstance(addrs, str) and addrs:
        return addrs
    addr = first.get("addr")
    if isinstance(addr, str) and addr:
        return addr
    addr = first.get("address")
    if isinstance(addr, str) and addr:
        return addr
    return None


def is_sweep_to_origin(tx, origin_address, current_sender):
    vout = tx.get("vout", [])
    if len(vout) != 1:
        return False
    if get_tx_sender(tx) != current_sender:
        return False
    return get_vout_address(vout[0]) == origin_address


def fetch_block_all_txs(session, block_height):
    all_txs = []
    page = 0
    while True:
        url = f"{API_URL}/block/{block_height}" if page == 0 else f"{API_URL}/block/{block_height}/{page}"
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException:
            break
        if resp.status_code != 200:
            break
        try:
            data = resp.json()
        except ValueError:
            break
        txs = data.get("txs")
        if not isinstance(txs, list):
            txs = data.get("block", {}).get("txs", []) if isinstance(data.get("block"), dict) else []
        if not isinstance(txs, list) or not txs:
            break
        all_txs.extend(txs)
        total_pages = data.get("totalPages") or data.get("pages")
        next_page = data.get("nextPage")
        if total_pages is not None:
            if page + 1 >= int(total_pages):
                break
        elif next_page is None:
            break
        page += 1
        if page > 200:
            break
    return all_txs


def fetch_full_tx(session, txid):
    try:
        resp = session.get(f"{API_URL}/tx/{txid}", timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def reconstruct_drip(address, start_block, end_block):
    session = requests.Session()
    b64_chunks = []
    current_sender = address
    chain_complete = False

    for block_height in range(start_block, end_block + 1):
        if chain_complete:
            break
        txs = fetch_block_all_txs(session, block_height)
        for tx in txs:
            sender = get_tx_sender(tx)
            if sender is None:
                txid = tx.get("txid")
                full_tx = fetch_full_tx(session, txid) if txid else None
                if full_tx:
                    tx = full_tx
                    sender = get_tx_sender(tx)
            if sender is None or sender != current_sender:
                continue
            if is_sweep_to_origin(tx, address, current_sender):
                print(f"{block_height} : End")
                chain_complete = True
                break
            chunk = decode_tx_chunk(tx)
            if not chunk:
                txid = tx.get("txid")
                if txid:
                    full_tx = fetch_full_tx(session, txid)
                    if full_tx:
                        chunk = decode_tx_chunk(full_tx)
            if not chunk:
                continue
            print(f"{block_height} : {chunk}")
            b64_chunks.append(chunk)
            c4 = chunk[3]
            next_entry = CHANGE_BOARD.get(c4)
            if not next_entry:
                break
            current_sender = next_entry

    if not b64_chunks:
        print("No DRIP payload found")
        return

    full_b64 = "".join(b64_chunks)
    print("-" * 60)
    print(full_b64)
    print("·" * 60)

    try:
        decoded_bytes = base64.b64decode(full_b64, validate=True)
        filename = datetime.now().strftime("%Y-%m-%d %H%M%S") + ".txt"
        with open(filename, "wb") as f:
            f.write(full_b64.encode("utf-8"))
            f.write(b"\n\n")
            f.write(decoded_bytes)
        try:
            print(decoded_bytes.decode("utf-8"))
        except UnicodeDecodeError:
            print(f"({len(decoded_bytes)} bytes)")
        print("-" * 60)
        print(f"File saved as: {filename}")
        print("-" * 60)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("--- D E C O D E R ---")
    address = input("Address: ").strip()
    if not address:
        raise SystemExit(1)
    range_str = input("Range: ").strip()
    print()
    print("=" * 60)
    try:
        s_block, e_block = map(int, range_str.split("-"))
    except ValueError:
        print("Format: startblock-endblock")
        raise SystemExit(1)
    start_block = min(s_block, e_block)
    end_block = max(s_block, e_block)
    reconstruct_drip(address, start_block, end_block)