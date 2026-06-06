import hashlib
import struct
import requests
import ecdsa
import base58
import base64
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def prepare_file_chunks(file_path, max_payload_size=1033):
    if not os.path.exists(file_path):
        print(f"Could not find '{file_path}'")
        print("-" * 60)
        exit()
        
    filename = os.path.basename(file_path)
    chunks = [f"0000 | {filename}"]
        
    with open(file_path, "rb") as file:
        raw_binary = file.read()
        
    b64_string = base64.b64encode(raw_binary).decode('utf-8')
    char_pointer = 0
    index = 1
    total_chars = len(b64_string)
    
    while char_pointer < total_chars:
        prefix = f"{index:04d} | "
        chunk_payload = b64_string[char_pointer:char_pointer + max_payload_size]
        chunks.append(prefix + chunk_payload)
        index += 1
        char_pointer += max_payload_size
        
    return chunks

def construct_tx(priv_key_bytes, sender_address, dest_address, amount_sats, change_sats, flo_data, utxo):
    pub_key_hex = get_public_key(priv_key_bytes)
    dest_script = f"76a914{address_to_pkh(dest_address)}88ac"
    change_script = f"76a914{address_to_pkh(sender_address)}88ac"
    
    out1 = to_le_hex(amount_sats, 8) + make_varint(len(dest_script)//2) + dest_script
    
    if change_sats > 0:
        out2 = to_le_hex(change_sats, 8) + make_varint(len(change_script)//2) + change_script
        outputs_hex = make_varint(2) + out1 + out2
    else:
        outputs_hex = make_varint(1) + out1
    
    txid_rev = bytes.fromhex(utxo['txid'])[::-1].hex()
    vout_hex = to_le_hex(utxo['vout'], 4)
    
    input_for_sig = txid_rev + vout_hex + make_varint(len(change_script)//2) + change_script + "ffffffff"
    inputs_hex_sig = make_varint(1) + input_for_sig
    
    locktime = "00000000"
    flo_data_hex = flo_data.encode('utf-8').hex()
    flo_data_field = make_varint(len(flo_data_hex)//2) + flo_data_hex
    
    version = "02000000"
    sighash_type = "01000000"
    raw_tx_to_hash = version + inputs_hex_sig + outputs_hex + locktime + flo_data_field + sighash_type
    hash_to_sign = dsha256(bytes.fromhex(raw_tx_to_hash))
    
    sig_der = sign_low_s(priv_key_bytes, hash_to_sign)
    sig_with_hashcode = sig_der + bytes([0x01]) 
    
    script_sig = make_varint(len(sig_with_hashcode)) + sig_with_hashcode.hex() + make_varint(len(pub_key_hex)//2) + pub_key_hex
    final_input = txid_rev + vout_hex + make_varint(len(script_sig)//2) + script_sig + "ffffffff"
    final_inputs_hex = make_varint(1) + final_input
    
    final_tx = version + final_inputs_hex + outputs_hex + locktime + flo_data_field
    return final_tx

def construct_fanout_tx(priv_key_bytes, sender_address, total_outputs, funding_per_utxo, fee_sats, utxo):
    pub_key_hex = get_public_key(priv_key_bytes)
    my_script = f"76a914{address_to_pkh(sender_address)}88ac"
    
    utxo_val = int(utxo['value'])
    total_allocated = total_outputs * funding_per_utxo
    change_sats = utxo_val - total_allocated - fee_sats
    
    if change_sats < 0:
        print(f"Insufficient balance")
        exit()
        
    outputs_hex = ""
    for _ in range(total_outputs):
        outputs_hex += to_le_hex(funding_per_utxo, 8) + make_varint(len(my_script)//2) + my_script
        
    if change_sats > 0:
        outputs_hex += to_le_hex(change_sats, 8) + make_varint(len(my_script)//2) + my_script
        total_output_count = total_outputs + 1
    else:
        total_output_count = total_outputs
        
    final_outputs_field = make_varint(total_output_count) + outputs_hex
    
    txid_rev = bytes.fromhex(utxo['txid'])[::-1].hex()
    vout_hex = to_le_hex(utxo['vout'], 4)
    
    input_for_sig = txid_rev + vout_hex + make_varint(len(my_script)//2) + my_script + "ffffffff"
    inputs_hex_sig = make_varint(1) + input_for_sig
    
    locktime = "00000000"
    flo_data_field = "00" 
    version = "02000000"
    sighash_type = "01000000"
    
    raw_tx_to_hash = version + inputs_hex_sig + final_outputs_field + locktime + flo_data_field + sighash_type
    hash_to_sign = dsha256(bytes.fromhex(raw_tx_to_hash))
    
    sig_der = sign_low_s(priv_key_bytes, hash_to_sign)
    sig_with_hashcode = sig_der + bytes([0x01]) 
    
    script_sig = make_varint(len(sig_with_hashcode)) + sig_with_hashcode.hex() + make_varint(len(pub_key_hex)//2) + pub_key_hex
    final_input = txid_rev + vout_hex + make_varint(len(script_sig)//2) + script_sig + "ffffffff"
    
    final_tx = version + make_varint(1) + final_input + final_outputs_field + locktime + flo_data_field
    return final_tx

def get_utxo(address, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(f"{API_URL}/utxo/{address}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"Network error: {e}")
                return []
        time.sleep(2)
    return []

def broadcast_tx(final_hex, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.post(f"{API_URL}/sendtx/", data=final_hex, timeout=10)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    return {"result": f"Success, but server returned non-JSON: {resp.text}"}
            else:
                return {"result": f"Server error {resp.status_code}: {resp.text}"}
        except Exception as e:
            if attempt == retries - 1:
                return {"result": f"Error: {e}"}
        time.sleep(2)
    return {"result": "Unknown error after retries"}

def broadcast_worker(actual_index, tx_hex):
    result = broadcast_tx(tx_hex)
    result_str = result.get('result', str(result)) if isinstance(result, dict) else str(result)
    return actual_index, result_str

if __name__ == "__main__":
    current_height = get_latest_height()
    print("--- F L O O D  Mk.II ---")
    print(f"Height: {current_height}\n")
    print("="*60)
    
    key_input = input("Key: ").strip()
    print("-" * 60)
    
    if " " in key_input:
        private_key = mnemonic_to_private_key(key_input)
    else:
        private_key = wif_to_private_key(key_input)
        
    pub_key_hex = get_public_key(private_key)
    sender_address = get_flo_address(bytes.fromhex(pub_key_hex))
    
    utxos = get_utxo(sender_address)
    total_balance_sats = sum(int(u['value']) for u in utxos)
    balance_flo = total_balance_sats / 100_000_000
    
    print(f"Address: {sender_address}")
    print(f"Balance: {balance_flo:.8f}")
    print("·" * 60)
    
    if not utxos or total_balance_sats == 0:
        print("Insufficient funds")
        print("-" * 60)
        exit()
    
    dest_address = input("Receiver: ")
    print("·" * 60)
    
    file_path = input("Filename: ")
    
    if not os.path.exists(file_path):
        print(f"Could not find '{file_path}'")
        print("-" * 60)
        exit()
        
    file_size_bytes = os.path.getsize(file_path)
    print(f"{file_size_bytes} Bytes")
    print("·" * 60)
    
    amount_flo = float(input("Amount: "))
    fee_flo = float(input("Fee:    "))
    print("·" * 60)
    
    missing_str = input("Missing: ")
    print("-" * 60)
    
    amount_sats = int(amount_flo * 100_000_000)
    fee_sats = int(fee_flo * 100_000_000)
    
    with open(file_path, "rb") as file:
        b64_length = len(base64.b64encode(file.read()).decode('utf-8'))
    print(f"{b64_length} Characters")
    
    all_chunks = prepare_file_chunks(file_path)
    
    if missing_str.strip():
        target_indices = [int(x.strip()) for x in missing_str.split(',') if x.strip().isdigit()]
    else:
        target_indices = list(range(len(all_chunks)))
        
    target_indices = [idx for idx in target_indices if idx < len(all_chunks)]
    
    if not target_indices:
        print("No valid chunks selected")
        exit()
        
    chunks_to_process = [(idx, all_chunks[idx]) for idx in target_indices]
    total_chunks = len(chunks_to_process)
    
    if missing_str.strip():
        print(f"Targeting {total_chunks} specific missing transactions")
    else:
        print(f"{total_chunks} Transactions required")
        
    print(f"{len(utxos)} UTXOs found")
    print("-" * 60)
    
    funding_per_chunk = amount_sats + fee_sats

    valid_utxos = [u for u in utxos if int(u['value']) >= funding_per_chunk]

    if len(valid_utxos) < total_chunks:
        needed_utxos = total_chunks - len(valid_utxos)
        
        print("Splitting")
        print("-" * 60)
        
        MAX_OUTPUTS_PER_BATCH = 2000
        
        if needed_utxos > MAX_OUTPUTS_PER_BATCH:
            
            outputs_to_generate = MAX_OUTPUTS_PER_BATCH
        else:
            outputs_to_generate = needed_utxos
        
        split_amount_flo = float(input("Amount: "))
        split_fee_flo = float(input("Fee:    "))
        
        split_amount_sats = int(split_amount_flo * 100_000_000)
        split_fee_sats = int(split_fee_flo * 100_000_000)
        
        total_split_cost_sats = (outputs_to_generate * split_amount_sats) + split_fee_sats
        
        print("·" * 60)
        
        largest_utxo = max(utxos, key=lambda x: int(x['value']))
        
        if int(largest_utxo['value']) < total_split_cost_sats:
            print(f"Insufficient funds for split. Largest UTXO has {int(largest_utxo['value'])/100_000_000:.8f} FLO.")
            print(f"You need {total_split_cost_sats / 100_000_000:.8f} FLO in a single UTXO.")
            exit()
            
        fanout_hex = construct_fanout_tx(private_key, sender_address, outputs_to_generate, split_amount_sats, split_fee_sats, largest_utxo)
        
        confirm = input("Confirm [Yes/No]: ")
        print("-" * 60)
        
        if confirm.strip().lower() in ["yes", "y"]:
            result = broadcast_tx(fanout_hex)
            if isinstance(result, dict):
                print(result.get("result", result))
            else:
                print(result)
                
            print("-" * 60)
            exit()
            
        else:
            print("[ABORTED]")
            print("-" * 60)
            exit()
            
    else:
        confirm = input("Confirm [Yes/No]: ")
        print("-" * 60)
        
        if confirm.strip().lower() in ["yes", "y"]:
            success_count = 0
            failed_chunks = []
            
            print("Constructing transactions...")
            print("-" * 60)
            tx_payloads = []
            
            for offset, (actual_index, chunk_data) in enumerate(chunks_to_process):
                utxo = valid_utxos[offset]
                utxo_val = int(utxo['value'])
                change_sats = utxo_val - amount_sats - fee_sats
                
                tx_hex = construct_tx(private_key, sender_address, dest_address, amount_sats, change_sats, chunk_data, utxo)
                tx_payloads.append((actual_index, tx_hex))
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_tx = {executor.submit(broadcast_worker, idx, hex_data): idx for idx, hex_data in tx_payloads}
                
                for future in as_completed(future_to_tx):
                    actual_index = future_to_tx[future]
                    try:
                        res_idx, result_str = future.result()
                        if len(result_str) == 64 and " " not in result_str:
                            print(f"{res_idx:04d}: {result_str}")
                            success_count += 1
                        else:
                            print(f"[NETWORK ERROR] {res_idx:04d} failed: {result_str}")
                            failed_chunks.append(res_idx)
                    except Exception as e:
                        print(f"[ERROR] {actual_index:04d} failed: {e}")
                        failed_chunks.append(actual_index)
                
            print("-" * 60)
            print(f"Success {success_count}/{total_chunks}")
            if failed_chunks:
                print(f"Failed chunks: {sorted(failed_chunks)}")
            print("-" * 60)
        else:
            print("[ABORTED]")
            print("-" * 60)
