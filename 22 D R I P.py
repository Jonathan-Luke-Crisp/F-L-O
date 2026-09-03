import hashlib
import time
import requests
import ecdsa
import base58
import base64

API_URL = "https://blockbook.flocard.app/api/v2"
BASE_FEE_SATS = 1000
STEP_BASE_SATS = 1000

DEST_BOARD = {
    "a": ("F6jDhqNmmxpdy2jhD3sivryBH6eXXhiMVt", "a "),
    "b": ("FEoS8PfkfUzPGanjoHBscLRbQb3s2aFjJv", "b "),
    "c": ("FV8aSfZQRtQccse8ADdRvhDNwvBzAkEYU8", "c "),
    "d": ("FTzsFTAy9cvmKok3Y5hmy15vXGYiKWvxHm", "d "),
    "e": ("FShUu9vLRM2cjXqFweS1hxZRU96KHKB5CH", "e "),
    "f": ("FCfPQnM85PQVCg3UoJR8krS2Tf8qArm9SK", "f "),
    "g": ("FEfsowkonFF9wvmBkQAC7zegkdYiC1vZnB", "g "),
    "h": ("FABoPkzTQfxRrUMKR4dneN1CzktxVdywmH", "h "),
    "i": ("FPq6LL7MXnYsyyH8rkCERnaQ7ezJec8byP", "i "),
    "j": ("FV7taErVL41jnGdhLbm3UJoXT4itz5DdMR", "j "),
    "k": ("F62SkR7iSLa2dKpVpCodKueArvQ3QLJWb4", "k "),
    "l": ("FCWgxqE1ig4GqbohLhCn5rJRzV2v19pwda", "l "),
    "m": ("FAkuNFTMTdyxwn9dx48n6Z7JdQzf6pJ6uj", "m "),
    "n": ("FMQfCcJFui3PNDiFTHAbvpDWLXuFhLjzHx", "n "),
    "o": ("FTrZkyDp6WxsscRTn3AJgeoFLThWSB1PMi", "o "),
    "p": ("FPbeY2VfApLDnMsErdQNCZmR112mBe3yWu", "p "),
    "q": ("FChL1r2eXiju8H824723uHY3KJQwBED369", "q "),
    "r": ("FTYGpDLS2z5C2Ren43G6sJ4a45uAjoM49P", "r "),
    "s": ("FQgj2yEMj26pZVsEWw61TfjAyeYQaWsFNx", "s "),
    "t": ("F8mccKDhDG74gzmry7DkLmo9yhsbaLHbMs", "t "),
    "u": ("FEtW4BsoyBh7AzDQpvSYCoCAWLguQ9Jy2G", "u "),
    "v": ("F9TPQPwCCchbJ3h7Dch6LUAg5KVftT4TA5", "v "),
    "w": ("FQs69AXTXxMiqtB2ryLmzkgsNM17bNfYhf", "w "),
    "x": ("FDitKcjKfvaL6bHecSeY4Qqm9DydQZCcKy", "x "),
    "y": ("FFDYa6C6G2qHVtvtPk3uVZ1ZYQ1nUaTrYK", "y "),
    "z": ("FFiksUuC4zR482Dt51bGyoAiwvBgWmPf7V", "z "),
    "A": ("FF13Grp5oY29TNpQwwmoUeMuBbuQ57TABV", "A "),
    "B": ("FDuqt4iwhnP3waWCfo2nUgYg2m7LjYYUpc", "B "),
    "C": ("FF46SWJY99gqGQKDBagnRoFqQBxbd3sgSa", "C "),
    "D": ("FUWmgjJfRPY619DuZa6sePCSx2CuPNZNmo", "D "),
    "E": ("FJ4UK6pKE2R6L5V8toRYJsXZk4e17iSauY", "E "),
    "F": ("FU18Cteyo8DFvLZ9yKCkfYoT3Ka8ux3vZd", "F "),
    "G": ("F8suqBt1SUeMW96whsWe3PRw3FnJoQArCg", "G "),
    "H": ("FRtiDMS5uj1Um9cotcFCJ6icHxKKgS8QZR", "H "),
    "I": ("FD7PVpwK7CEb9FAaf1CCyMz3G389bHj5Md", "I "),
    "J": ("FNP2hCJoFXvkYC6yAwC4RW5CYKWAhpQKxS", "J "),
    "K": ("FR84i5ekaQvi7Kmd9aDQxP3C3dXhsfSULf", "K "),
    "L": ("FEE4hoiAUEUAu968kRp8gdsLomHVEeisiG", "L "),
    "M": ("FCaqVXQg72BXv4MapsxiKobChxmkd5iyHM", "M "),
    "N": ("FMxjzQQ46pkeVciLPCjGhE9cQNr7FXctrN", "N "),
    "O": ("FJwutKVgSevJX8XVpsTJJxgM57t6KxnY1z", "O "),
    "P": ("FGfbpMMkr3F7nubkYaJYRGmahTynMfBGYk", "P "),
    "Q": ("FTXxtqaafXwJqRsqKSogrUfDFwHqeTEcEa", "Q "),
    "R": ("FQNVQZp6JPeLimdJDZbmHADomEDJwFHsKu", "R "),
    "S": ("FUu3s4Hn5R8YC1mUTPeSC8ztKvaWzFw88a", "S "),
    "T": ("FSuCxwhP8UHg24hzfEuwg83nzabX7ALCc7", "T "),
    "U": ("FJv3B6d9EP5mEHXQAD5p69C9MDZ1LczGok", "U "),
    "V": ("FGmbWTyfswg6zXgtBUc3CakTQsu961iBRL", "V "),
    "W": ("F7UKWSLcSpKRHhS97sgkRtxm2dN4XdtmHd", "W "),
    "X": ("FAwTyeuJVeGQx61KXEPzYcFxGhQywHehZ2", "X "),
    "Y": ("FLaVVFWqz612exEnbq6dUvrKURmeK1HKeP", "Y "),
    "Z": ("FKPz5PsQQXUu1UHYNtnQcv75MpJBFkdqhi", "Z "),
    "0": ("FDBRhHSPSZjWmZwL9yYz4Xp2AYMq5c8ioC", "0 "),
    "1": ("FAJUN5oAuySQ3kyYkq2USm3YP3YJgbnViq", "1 "),
    "2": ("FQ1BstRjCe4d9GnGoj7mVYeFY5NVSJdRmH", "2 "),
    "3": ("FR8sha4PCgFo5LbAabKa6Aitm4goaeZmNw", "3 "),
    "4": ("FQ9U91L9b3yoJKTqZ6h7o352UzGSUG6Qs3", "4 "),
    "5": ("F8AaRRGvqrQ7wSHg3qx1pFa9hweCtL3VWU", "5 "),
    "6": ("FHeXsbYsrB64zqp5K2mRQhEYsq8wyjZDMN", "6 "),
    "7": ("FTSAfAd3t5FS2eLJ8KG1pYAFavekvpu6Tq", "7 "),
    "8": ("FRcnAtrpyxUNWVs9yJDsdDxHJMfvJ2E5je", "8 "),
    "9": ("F6ASdhgCKdEiUJXZ7Sf764VGK4kS2dzuij", "9 "),
    "+": ("F6CXhH7tBpforeBnWniBcAboWkYHEnBUx6", "+ "),
    "/": ("FK7ecLx44TwtMjXjZozjDuFK4JukRm7kTJ", "/ "),
    "=": ("FUXesV1sstjUrsCPSq77Brh8qQGyB4ECYX", "= "),
}

