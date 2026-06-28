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
    print("--- F L O D A T A ---")

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
        
    print("\n" + "="*60)
    
    cutoff = int((datetime.now() - timedelta(hours=999999)).timestamp())
    current = start_height
    scanning = True
    
    BATCH_SIZE = 50
    WORKERS = 10

    while scanning:
        heights_to_check = list(range(current, current - BATCH_SIZE, -1))
        
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            future_to_height = {executor.submit(fetch_block, h): h for h in heights_to_check}
            
            for height in heights_to_check:
                data = next((f.result()[1] for f in future_to_height if future_to_height[f] == height), None)
                
                if not data:
                    continue

                b_time = data.get("time", 0)
                if b_time < cutoff:
                    scanning = False
                    break
                
                dt = datetime.fromtimestamp(b_time).strftime('%I:%M:%S %p %m/%d/%y')
                
                flo_entries = []
                txs = data.get("txs", [])
                for tx in txs:
                    vin = tx.get("vin", [])
                    if vin and vin[0].get("coinbase"):
                        continue
                    
                    flo_data = tx.get("coinSpecificData", {}).get("floData") or tx.get("floData")
                    if flo_data:
                        flo_entries.append(flo_data.strip())
                
                if flo_entries:
                    sys.stdout.write(f"\r\033[K") 
                    
                    print(f"{height} | {dt}\n")
                    for entry in flo_entries:
                        print(f"{entry}\n")
                    print("-" * 60)
                else:
                    sys.stdout.write(f"\r\033[K{height} | {dt}")
                    sys.stdout.flush()
                    
        current -= BATCH_SIZE

if __name__ == "__main__":
    main()
