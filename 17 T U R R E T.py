import os
import time
import requests
import hashlib
import ecdsa
import base58
from datetime import datetime

API_URL = "https://blockbook.flocard.app/api/v2"

def get_latest_height():
    try:
        res = requests.get(f"{API_URL}/", timeout=10).json()
        return res.get("blockbook", {}).get("bestHeight", "Unknown")
    except Exception:
        return "Unknown"

def get_balance_and_utxos(address):
    try:
        res = requests.get(f"{API_URL}/utxo/{address}", timeout=10).json()
        balance_sats = sum(int(utxo['value']) for utxo in res)
        return balance_sats / 100_000_000, res
    except Exception:
        return 0.0, []
        
def mnemonic_to_private_key(mnemonic_phrase):
    seed = hashlib.pbkdf2_hmac('sha512', mnemonic_phrase.encode('utf-8'), b'mnemonic', 2048)
    return seed[:32]
    
def wif_to_private_key(wif):
    return base58.b58decode(wif)[1:33]                    

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

def construct_tx(priv_key_bytes, sender_address, dest_address, amount_sats, change_sats, flo_data, selected_utxos):
    pub_key_hex = get_public_key(priv_key_bytes)
    dest_script = f"76a914{address_to_pkh(dest_address)}88ac"
    change_script = f"76a914{address_to_pkh(sender_address)}88ac"

    out1 = to_le_hex(amount_sats, 8) + make_varint(len(dest_script)//2) + dest_script
    if change_sats > 0:
        out2 = to_le_hex(change_sats, 8) + make_varint(len(change_script)//2) + change_script
        outputs_hex = make_varint(2) + out1 + out2
    else:
        outputs_hex = make_varint(1) + out1

    inputs_data = []
    for u in selected_utxos:
        inputs_data.append({
            'txid_rev': bytes.fromhex(u['txid'])[::-1].hex(),
            'vout_hex': to_le_hex(u['vout'], 4)
        })

    version = "02000000"
    locktime = "00000000"
    flo_data_hex = flo_data.encode('utf-8').hex()
    flo_data_field = make_varint(len(flo_data_hex)//2) + flo_data_hex
    sighash_type = "01000000"

    final_inputs = []
    for i in range(len(inputs_data)):
        inputs_for_hashing = make_varint(len(inputs_data))
        for j in range(len(inputs_data)):
            if i == j:
                inputs_for_hashing += inputs_data[j]['txid_rev'] + inputs_data[j]['vout_hex'] + make_varint(len(change_script)//2) + change_script + "ffffffff"
            else:
                inputs_for_hashing += inputs_data[j]['txid_rev'] + inputs_data[j]['vout_hex'] + "00" + "ffffffff"

        raw_tx_to_hash = version + inputs_for_hashing + outputs_hex + locktime + flo_data_field + sighash_type
        hash_to_sign = dsha256(bytes.fromhex(raw_tx_to_hash))

        sig_der = sign_low_s(priv_key_bytes, hash_to_sign)
        sig_with_hashcode = sig_der + bytes([0x01])

        script_sig = make_varint(len(sig_with_hashcode)) + sig_with_hashcode.hex() + make_varint(len(pub_key_hex)//2) + pub_key_hex
        final_input_hex = inputs_data[i]['txid_rev'] + inputs_data[i]['vout_hex'] + make_varint(len(script_sig)//2) + script_sig + "ffffffff"
        final_inputs.append(final_input_hex)

    final_inputs_hex = make_varint(len(final_inputs)) + "".join(final_inputs)
    final_tx = version + final_inputs_hex + outputs_hex + locktime + flo_data_field

    return final_tx

def wait_for_confirmation(txid):
    while True:
        try:
            res = requests.get(f"{API_URL}/tx/{txid}", timeout=10).json()
            if res.get("confirmations", 0) > 0:
                break
        except Exception:
            pass
        time.sleep(10)

def broadcast_tx(raw_hex):
    try:
        res = requests.post(f"{API_URL}/sendtx/", data=raw_hex, timeout=10)
        if res.status_code == 200:
            try:
                return {"result": res.json().get("result", res.text.strip('"'))}
            except:
                return {"result": res.text.strip('"')}
        else:
            return {"error": res.text}
    except Exception as e:
        return {"error": str(e)}

os.system('cls' if os.name == 'nt' else 'clear')
height = get_latest_height()

print("--- T U R R E T ---")
print(f"Height: {height}")
print("\n"+"="*60)

key_input = input("Key: ").strip()
try:
    if len(key_input) in [51, 52]:
        priv_key_bytes = wif_to_private_key(key_input)
    elif len(key_input) == 64:
        priv_key_bytes = bytes.fromhex(key_input)
    else:
        priv_key_bytes = mnemonic_to_private_key(key_input)
        
    pub_key_hex = get_public_key(priv_key_bytes)
    sender_address = get_flo_address(bytes.fromhex(pub_key_hex))
except Exception as e:
    print(f"Key Error: {e}")
    exit()

balance, current_utxos = get_balance_and_utxos(sender_address)

print("-" * 60)
print(f"Address: {sender_address}")
print(f"Balance: {balance:.8f} FLO")
print("·" * 60)

if balance == 0:
    print("Insufficient balance")
    print("-" * 60)
    exit()

receiver = input("Receiver: ").strip()
print("·" * 60)

flo_data_input = input("floData: ").strip()
data_len = len(flo_data_input.encode('utf-8'))
print(f"{data_len}/1040")
print("·" * 60)

if data_len > 1040:
    print("Exceeds character limit")
    print("-" * 60)
    exit()

try:
    depth = int(input("Depth: ").strip())
except ValueError:
    print("Invalid depth")
    exit()
    
print("·" * 60)

try:
    amount_flo = float(input("Amount: ").strip())
    fee_flo = float(input("Fee:    ").strip())
except ValueError:
    print("Invalid amount or fee")
    exit()
    
print("-" * 60)

confirm = input("Confirm [Yes/No]: ").strip()

if confirm.lower() not in ['yes', 'y']:
    print("-"*60)
    print("[ABORTED]")
    print("-"*60)
    exit()

print("-"*60)
print("Firing")
print("-"*60)

amount_sats = int(amount_flo * 100_000_000)
fee_sats = int(fee_flo * 100_000_000)
total_needed = amount_sats + fee_sats

success_count = 0

for i in range(depth):
    current_balance, utxos = get_balance_and_utxos(sender_address)
    
    selected_utxos = []
    collected_sats = 0
    for u in utxos:
        selected_utxos.append(u)
        collected_sats += int(u['value'])
        if collected_sats >= total_needed:
            break
            
    if collected_sats < total_needed:
        print(f"Loop halted at index {i}: Insufficient spendable UTXO inputs")
        break
        
    change_sats = collected_sats - total_needed
    if 0 < change_sats <= 546:
        change_sats = 0
        
    final_hex = construct_tx(
        priv_key_bytes=priv_key_bytes,
        sender_address=sender_address,
        dest_address=receiver,
        amount_sats=amount_sats,
        change_sats=change_sats,
        flo_data=flo_data_input,
        selected_utxos=selected_utxos
    )
    
    result = broadcast_tx(final_hex)
    
    if "error" in result:
        print(f"Network Broadcast Error: {result['error']}")
        break
        
    txid = result.get("result", "Unknown TXID")
    success_count += 1
    
    wait_for_confirmation(txid)
        
    try:
        tx_data = requests.get(f"{API_URL}/tx/{txid}").json()
        block_height = tx_data.get("blockHeight", "Pending")
        block_time = tx_data.get("blockTime")
            
        if block_time is None or block_time == 0:
            block_time = int(time.time())
                
        formatted_time = datetime.fromtimestamp(block_time).strftime('%I:%M:%S %p %m/%d/%y')
        print(f"{success_count}/{depth} | {block_height} | {formatted_time}")
        print(f"{txid}")
    except Exception:
        print(f"Pending | Parsing Error")
    print("-" * 60)

print(f"Success {success_count}/{depth}")
print("-"*60)
