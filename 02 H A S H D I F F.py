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

def format_hashrate(hashes_per_second):
    if hashes_per_second == 0:
        return "··0.00 H/s"
    
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s"]
    i = 0
    while hashes_per_second >= 1000 and i < len(units) - 1:
        hashes_per_second /= 1000.0
        i += 1
        
    val_str = f"{hashes_per_second:.2f}"
    val_padded = ("·" * (6 - len(val_str))) + val_str
    
    return f"{val_padded} {units[i]}"

def format_difficulty(diff):
    if diff == 0:
        val_str = "0.00"
    elif diff >= 999995:
        val_str = f"{diff/1000000:.1f}M"
    elif diff >= 999.995:
        val_str = f"{diff/1000:.1f}K"
    elif diff >= 1:
        val_str = f"{diff:.2f}"
    else:
        val_str = f"{diff:.4f}"
        
    val_padded = ("·" * (6 - len(val_str))) + val_str
    return val_padded

def fetch_block(height):
    try:
        return height, session.get(f"{BASE_URL}/block/{height}", timeout=10).json()
    except:
        return height, None

def main():
    print("--- H A S H / D I F F ---")

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
        
    print("\n" + "="*54)
    
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
                    print(f"FAILED TO FETCH: {height}")
                    continue
                
                b_time = data.get("time", 0)
                if b_time < cutoff:
                    scanning = False
                    break
                
                difficulty = float(data.get("difficulty", 0))
                hashrate_raw = (difficulty * (2**32)) / 40
                
                readable_hashrate = format_hashrate(hashrate_raw)
                diff_padded = format_difficulty(difficulty)
                
                dt = datetime.fromtimestamp(b_time).strftime('%I:%M:%S %p %m/%d/%y')

                print(f"{height} | {readable_hashrate} | {diff_padded} | {dt}")
                    
        current -= BATCH_SIZE

    print("-" * 54)

if __name__ == "__main__":
    main()
