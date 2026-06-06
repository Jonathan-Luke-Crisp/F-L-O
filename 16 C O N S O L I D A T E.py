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

def construct_consolidate_tx(priv_key_bytes, sender_address, dest_address, amount_sats, selected_utxos):
    sk = ecdsa.SigningKey.from_string(priv_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    y_is_odd = int.from_bytes(vk.to_string()[32:], 'big') % 2
    prefix = b'\x03' if y_is_odd else b'\x02'
    pub_key_hex = (prefix + vk.to_string()[:32]).hex()
    
    sender_script = f"76a914{address_to_pkh(sender_address)}88ac"
    dest_script = f"76a914{address_to_pkh(dest_address)}88ac"
    
    out1 = to_le_hex(amount_sats, 8) + make_varint(len(dest_script)//2) + dest_script
    outputs_hex = make_varint(1) + out1

    locktime = "00000000"
    flo_data_field = "00" 
    version = "02000000"
    sighash_type = "01000000"

    final_inputs_hex = make_varint(len(selected_utxos))
    
    for i in range(len(selected_utxos)):
        inputs_for_sig_hex = make_varint(len(selected_utxos))
        
        for j, utxo in enumerate(selected_utxos):
            txid_rev = bytes.fromhex(utxo['txid'])[::-1].hex()
            vout_hex = to_le_hex(utxo['vout'], 4)
            
            if i == j:
                inputs_for_sig_hex += txid_rev + vout_hex + make_varint(len(sender_script)//2) + sender_script + "ffffffff"
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
                data = resp.json()
                return data.get("result", str(data))
            except ValueError:
                return f"Success, but server returned non-JSON: {resp.text}"
        else:
            return f"Server rejected (Code {resp.status_code}): {resp.text}"
    except Exception as e:
        return f"Broadcast failed: {e}"

if __name__ == "__main__":
    current_height = get_latest_height()
    print("--- C O N S O L I D A T E ---")
    print(f"Height: {current_height}\n")
    print("="*60)
    key_input = input("Key: ").strip()
    print("-"*60)
    
    if " " in key_input:
        private_key = mnemonic_to_private_key(key_input)
    else:
        private_key = wif_to_private_key(key_input)
        
    pub_key_hex = get_public_key(private_key)
    sender_address = get_flo_address(bytes.fromhex(pub_key_hex))
    
    utxos = get_utxo(sender_address)
    total_balance_sats = sum(int(u['value']) for u in utxos)
    balance_flo = total_balance_sats / 100_000_000
    
    print(f"Address:  {sender_address}")
    print(f"Balance:  {balance_flo:.8f}")
    print(f"UTXOs:    {len(utxos)}")
    print("·" * 60)
    
    if len(utxos) <= 1:
        print("Wallet is already consolidated")
        print("-"*60)
        exit()
        
    receiver_address = input("Receiver: ").strip()
    if not receiver_address:
        receiver_address = sender_address
        
    print("·" * 60)
    
    fee_flo = float(input("Fee: "))
    fee_sats = int(fee_flo * 100_000_000)
    
    MAX_INPUTS = 500
    
    batches = [utxos[i:i + MAX_INPUTS] for i in range(0, len(utxos), MAX_INPUTS)]
    valid_batches = [b for b in batches if len(b) > 1]
    num_txs = len(valid_batches)
    
    print("-"*60)
    print(f"{num_txs} Transactions")
    print("-"*60)
    
    if num_txs == 0:
        print("Not enough UTXOs to consolidate")
        print("-"*60)
        exit()
        
    confirm = input("Confirm [Yes/No]: ")
    print("-"*60)
    
    if confirm.strip().lower() in ["yes", "y"]:
        for batch in valid_batches:
            collected_sats = sum(int(u['value']) for u in batch)
            amount_to_send_sats = collected_sats - fee_sats
            
            if amount_to_send_sats > 0:
                final_hex = construct_consolidate_tx(private_key, sender_address, receiver_address, amount_to_send_sats, batch)
                result = broadcast_tx(final_hex)
                print(result)
            else:
                print(f"(Skipped {len(batch)} UTXOs - Value lower than fee)")
                print("-"*60)
                
    else:
        print("[ABORTED]")
        print("-"*60)
