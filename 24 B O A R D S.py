import hashlib
import ecdsa

def mnemonic_to_private_key(mnemonic_phrase):
    seed = hashlib.pbkdf2_hmac('sha512', mnemonic_phrase.encode('utf-8'), b'mnemonic', 2048)
    return seed[:32]

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

def get_public_key_compressed(priv_key_bytes):
    sk = ecdsa.SigningKey.from_string(priv_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    pubkey = vk.to_string()
    prefix = b'\x02' if pubkey[-1] % 2 == 0 else b'\x03'
    return prefix + pubkey[:32]

def get_flo_address(pubkey_bytes):
    sha = hashlib.sha256(pubkey_bytes).digest()
    ripemd = hashlib.new('ripemd160')
    ripemd.update(sha)
    hash160 = ripemd.digest()
    payload = b'\x23' + hash160
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58_encode(payload + checksum)

def format_board(board_name, entries, include_mnemonic=True):
    lines = [f"{board_name} = {{"]
    for char, addr, mnemonic in entries:
        if include_mnemonic:
            lines.append(f'    "{char}": ("{addr}", "{mnemonic}"),')
        else:
            lines.append(f'    "{char}": ("{addr}"),')
    lines.append("}")
    return "\n".join(lines)

def generate_boards():
    base64_chars = [chr(c) for c in range(ord('a'), ord('z')+1)] + \
                   [chr(c) for c in range(ord('A'), ord('Z')+1)] + \
                   [str(i) for i in range(10)] + \
                   ['+', '/', '=']
    
    receiver_entries = []
    
    # Test mnemonics were 1a - 2=
    
    for char in base64_chars:
        mnemonic = f"{char} "
        priv_bytes = mnemonic_to_private_key(mnemonic)
        pub_bytes = get_public_key_compressed(priv_bytes)
        addr = get_flo_address(pub_bytes)
        receiver_entries.append((char, addr, mnemonic))

    change_entries = []
    
    for char in base64_chars:
        mnemonic = f" {char}"
        priv_bytes = mnemonic_to_private_key(mnemonic)
        pub_bytes = get_public_key_compressed(priv_bytes)
        addr = get_flo_address(pub_bytes)
        change_entries.append((char, addr, mnemonic))

    drip_output = "\n\n".join([
        format_board("DEST_BOARD", receiver_entries, include_mnemonic=True),
        format_board("CHANGE_BOARD", change_entries, include_mnemonic=True),
    ]) + "\n"

    decoder_output = "\n\n".join([
        format_board("DEST_BOARD", receiver_entries, include_mnemonic=False),
        format_board("CHANGE_BOARD", change_entries, include_mnemonic=False),
    ]) + "\n"

    with open("DRIP Boards.txt", "w", encoding="utf-8") as f:
        f.write(drip_output)

    with open("DECODER Boards.txt", "w", encoding="utf-8") as f:
        f.write(decoder_output)
        
    print("--- B O A R D S ---")
    print("\n" + "=" * 48)
    print("Saved as DRIP Boards.txt and DECODER Boards.txt")

if __name__ == "__main__":
    generate_boards()