CHANGE_BOARD = {
    "a": ("FCTRsMiRYGiujsf3HLyfTgRK8zjFtBzAGt", " a"),
    "b": ("FQZhry1vHXJkGRZeTH4NBJMPun1tnmunRF", " b"),
    "c": ("FV1dLSdksQUZdxqsJ2Y4JjgarL54aqsUtE", " c"),
    "d": ("FTy3kXhLWQmJ5Ax1HdzfPMkiBwTsqQWN31", " d"),
    "e": ("FDHE7FYZns8dtrYkaXUXVxgRDwcQB1X7gw", " e"),
    "f": ("FG4d5jpqvCQxQdhA3YDfAAVY8wWiMLcX4x", " f"),
    "g": ("FTd5bSBkSaoXvdfCsYoN15Gv6PRpb9oQRm", " g"),
    "h": ("FAdGuBr8AJbAsqeAMDePAm47UwRiuESz97", " h"),
    "i": ("F6NkPt9M65tj8RpLkwqQX8CJWJgTUsiKPy", " i"),
    "j": ("FMQKfpMSNa7qVJoogDzthgaEU4HaLSZCn6", " j"),
    "k": ("FSTv71ZsQtVmkNUYnJ68xe5qmXyXhNJm99", " k"),
    "l": ("FGqrtA53oGnxpAGhvkf6hgCrrNtp7aftQT", " l"),
    "m": ("FJfpV61gNqZ7NyV82ixe6N4rfN15mmPVLP", " m"),
    "n": ("FPu511JBUwRukYpp7L9oRwKHNoFTCBxi84", " n"),
    "o": ("F83rKXqdo83yfziJk4xpGe7u74d1FnA1XT", " o"),
    "p": ("FKnDvaq4koy4kosSfPVsihHMv3oDQZ4bmM", " p"),
    "q": ("F6mNAo558qXGJ5rDEBNb51bYZgVtjLEVL3", " q"),
    "r": ("FDBWwMGZakeFy85HfesL45C31DPqP3JmQm", " r"),
    "s": ("FGHKLRQLCcgCAYWcsRwzLsHWSZvEwiyH5V", " s"),
    "t": ("F79TDPeGTG8K2wuAmJU3YJPyd7KsZwjSgW", " t"),
    "u": ("F8HiXikbNMEt7HxtiKegz51ph8CuLwfaAt", " u"),
    "v": ("FR5JhzEz4kHtCxiGFnNrpa1BRNAQwgDcRY", " v"),
    "w": ("FFLTbUhDqxKuUEkr9HfdrnaVHgVXL3WFp3", " w"),
    "x": ("FPoPM8NWaxkKRTMVQMFNVMGui7guBbgUC2", " x"),
    "y": ("FJDj9Uqkzn8un68hHas5s9aVksKP3CUyS6", " y"),
    "z": ("FNjZyX1F424VAZCCpg7PqZgNHxtBxq5NNG", " z"),
    "A": ("FUHKM8pUTdE6bSmFFbqQKSXNGfMNhHU6qh", " A"),
    "B": ("FDiuzr6nhEtnBEPJuf6kdrddkAibtHCTD4", " B"),
    "C": ("F8NiSE5rYypft9BJh55p6ewmTqAisSkoXq", " C"),
    "D": ("FRdTuE4qjjWsX4a8pjSJ8KAbrkcyqrx2La", " D"),
    "E": ("FUchbzuMby1wWtfwjVAXJeVSahQTH7Z3tN", " E"),
    "F": ("FG5gnkzsheeJAiRcrAadwoKovEnqAggQgL", " F"),
    "G": ("FPFftEdeaRhq3GZr6Jrv23st9MWRpJpDfT", " G"),
    "H": ("FQES7JYwuDxAZfJTAPb4pBRjxctkU8SbgK", " H"),
    "I": ("FKqASSMgS8YbNt3e8yaiAYVRVrHfQmHLHk", " I"),
    "J": ("FAc9xFVbp3s2y68u4Lfr9nLLdbX3jUDLj8", " J"),
    "K": ("FCgSWoTaTP7awaS8KDhxsW8MifgeLjTurk", " K"),
    "L": ("FNSMHAp9AEPDGN2bUdNAy5d6rHAhjUQ7zC", " L"),
    "M": ("FKGU7ZJNzkpRg4nHwR4BNYMngNEFKjVcDL", " M"),
    "N": ("FENp19UFZbe7JNbkv3t41TU2JrCkLgB3AL", " N"),
    "O": ("F8yM4CLLyCvt4XQCofk9RtVMkJviW6HMKH", " O"),
    "P": ("FH5611arnMGBFHxLMz4wao9rSoNoXPzmVF", " P"),
    "Q": ("FTs4sJi3iPUqFmkU4DbvwRTT2dauH8KHrh", " Q"),
    "R": ("FL6vqRk6qw3eTUimVhRtgrRwfZDmjMVq4m", " R"),
    "S": ("FKoAYuF66hdtqYxwvjJXAWggFF2GFrCxWT", " S"),
    "T": ("F7Rkj1iiH9538K4wBCKK2EbpcZJnzJeLVo", " T"),
    "U": ("F6GsqmwCe93mRiUMNZD629ZycMvndKN4XK", " U"),
    "V": ("FLDdWPrP8geXCSp1vBFajnvzSj7G1QZGps", " V"),
    "W": ("F8XxutMTGazc5V7xWG2MGk32cQCHBBK5a2", " W"),
    "X": ("FAacRDm2VCa6DaiJ5L6uFZ6JgXXDMCgjAA", " X"),
    "Y": ("FKFKM1M4Z6vCZV2W2bnc1e2GXesVEFYZ2V", " Y"),
    "Z": ("FAUZUPxUffVEiJbMQ8haQFYycF7nNQ9nfC", " Z"),
    "0": ("FDARfsjSwvEJ9gRgqjpb1BXJyNNwcYPrGd", " 0"),
    "1": ("FNEh9oTLwghftEhJoCwS1dJj2yLvRSnkKy", " 1"),
    "2": ("FSoFWQdQcS9YiJykTWvhfUz9FFQvDS4Bc1", " 2"),
    "3": ("FBhmqHKYe44yiX1eg1apBgm9zt661gTwZu", " 3"),
    "4": ("F6R7M1gpusvfZiCgNvrEVtnVfPVJ3k8gZg", " 4"),
    "5": ("FK5ZtZXATpzYHdbeeZcRxdLgMXi1S6vKQy", " 5"),
    "6": ("FU4j1BRBhR5XjYb5WSDeX4pjX5t1Uvz32g", " 6"),
    "7": ("FGrJuH9zaVHx1feScX6req9WnFMxtrxaxT", " 7"),
    "8": ("FUNpiDH3wM1t7qtzFP5LR1gbvSod5dUgzJ", " 8"),
    "9": ("FAGyarRhkCLtrFepkymfzE3pMkMWXqe3qJ", " 9"),
    "+": ("FSyGFrsPtLTeR6s2Xpx8hkXfiv28jwsBjg", " +"),
    "/": ("FQnFbofByb3ZrcsBmkDoGqDkcghz9NsSrd", " /"),
    "=": ("FLdX6zAiysQjpi9y7Ze83pFAaqWbAjqrrP", " ="),
}

