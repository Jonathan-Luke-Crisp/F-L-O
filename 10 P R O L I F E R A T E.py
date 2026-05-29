import os
import time
import hashlib
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

def generate_bip39_mnemonic(entropy_bytes, wordlist):
    h = hashlib.sha256(entropy_bytes).digest()
    checksum_bits = bin(h[0])[2:].zfill(8)[:4]
    entropy_bits = ''.join(bin(b)[2:].zfill(8) for b in entropy_bytes)
    total_bits = entropy_bits + checksum_bits
    indices = [int(total_bits[i:i+11], 2) for i in range(0, 132, 11)]
    return " ".join([wordlist[i] for i in indices])

def get_utxo(address):
    try:
        resp = requests.get(f"{API_URL}/utxo/{address}")
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []

def broadcast_tx(final_hex):
    try:
        resp = requests.post(f"{API_URL}/sendtx/", data=final_hex)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Server rejected (Code {resp.status_code}): {resp.text}"}
    except Exception as e:
        return {"error": f"Broadcast failed: {e}"}

def wait_for_confirmation(txid):
    while True:
        try:
            resp = requests.get(f"{API_URL}/tx/{txid}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("confirmations", 0) > 0:
                    break
        except Exception:
            pass
        
        time.sleep(1)

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

if __name__ == "__main__":
    if not os.path.exists("english.txt"):
        print("Missing english.txt")
        exit()
        
    with open("english.txt", "r") as f:
        wordlist = [line.strip() for line in f.readlines()]

    print("--- P R O L I F E R A T E ---")
    height = get_latest_height()
    print(f"Height: {height}")
    print()
    print("=" * 60)
    
    main_mnemonic = input("Key: ").strip()
    print("-" * 60)
    
    main_priv_key = mnemonic_to_private_key(main_mnemonic)
    main_pub_hex = get_public_key(main_priv_key)
    main_address = get_flo_address(bytes.fromhex(main_pub_hex))
    
    utxos = get_utxo(main_address)
    total_balance_sats = sum(int(u['value']) for u in utxos)
    balance_flo = total_balance_sats / 100_000_000
    
    print(f"Address: {main_address}")
    print(f"Balance: {balance_flo:.8f}")
    print("·" * 60)
    
    if total_balance_sats == 0:
        print("Insufficient funds")
        print("-" * 60)
        exit()
    
    try:
        base_amount_flo = float(input("Base:  "))
        batch_count = int(input("Depth: "))
        print("·" * 60)
        
        resume_input = input("Resume: ").strip()
        resume_from = int(resume_input) if resume_input else 0
    except ValueError:
        print("Invalid input")
        exit()
        
    print("·" * 60)
    
    try:
        fee_flo = float(input("Fee: "))
    except ValueError:
        print("Invalid input")
        exit()
        
    fee_sats = int(round(fee_flo * 100_000_000))
    base_amount_sats = int(round(base_amount_flo * 100_000_000))
    
    start_sats = base_amount_sats + resume_from
    end_sats = base_amount_sats + resume_from + batch_count - 1
    
    start_flo = start_sats / 100_000_000
    end_flo = end_sats / 100_000_000
    
    print("-" * 60)
    print(f"{start_flo:.8f} > {end_flo:.8f}")
    print("-" * 60)
    
    confirm = input("Confirm [Yes/No]: ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("-" * 60)
        print("[ABORTED]")
        print("-" * 60)
        exit()
    print("-" * 60)

    success_count = 0
    
    for i in range(batch_count):
        current_index = resume_from + i
        
        amount_sats = base_amount_sats + current_index
        current_amount_flo = amount_sats / 100_000_000
        total_needed = amount_sats + fee_sats
        
        entropy = os.urandom(16)
        new_mnemonic = generate_bip39_mnemonic(entropy, wordlist)
        new_seed = hashlib.pbkdf2_hmac('sha512', new_mnemonic.encode('utf-8'), b'mnemonic', 2048)
        new_priv_bytes = new_seed[:32]
        new_sk = ecdsa.SigningKey.from_string(new_priv_bytes, curve=ecdsa.SECP256k1)
        new_pub_bytes = new_sk.verifying_key.to_string(encoding="compressed")
        drop_address = get_flo_address(new_pub_bytes)
        
        utxos = get_utxo(main_address)
        selected_utxos = []
        collected_sats = 0
        
        for u in utxos:
            selected_utxos.append(u)
            collected_sats += int(u['value'])
            if collected_sats >= total_needed:
                break
                
        if collected_sats < total_needed:
            print("Insufficient funds")
            print("-" * 60)
            exit()
            
        change_sats = collected_sats - total_needed
        
        if 0 < change_sats <= 546:
            change_sats = 0  
            
        flo_data = new_mnemonic
        
        final_hex = construct_tx(main_priv_key, main_address, drop_address, amount_sats, change_sats, flo_data, selected_utxos)
        result = broadcast_tx(final_hex)
        
        if "error" in result:
            print(result["error"])
            break
            
        txid = result.get("result", "Unknown TXID")
        success_count += 1
        
        if i < batch_count - 1:
            wait_for_confirmation(txid)
            
        tx_data = requests.get(f"{API_URL}/tx/{txid}").json()
        block_height = tx_data.get("blockHeight", "Pending")
        block_time = tx_data.get("blockTime", 0)
        
        from datetime import datetime
        formatted_time = datetime.fromtimestamp(block_time).strftime('%I:%M:%S %p %m/%d/%y')
        
        print(f"{block_height} | {formatted_time}")
        print(f"{txid}")
        print("·" * 60)
        print(f"{drop_address}")
        print(f"\n{new_mnemonic}")
        print(f"\n{current_amount_flo:.8f}")
        print("-" * 60)
            
    print(f"Success {success_count}/{batch_count}")
    print("-" * 60)
