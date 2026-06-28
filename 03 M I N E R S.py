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
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry_strategy)
session.mount('https://', adapter)

def fetch_block(height):
    try:
        return height, session.get(f"{BASE_URL}/block/{height}", timeout=10).json()
    except:
        return height, None

def main():
    print("--- M I N E R S ---")

    try:
        latest = session.get(f"{BASE_URL}/", timeout=10).json().get("blockbook", {}).get("bestHeight")
    except Exception as e:
        print("Could not connect to the API.")
        return
        
    user_input = input(f"Height: ").strip()
    
    if user_input:
        try:
            start_height = int(user_input)
        except ValueError:
            print("Invalid height entered. Please enter numbers only. Exiting.")
            return
    else:
        start_height = latest
        sys.stdout.write(f"\033[1A\rHeight: {start_height}\n")
        sys.stdout.flush()
        
    print("\n" + "=" * 45)
    
    cutoff = int((datetime.now() - timedelta(hours=999999)).timestamp())
    current = start_height
    scanning = True
    
    BATCH_SIZE = 200
    WORKERS = 20

    while scanning:
        heights_to_check = list(range(current, current - BATCH_SIZE, -1))
        
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            future_to_height = {executor.submit(fetch_block, h): h for h in heights_to_check}
            
            for height in heights_to_check:
                data = next((f.result()[1] for f in future_to_height if future_to_height[f] == height), None)
                
                if not data:
                    print(f"FAILED TO FETCH: {height}")
                    continue

                b_time = data.get("time", 0)
                if b_time < cutoff:
                    scanning = False
                    break
                
                txs = data.get("txs", [])
                if not txs:
                    continue
                    
                coinbase_tx = txs[0]
                
                vin = coinbase_tx.get("vin", [])
                if not vin or not vin[0].get("coinbase"):
                    continue
                    
                miner_address = "Unknown Address"
                vout = coinbase_tx.get("vout", [])
                
                for out in vout:
                    if int(out.get("value", 0)) > 0:
                        addresses = out.get("addresses", [])
                        if addresses:
                            miner_address = addresses[0]
                            break
                        
                print(f"{height} | {miner_address}")
                    
        current -= BATCH_SIZE

if __name__ == "__main__":
    main()