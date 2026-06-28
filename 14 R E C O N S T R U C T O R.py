import requests
import base64
import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://blockbook.flocard.app/api/v2"

def get_flo_data(data):
    if isinstance(data, dict):
        if 'floData' in data: 
            return data['floData']
        for val in data.values():
            res = get_flo_data(val)
            if res: 
                return res
    elif isinstance(data, list):
        for item in data:
            res = get_flo_data(item)
            if res: 
                return res
    return None

def fetch_single_tx(tx, max_retries=5):
    txid = tx['txid']
    height = tx.get('blockHeight', 0)
    
    flo_data = get_flo_data(tx)
    
    if not flo_data:
        for attempt in range(max_retries):
            try:
                tx_resp = requests.get(f"{API_URL}/tx/{txid}", timeout=10)
                if tx_resp.status_code == 200:
                    flo_data = get_flo_data(tx_resp.json())
                    break
                elif tx_resp.status_code == 429:
                    time.sleep(1.5 ** attempt) 
                else:
                    time.sleep(1)
            except Exception:
                time.sleep(1.5 ** attempt)
            
    if flo_data and " | " in flo_data:
        try:
            header, payload = flo_data.split(" | ", 1)
            return int(header), payload, height
        except (ValueError, IndexError):
            pass
            
    return None

def fetch_and_reconstruct(address, start_block, end_block):
    transactions = []
    
    for block in range(start_block, end_block + 1):
        current_page = 1
        total_pages = 1
        block_tx_count = 0
        
        while current_page <= total_pages:
            try:
                url = f"{API_URL}/address/{address}?details=txs&page={current_page}&from={block}&to={block}"
                resp = requests.get(url, timeout=15)
                
                if resp.status_code == 200:
                    data = resp.json()
                    page_txs = data.get('transactions', [])
                    transactions.extend(page_txs)
                    block_tx_count += len(page_txs)
                    
                    total_pages = data.get('totalPages', 1)
                    current_page += 1
                elif resp.status_code == 429:
                    time.sleep(1.5)
                    continue
                else:
                    break
            except Exception as e:
                print(f"Network error on block {block}: {e}")
                break
        
        if block_tx_count > 0:
            print(f"{block}: {block_tx_count}")

    if not transactions:
        print("\nNo transactions found in this block range")
        return

    chunks = {}
    total_found = 0

    print("-" * 44)

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_tx = {executor.submit(fetch_single_tx, tx): tx for tx in transactions}
        
        for future in as_completed(future_to_tx):
            result = future.result()
            if result:
                header, payload, height = result
                chunks[header] = payload
                total_found += 1

    if total_found == 0:
        print("\nNo valid data chunks extracted")
        return
        
    print(f"Found {total_found} transactions")
    print("-" * 44)
    
    if 0 in chunks:
        original_filename = chunks[0].strip()
        filename = f"recovered_{os.path.basename(original_filename)}"
    else:
        filename = f"recovered_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    data_keys = sorted([k for k in chunks.keys() if k > 0])
    if data_keys:
        expected_sequence = set(range(1, max(data_keys) + 1))
        missing_chunks = expected_sequence - set(data_keys)
        if missing_chunks:
            print(f"Missing sequences: {', '.join(f'{m:04d}' for m in sorted(missing_chunks))}")
            print("[WARNING] The reconstruction will likely be corrupted")

    full_b64 = "".join([chunks[i] for i in data_keys])
    
    try:
        with open(filename, "wb") as f:
            f.write(base64.b64decode(full_b64))
        print(f"File saved as: {filename}")
        print("-" * 44)
    except Exception as e:
        print(f"Failed to write file to storage: {e}")
        print("-" * 44)

if __name__ == "__main__":
    print("--- R E C O N S T R U C T O R ---")
    address = input("Address: ").strip()
    range_str = input("Range: ").strip()
    
    print("\n" + "="*44)
    
    try:
        start, end = map(int, range_str.split('-'))
        
        if start > end:
            start, end = end, start
            
        fetch_and_reconstruct(address, start, end)
    except ValueError:
        print("Please enter range in format: startblock-endblock")