def get_block_height():
    try:
        resp = requests.get(API_URL, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("blockbook", {}).get("bestHeight", "N/A")
    except Exception:
        pass
    return "N/A"

def dsha256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def to_le_hex(value, length):
    return value.to_bytes(length, 'little').hex()

def make_varint(n):
    if n < 0xfd: return to_le_hex(n, 1)
    if n <= 0xffff: return "fd" + to_le_hex(n, 2)
    if n <= 0xffffffff: return "fe" + to_le_hex(n, 4)
    return "ff" + to_le_hex(n, 8)

def address_to_pkh(address):
    return base58.b58decode(address)[1:21].hex()

def mnemonic_to_private_key(mnemonic_phrase):
    seed = hashlib.pbkdf2_hmac('sha512', mnemonic_phrase.encode('utf-8'), b'mnemonic', 2048)
    return seed[:32]

def get_public_key(priv_key_bytes):
    sk = ecdsa.SigningKey.from_string(priv_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    pubkey = vk.to_string()
    prefix = b'\x02' if pubkey[-1] % 2 == 0 else b'\x03'
    return (prefix + pubkey[:32]).hex()

def get_flo_address(pubkey_bytes):
    sha = hashlib.sha256(pubkey_bytes).digest()
    ripemd = hashlib.new('ripemd160')
    ripemd.update(sha)
    payload = b'\x23' + ripemd.digest()
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    b58_addr = base58.b58encode(payload + checksum)
    return b58_addr.decode('utf-8') if isinstance(b58_addr, bytes) else b58_addr

def sign_low_s(priv_key_bytes, hash_to_sign):
    sk = ecdsa.SigningKey.from_string(priv_key_bytes, curve=ecdsa.SECP256k1)
    sig = sk.sign_digest_deterministic(hash_to_sign, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_string)
    r, s = ecdsa.util.sigdecode_string(sig, sk.curve.order)
    if s > sk.curve.order // 2:
        s = sk.curve.order - s
    return ecdsa.util.sigencode_der(r, s, sk.curve.order)

def validate_board(board, name):
    for char, (address, mnemonic) in board.items():
        private_key = mnemonic_to_private_key(mnemonic)
        pub_key_hex = get_public_key(private_key)
        derived_address = get_flo_address(bytes.fromhex(pub_key_hex))

        if derived_address != address:
            print(f"{name} ERROR: {char} / {mnemonic}")
            print(f"Expected: {address}")
            print(f"Derived:  {derived_address}")
            return False

    return True

def char_to_offset(c):
    if 'a' <= c <= 'z':
        return ord(c) - ord('a')
    elif 'A' <= c <= 'Z':
        return 26 + (ord(c) - ord('A'))
    elif '0' <= c <= '9':
        return 52 + (ord(c) - ord('0'))
    elif c == '+':
        return 62
    elif c == '/':
        return 63
    elif c == '=':
        return 64
    return 0

def get_utxo(address):
    try:
        resp = requests.get(f"{API_URL}/utxo/{address}", timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"Blockbook UTXO request failed (HTTP {resp.status_code}): {resp.text}")
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected UTXO response for {address}: {data}")
        return data
    except requests.RequestException as e:
        raise RuntimeError(f"Blockbook connection failed: {e}") from e
    except ValueError as e:
        raise RuntimeError(f"Invalid JSON returned by Blockbook: {e}") from e

def broadcast_tx(final_hex):
    try:
        resp = requests.post(f"{API_URL}/sendtx/", data=final_hex, timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}

def wait_for_confirmation(txid):
    while True:
        try:
            resp = requests.get(f"{API_URL}/tx/{txid}", timeout=5)
            if resp.status_code == 200 and resp.json().get("confirmations", 0) > 0:
                return True
        except Exception:
            pass
        time.sleep(2)

def construct_drip_tx(
    priv_key_bytes,
    sender_addr,
    dest_addr,
    change_addr,
    amount_sats,
    encoded_fee_sats,
    utxos,
    main_change_addr=None,
    total_budget_sats=0
):
    pub_key_hex = get_public_key(priv_key_bytes)
    dest_script = f"76a914{address_to_pkh(dest_addr)}88ac"
    change_script = f"76a914{address_to_pkh(change_addr)}88ac"
    
    collected_sats = sum(int(u['value']) for u in utxos)
    
    out1 = to_le_hex(amount_sats, 8) + make_varint(len(dest_script)//2) + dest_script
    
    if main_change_addr:
        drip_chain_sats = total_budget_sats - amount_sats - encoded_fee_sats
        main_change_sats = collected_sats - total_budget_sats
        
        if drip_chain_sats <= 0 or main_change_sats <= 0:
            raise ValueError("Insufficient budget or main balance")
            
        out2 = to_le_hex(drip_chain_sats, 8) + make_varint(len(change_script)//2) + change_script
        main_script = f"76a914{address_to_pkh(main_change_addr)}88ac"
        out3 = to_le_hex(main_change_sats, 8) + make_varint(len(main_script)//2) + main_script
        outputs_hex = make_varint(3) + out1 + out2 + out3
    else:
        chain_change_sats = collected_sats - amount_sats - encoded_fee_sats
        if chain_change_sats <= 0:
            raise ValueError("Drip budget exhausted")
        out2 = to_le_hex(chain_change_sats, 8) + make_varint(len(change_script)//2) + change_script
        outputs_hex = make_varint(2) + out1 + out2

    version = "02000000"
    locktime = "00000000"
    flo_data_field = "00"
    sighash_type = "01000000"
    
    inputs_data = [{'txid_rev': bytes.fromhex(u['txid'])[::-1].hex(), 'vout_hex': to_le_hex(u['vout'], 4)} for u in utxos]
    sender_script = f"76a914{address_to_pkh(sender_addr)}88ac"
    
    final_inputs = []
    for i in range(len(inputs_data)):
        inputs_for_hashing = make_varint(len(inputs_data))
        for j in range(len(inputs_data)):
            if i == j:
                inputs_for_hashing += inputs_data[j]['txid_rev'] + inputs_data[j]['vout_hex'] + make_varint(len(sender_script)//2) + sender_script + "ffffffff"
            else:
                inputs_for_hashing += inputs_data[j]['txid_rev'] + inputs_data[j]['vout_hex'] + "00" + "ffffffff"
                
        hash_to_sign = dsha256(bytes.fromhex(version + inputs_for_hashing + outputs_hex + locktime + flo_data_field + sighash_type))
        sig_der = sign_low_s(priv_key_bytes, hash_to_sign)
        script_sig = make_varint(len(sig_der) + 1) + (sig_der + b'\x01').hex() + make_varint(len(pub_key_hex)//2) + pub_key_hex
        final_inputs.append(inputs_data[i]['txid_rev'] + inputs_data[i]['vout_hex'] + make_varint(len(script_sig)//2) + script_sig + "ffffffff")
        
    return version + make_varint(len(final_inputs)) + "".join(final_inputs) + outputs_hex + locktime + flo_data_field

def construct_sweep_tx(
    priv_key_bytes,
    sender_addr,
    destination_addr,
    utxos,
    fee_sats
):
    pub_key_hex = get_public_key(priv_key_bytes)
    destination_script = f"76a914{address_to_pkh(destination_addr)}88ac"

    collected_sats = sum(int(u["value"]) for u in utxos)
    amount_sats = collected_sats - fee_sats

    if amount_sats <= 546:
        raise ValueError("Insufficient funds for sweep")

    out = to_le_hex(amount_sats, 8) + make_varint(len(destination_script) // 2) + destination_script
    outputs_hex = make_varint(1) + out

    version = "02000000"
    locktime = "00000000"
    flo_data_field = "00"
    sighash_type = "01000000"

    sender_script = f"76a914{address_to_pkh(sender_addr)}88ac"
    inputs_data = [{"txid_rev": bytes.fromhex(u["txid"])[::-1].hex(), "vout_hex": to_le_hex(u["vout"], 4)} for u in utxos]

    final_inputs = []
    for i in range(len(inputs_data)):
        inputs_for_hashing = make_varint(len(inputs_data))
        for j in range(len(inputs_data)):
            if i == j:
                inputs_for_hashing += inputs_data[j]["txid_rev"] + inputs_data[j]["vout_hex"] + make_varint(len(sender_script) // 2) + sender_script + "ffffffff"
            else:
                inputs_for_hashing += inputs_data[j]["txid_rev"] + inputs_data[j]["vout_hex"] + "00" + "ffffffff"

        hash_to_sign = dsha256(bytes.fromhex(version + inputs_for_hashing + outputs_hex + locktime + flo_data_field + sighash_type))
        sig_der = sign_low_s(priv_key_bytes, hash_to_sign)
        script_sig = make_varint(len(sig_der) + 1) + (sig_der + b"\x01").hex() + make_varint(len(pub_key_hex) // 2) + pub_key_hex
        final_inputs.append(inputs_data[i]["txid_rev"] + inputs_data[i]["vout_hex"] + make_varint(len(script_sig) // 2) + script_sig + "ffffffff")

    return version + make_varint(len(final_inputs)) + "".join(final_inputs) + outputs_hex + locktime + flo_data_field

if __name__ == "__main__":

    if not validate_board(DEST_BOARD, "DEST_BOARD"):
        exit()

    if not validate_board(CHANGE_BOARD, "CHANGE_BOARD"):
        exit()

    current_height = get_block_height()
    print("--- D R I P ---")
    print(f"Height: {current_height}\n")
    print("=" * 60)
    key_input = input("Key: ").strip()
    print("-" * 60)

    if len(key_input) in [51, 52]:
        private_key = base58.b58decode(key_input)[1:33]
    elif len(key_input) == 64:
        private_key = bytes.fromhex(key_input)
    else:
        private_key = mnemonic_to_private_key(key_input)

    main_priv = private_key
    pub_key_hex = get_public_key(private_key)
    sender_address = get_flo_address(bytes.fromhex(pub_key_hex))
    original_address = sender_address

    try:
        utxos = get_utxo(original_address)
    except RuntimeError as e:
        print(f"UTXO lookup failed: {e}")
        print("-" * 60)
        exit()

    total_balance_sats = sum(int(u["value"]) for u in utxos)
    balance_flo = total_balance_sats / 100_000_000

    print(f"Address: {original_address}")
    print(f"Balance: {balance_flo:.8f}")
    print("·" * 60)

    if total_balance_sats == 0:
        print("Insufficient funds")
        print("-" * 60)
        exit()

    mode = input("Text or Base64 (1/2): ").strip()
    print("·" * 60)

    if mode == "1":
        msg = input("Encode: ").strip()
        print("·" * 60)
        b64 = base64.b64encode(msg.encode("utf-8")).decode("ascii")
        print(f"String: {b64}")

    elif mode == "2":
        b64 = input("String: ").strip()
        print("·" * 60)
        try:
            base64.b64decode(b64, validate=True)
        except Exception:
            print("Invalid Base64")
            print("-" * 60)
            exit()
            
        if len(b64) % 4 != 0:
            print("Invalid Base64")
            print("-" * 60)
            exit()

    else:
        print("Enter 1 or 2")
        print("-" * 60)
        exit()

    total_chunks = len(b64) // 4
    total_tx_count = total_chunks + 1  

    print(f"{len(b64)} Characters")
    print(f"{total_tx_count} Transactions")
    print("-" * 60)

    tx_plan = []
    invalid_chars = False

    for i in range(0, len(b64), 4):
        chunk = b64[i:i+4]
        c1, c2, c3, c4 = chunk[0], chunk[1], chunk[2], chunk[3]

        dest_entry   = DEST_BOARD.get(c3)
        change_entry = CHANGE_BOARD.get(c4)

        if not dest_entry or not change_entry:
            print(f"Error: Missing board entry for characters '{c3}' / '{c4}'")
            invalid_chars = True
            break

        tx_plan.append({
            "chunk": chunk,
            "c1": c1,
            "c2": c2,
            "c3": c3,
            "c4": c4,
            "amount_sats": STEP_BASE_SATS + char_to_offset(c1),
            "encoded_fee_sats": BASE_FEE_SATS + char_to_offset(c2),
            "dest_addr": dest_entry[0],
            "change_addr": change_entry[0],
            "change_mnemonic": change_entry[1]
        })

    if invalid_chars:
        print("Invalid Characters")
        print("-" * 60)
        exit()

    encoded_spending_sats = sum(
        tx["amount_sats"] + tx["encoded_fee_sats"]
        for tx in tx_plan
    )

    FINAL_SWEEP_AMOUNT_SATS = 1000
    FINAL_SWEEP_FEE_SATS = BASE_FEE_SATS

    drip_budget_sats = encoded_spending_sats + FINAL_SWEEP_AMOUNT_SATS + FINAL_SWEEP_FEE_SATS

    print(f"Required: {drip_budget_sats / 100_000_000:.8f}")

    if drip_budget_sats >= total_balance_sats:
        print("Error: Wallet balance is insufficient for the calculated drip payload")
        print(f"Available: {total_balance_sats / 100_000_000:.8f}")
        print("-" * 60)
        exit()

    print("-" * 60)

    for idx, tx in enumerate(tx_plan, 1):
        print(f"Amount   : [{tx['c1']}] : {tx['amount_sats']/1e8:.8f}")
        print(f"Fee      : [{tx['c2']}] : {tx['encoded_fee_sats']/1e8:.8f}")
        print(f"Receiver : [{tx['c3']}] : {tx['dest_addr']}")
        print(f"Change   : [{tx['c4']}] : {tx['change_addr']}")
        print("-" * 60)
        
    print(f"Amount   : {FINAL_SWEEP_AMOUNT_SATS / 100_000_000:.8f}")
    print(f"Fee      : {FINAL_SWEEP_FEE_SATS / 100_000_000:.8f}")
    print(f"Receiver : {original_address}")
    print("-" * 60)

    confirm = input("Confirm (Yes/No): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("[ABORTED]")
        print("-" * 60)
        exit()
    print("-" * 60)

    current_priv = main_priv
    current_addr = original_address
    success = 0

    for idx, tx in enumerate(tx_plan, 1):
        chunk = tx["chunk"]
        amount_sats = tx["amount_sats"]
        encoded_fee_sats = tx["encoded_fee_sats"]
        dest_addr = tx["dest_addr"]
        change_addr = tx["change_addr"]
        change_mnemonic = tx["change_mnemonic"]

        print(f"{idx}/{total_tx_count} [{chunk}]")

        try:
            utxos = get_utxo(current_addr)
        except RuntimeError as e:
            print(f"UTXO lookup failed: {e}")
            break

        if not utxos:
            print("No UTXOs available on current address")
            break

        try:
            if idx == 1:
                tx_hex = construct_drip_tx(
                    current_priv,
                    current_addr,
                    dest_addr,
                    change_addr,
                    amount_sats,
                    encoded_fee_sats,
                    utxos,
                    main_change_addr=original_address,
                    total_budget_sats=drip_budget_sats
                )
            else:
                tx_hex = construct_drip_tx(
                    current_priv,
                    current_addr,
                    dest_addr,
                    change_addr,
                    amount_sats,
                    encoded_fee_sats,
                    utxos
                )
        except ValueError as e:
            print(f"Construction failed: {e}")
            break

        result = broadcast_tx(tx_hex)
        if isinstance(result, dict) and ("error" in result or "result" not in result):
            print(f"Broadcast failed: {result}")
            break

        txid = result.get("result") if isinstance(result, dict) else str(result)
        print(f"{txid}")
        
        if wait_for_confirmation(txid):
            success += 1
        else:
            print("Confirmation failed/timed out")
            break
            
        print("-" * 60)

        current_priv = mnemonic_to_private_key(change_mnemonic)
        current_addr = change_addr

    if current_addr != original_address:
        print(f"{total_chunks + 1}/{total_tx_count} [End]")

        try:
            utxos = get_utxo(current_addr)
        except RuntimeError as e:
            print(f"Sweep UTXO lookup failed: {e}")
            utxos = []

        if utxos:
            try:
                tx_hex = construct_sweep_tx(
                    current_priv,
                    current_addr,
                    original_address,
                    utxos,
                    FINAL_SWEEP_FEE_SATS
                )

                result = broadcast_tx(tx_hex)

                if isinstance(result, dict) and "result" in result:
                    sweep_txid = result["result"]
                    print(f"{sweep_txid}")

                    if wait_for_confirmation(sweep_txid):
                        success += 1
                    else:
                        print("Sweep confirmation failed/timed out")
                else:
                    print(f"Sweep broadcast failed: {result}")

            except Exception as e:
                print(f"Sweep failed: {e}")
        else:
            print("No UTXOs found for final sweep")

    print("-" * 60)
    print(f"Success {success}/{total_tx_count}")
    print("-" * 60)