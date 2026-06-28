import hashlib
import binascii
import ecdsa
import os

def base58_encode(data):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = int.from_bytes(data, 'big')
    res = ''
    while n > 0:
        n, remainder = divmod(n, 58)
        res = alphabet[remainder] + res
    return res

def get_wif(raw_priv_key):
    payload = b'\xA3' + raw_priv_key + b'\x01'
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58_encode(payload + checksum)

def get_flo_address(pubkey_bytes):
    sha = hashlib.sha256(pubkey_bytes).digest()
    ripemd = hashlib.new('ripemd160')
    ripemd.update(sha)
    hash160 = ripemd.digest()
    payload = b'\x23' + hash160
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58_encode(payload + checksum)

def generate_bip39_mnemonic(entropy_bytes):
    h = hashlib.sha256(entropy_bytes).digest()
    checksum_bits = bin(h[0])[2:].zfill(8)[:4]
    entropy_bits = ''.join(bin(b)[2:].zfill(8) for b in entropy_bytes)
    total_bits = entropy_bits + checksum_bits
    indices = [int(total_bits[i:i+11], 2) for i in range(0, 132, 11)]
    
    with open("english.txt", "r") as f:
        wordlist = [line.strip() for line in f.readlines()]
    return " ".join([wordlist[i] for i in indices])

def run_generator():
    print("--- G E N E R A T O R ---")
    filename = input("Filename: ").strip()
    salt = input("Salt: ").strip()
    
    if not os.path.exists("english.txt"):
        print("Missing english.txt")
        return

    if filename == "":
        entropy = os.urandom(16)
    else:
        if not os.path.exists(filename):
            print("File not found")
            return

        with open(filename, "rb") as f:
            img_bytes = f.read()

        dynamic_salt = hashlib.scrypt(
            password=salt.encode(), 
            salt=img_bytes, 
            n=16384, r=8, p=1, dklen=128
        )

        entropy = hashlib.scrypt(
            password=img_bytes, 
            salt=dynamic_salt, 
            n=16384, r=8, p=1, dklen=16
        )

    mnemonic = generate_bip39_mnemonic(entropy)

    seed = hashlib.pbkdf2_hmac('sha512', mnemonic.encode('utf-8'), b'mnemonic', 2048)
    priv_bytes = seed[:32]

    wif = get_wif(priv_bytes)
    sk = ecdsa.SigningKey.from_string(priv_bytes, curve=ecdsa.SECP256k1)
    pub_bytes = sk.verifying_key.to_string(encoding="compressed")
    address = get_flo_address(pub_bytes)
    
    print("\n" + "=" * 60)
    print(f"Mnemonic:\n{mnemonic}")
    print(f"\nAddress:\n{address}")
    print(f"\nPrivate Key:\n{wif}")
    print(f"\nPublic Key:\n{binascii.hexlify(pub_bytes).decode('utf-8')}")
    print("\n" + "-" * 60)

if __name__ == "__main__":
    run_generator()
