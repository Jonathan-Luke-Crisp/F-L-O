import requests
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib3.util.retry import Retry

BASE_URL = "https://blockbook.flocard.app/api/v2"
session = requests.Session()

retry_strategy = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry_strategy)
session.mount('https://', adapter)

def fetch_block(height):
    try:
        return height, session.get(f"{BASE_URL}/block/{height}", timeout=10).json()
    except:
        return height, None

def main():
    print("--- A C T I V I T Y ---")

    try:
        latest = session.get(f"{BASE_URL}/", timeout=10).json().get("blockbook", {}).get("bestHeight")
    except Exception as e:
        print("Could not connect to the API")
        return
        
    user_input = input(f"Height: ").strip()
    
    if user_input:
        try:
            start_height = int(user_input)
        except ValueError:
            print("Invalid height entered")
            return
    else:
        start_height = latest
        sys.stdout.write(f"\033[1A\rHeight: {start_height}\n")
        sys.stdout.flush()
        
    print("\n" + "="*55)
    
    cutoff = int((datetime.now() - timedelta(hours=999999)).timestamp())
    current = start_height
    scanning = True
    
    BATCH_SIZE = 200
    WORKERS = 20

    while scanning:
        heights_to_check = list(range(current, current - BATCH_SIZE, -1))
        
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = [executor.submit(fetch_block, h) for h in heights_to_check]
            
            for future in futures:
                height, data = future.result()
                
                if not data: 
                    print(f"\rFAILED TO FETCH: {height}\033[K")
                    continue
                
                b_time = data.get("time", 0)
                if b_time < cutoff:
                    scanning = False
                    break
                
                tx_count = data.get("txCount", 0)
                dt = datetime.fromtimestamp(b_time).strftime('%I:%M:%S %p %m/%d/%y')
                
                total_sats = sum(
                    int(vout.get("value", "0")) 
                    for tx in data.get("txs", []) 
                    for vout in tx.get("vout", [])
                )
                amount_flo = total_sats / 100_000_000
                
                val_str = f"{amount_flo:.8f}"
                amount_padded = ("·" * (14 - len(val_str))) + val_str
                
                tx_str = str(tx_count)
                tx_padded = ("·" * (4 - len(tx_str))) + tx_str
                
                line = f"{height} | {tx_padded} | {amount_padded} | {dt}"
                
                if tx_count > 1:
                    print(f"\r{line}\033[K")
                else:
                    print(f"\r{line}\033[K", end="", flush=True)
                    
        current -= BATCH_SIZE

    print(f"\r" + "-" * 55 + "\033[K")

if __name__ == "__main__":
    main()
