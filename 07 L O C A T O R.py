import hashlib
import ecdsa
import base58
import os

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

if __name__ == "__main__":
    while True:
        print("--- L O C A T O R ---")
        mnemonic = input("Mnemonic: ").strip()
        
        if not mnemonic:
            break
            
        print("\n" + "=" * 60)
        
        try:
            private_key = mnemonic_to_private_key(mnemonic)
            pub_key_hex = get_public_key(private_key)
            flo_address = get_flo_address(bytes.fromhex(pub_key_hex))
            
            filename = f"{mnemonic}.txt"
            file_content = f"{mnemonic}\n{flo_address}\n"
            
            with open(filename, "w") as f:
                f.write(file_content)
                
            print(f"{flo_address}")
            print(f"Saved as {filename}")
            
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            
        print("-" * 60 + "\n")