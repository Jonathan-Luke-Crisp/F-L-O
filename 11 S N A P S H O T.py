import json
import requests

url = "https://altquick.com/api/v2/orderbook/BTC_FLO"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("--- S N A P S H O T ---")
print("\n" + "="*24)

response = requests.get(url, headers=headers)

if response.status_code == 200:
    orderbook_data = response.json()
    
    filename = "orderbook.json"
    with open(filename, "w") as f:
        json.dump(orderbook_data, f, indent=4)
        
    print("Saved as orderbook.json")
else:
    print(f"Failed. Status code: {response.status_code}")
    print(response.text) 

print("-" * 24)