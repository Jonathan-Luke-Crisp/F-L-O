import hashlib
import struct
import requests
import ecdsa
import base58

API_URL = "https://blockbook.flocard.app/api/v2"

def get_latest_height():
    try:
        res = requests.get(f"{API_URL}/", timeout=10).json()
        return res.get("blockbook", {}).get("bestHeight", "Unknown")
    except Exception:
        return "Unknown"

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

def wif_to_private_key(wif):
    return base58.b58decode(wif)[1:33]

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
    hash160 = ripemd.digest()
    payload = b'\x23' + hash160
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

def construct_fan_in_tx(priv_key_bytes, sender_address, dest_address, amount_sats, change_sats, flo_data, selected_utxos):
    sk = ecdsa.SigningKey.from_string(priv_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    y_is_odd = int.from_bytes(vk.to_string()[32:], 'big') % 2
    prefix = b'\x03' if y_is_odd else b'\x02'
    pub_key_hex = (prefix + vk.to_string()[:32]).hex()
    
    dest_script = f"76a914{address_to_pkh(dest_address)}88ac"
    my_script = f"76a914{address_to_pkh(sender_address)}88ac"
    
    out1 = to_le_hex(amount_sats, 8) + make_varint(len(dest_script)//2) + dest_script
    if change_sats > 0:
        out2 = to_le_hex(change_sats, 8) + make_varint(len(my_script)//2) + my_script
        outputs_hex = make_varint(2) + out1 + out2
    else:
        outputs_hex = make_varint(1) + out1

    locktime = "00000000"
    flo_data_hex = flo_data.encode('utf-8').hex()
    flo_data_field = make_varint(len(flo_data_hex)//2) + flo_data_hex
    version = "02000000"
    sighash_type = "01000000"

    final_inputs_hex = make_varint(len(selected_utxos))
    
    for i in range(len(selected_utxos)):
        inputs_for_sig_hex = make_varint(len(selected_utxos))
        
        for j, utxo in enumerate(selected_utxos):
            txid_rev = bytes.fromhex(utxo['txid'])[::-1].hex()
            vout_hex = to_le_hex(utxo['vout'], 4)
            
            if i == j:
                inputs_for_sig_hex += txid_rev + vout_hex + make_varint(len(my_script)//2) + my_script + "ffffffff"
            else:
                inputs_for_sig_hex += txid_rev + vout_hex + "00" + "ffffffff"

        raw_tx_to_hash = version + inputs_for_sig_hex + outputs_hex + locktime + flo_data_field + sighash_type
        hash_to_sign = dsha256(bytes.fromhex(raw_tx_to_hash))
        
        sig_der = sk.sign_digest(hash_to_sign, sigencode=ecdsa.util.sigencode_der_canonize)
        sig_with_hashcode = sig_der + bytes([0x01]) 
        
        script_sig = make_varint(len(sig_with_hashcode)) + sig_with_hashcode.hex() + make_varint(len(pub_key_hex)//2) + pub_key_hex
        
        txid_rev = bytes.fromhex(selected_utxos[i]['txid'])[::-1].hex()
        vout_hex = to_le_hex(selected_utxos[i]['vout'], 4)
        final_inputs_hex += txid_rev + vout_hex + make_varint(len(script_sig)//2) + script_sig + "ffffffff"

    final_tx = version + final_inputs_hex + outputs_hex + locktime + flo_data_field
    return final_tx

def get_utxo(address):
    try:
        resp = requests.get(f"{API_URL}/utxo/{address}")
        return resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Network error: {e}")
        return []

def broadcast_tx(final_hex):
    try:
        resp = requests.post(f"{API_URL}/sendtx/", data=final_hex)
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                return {"result": f"Success, but server returned non-JSON: {resp.text}"}
        else:
            return {"result": f"Server rejected (Code {resp.status_code}): {resp.text}"}
    except Exception as e:
        return {"result": f"Broadcast failed: {e}"}

if __name__ == "__main__":
    current_height = get_latest_height()
    print("--- B R O A D C A S T E R  Mk.II ---")
    print(f"Height: {current_height}\n")
    print("="*60)
    key_input = input("Key: ").strip()
    
    if " " in key_input:
        private_key = mnemonic_to_private_key(key_input)
    else:
        private_key = wif_to_private_key(key_input)
        
    pub_key_hex = get_public_key(private_key)
    sender_address = get_flo_address(bytes.fromhex(pub_key_hex))
    
    utxos = get_utxo(sender_address)
    total_balance_sats = sum(int(u['value']) for u in utxos)
    balance_flo = total_balance_sats / 100_000_000
    
    print("-"*60)
    print(f"Address: {sender_address}")
    print(f"Balance: {balance_flo:.8f}")
    print("·"*60)
    
    if not utxos:
        print("Insufficient funds")
        print("-"*60)
        exit()
        
    dest_address = input("Receiver: ")
    print("·"*60)
    flo_data = input("floData: ")
    
    data_length = len(flo_data.encode('utf-8'))
    print(f"{data_length}/1040")
    
    if data_length > 1040:
        print("-"*60)
        print("Exceeds character limit")
        print("-"*60)
        exit()
        
    print("·"*60)
    amount_flo = float(input("Amount: "))
    fee_flo = float(input("Fee:    "))
    
    amount_sats = int(amount_flo * 100_000_000)
    fee_sats = int(fee_flo * 100_000_000)
    total_needed = amount_sats + fee_sats
        
    selected_utxos = []
    collected_sats = 0
    MAX_INPUTS = 200
    
    for u in utxos:
        selected_utxos.append(u)
        collected_sats += int(u['value'])
        
        if collected_sats >= total_needed or len(selected_utxos) >= MAX_INPUTS:
            break
            
    if len(selected_utxos) == MAX_INPUTS and collected_sats < total_needed:
        amount_sats = collected_sats - fee_sats
        total_needed = collected_sats
        print("-"*60)
        print(f"LIMIT: {amount_sats / 100_000_000:.8f}")
    
    if collected_sats < total_needed:
        print(f"Insufficient funds. Found {collected_sats / 100_000_000:.8f} FLO. You need {total_needed / 100_000_000:.8f} FLO")
        exit()
        
    change_sats = collected_sats - total_needed
    
    final_hex = construct_fan_in_tx(private_key, sender_address, dest_address, amount_sats, change_sats, flo_data, selected_utxos)
    
    print("-" * 60)
    print(f"{final_hex}")
    print("-" * 60)
    
    confirm = input("Confirm [Yes/No]: ")
    print("-" * 60)
    
    if confirm.strip().lower() in ["yes", "y"]:
        result = broadcast_tx(final_hex)
        if isinstance(result, dict):
            print(result.get("result", result))
        else:
            print(result)
    else:
        print("[ABORTED]")
    print("-" * 60)
