import json
import requests

def parse_book(book_data):
    return {float(item[0]): float(item[1]) for item in book_data}

def check_changes(yesterday_book, today_book):
    changes = []
    all_prices = sorted(set(yesterday_book.keys()) | set(today_book.keys()))
    
    for price in all_prices:
        past_vol = yesterday_book.get(price, 0)
        live_vol = today_book.get(price, 0)
        
        diff_flo = round(live_vol - past_vol, 8)
        
        if diff_flo != 0:
            prefix = "/\\" if diff_flo > 0 else "\\/"
            abs_flo = abs(diff_flo)
            
            val_str = f"{abs_flo:.8f}"
            
            padding = "·" * (15 - len(val_str))
            formatted_val = f"{padding}{val_str}"
            
            change_str = f"{prefix}{formatted_val} FLO  @  {price:.8f} BTC"
            changes.append(change_str)
            
    return changes

def main():
    print("--- O R D E R B O O K ---")
    print("\n" + "="*41)

    filename = "orderbook.json"
    try:
        with open(filename, "r") as f:
            saved_data = json.load(f)
    except FileNotFoundError:
        print("Error: Snapshot file not found.")
        return

    yesterday_bids = parse_book(saved_data.get('bids', []))
    yesterday_asks = parse_book(saved_data.get('asks', []))

    url = "https://altquick.com/api/v2/orderbook/BTC_FLO"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        live_response = requests.get(url, headers=headers)
        live_data = live_response.json()
        
        today_bids = parse_book(live_data.get('bids', []))
        today_asks = parse_book(live_data.get('asks', []))

        updates = []
        updates.extend(check_changes(yesterday_bids, today_bids))
        updates.extend(check_changes(yesterday_asks, today_asks))

        if updates:
            for update in updates:
                print(update)
        else:
            print("· · · · · · N O  C H A N G E · · · · · · ")
        
        print("-" * 41)

    except Exception as e:
        print(f"Error fetching live data: {e}")

if __name__ == "__main__":
    main()
