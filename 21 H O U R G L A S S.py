import json
import os

def triangle(num_orders):
    return sum(range(1, int(num_orders) + 1))

def build_sell_orders(baseline_price, num_orders, increment, total_asset):
    divisor = triangle(num_orders)
    sell_unit = total_asset / divisor if divisor > 0 else 0
    orders = []
    for i in range(1, int(num_orders) + 1):
        price = baseline_price * (1 + (i * increment / 100))
        asset_allocated = sell_unit * i
        orders.append({
            "rung": i * increment,
            "price": price,
            "asset_allocated": asset_allocated,
            "filled": False
        })
    return orders

def build_buy_orders(baseline_price, num_orders, increment, total_fiat):
    divisor = triangle(num_orders)
    buy_unit = total_fiat / divisor if divisor > 0 else 0
    orders = []
    for i in range(1, int(num_orders) + 1):
        price = baseline_price * (1 - (i * increment / 100))
        fiat_allocated = buy_unit * i
        orders.append({
            "rung": i * increment,
            "price": price,
            "fiat_allocated": fiat_allocated,
            "filled": False
        })
    return orders

def process_price_update(state, new_price):
    buys_filled = 0
    sells_filled = 0
    
    for buy in state["buy_orders"]:
        if not buy["filled"] and new_price <= buy["price"]:
            buy["filled"] = True
            state["total_fiat"] -= buy["fiat_allocated"]
            state["total_asset"] += (buy["fiat_allocated"] / buy["price"])
            buys_filled += 1
            
    for sell in state["sell_orders"]:
        if not sell["filled"] and new_price >= sell["price"]:
            sell["filled"] = True
            state["total_asset"] -= sell["asset_allocated"]
            state["total_fiat"] += (sell["asset_allocated"] * sell["price"])
            sells_filled += 1
            
    reset_side = None
    
    if buys_filled > 0 and sells_filled == 0:
        reset_side = "sell"
        state["sell_orders"] = build_sell_orders(
            new_price, 
            state["sell_settings"]["orders"], 
            state["sell_settings"]["increment"], 
            state["total_asset"]
        )
        state["baseline_price"] = new_price
        
    elif sells_filled > 0 and buys_filled == 0:
        reset_side = "buy"
        state["buy_orders"] = build_buy_orders(
            new_price, 
            state["buy_settings"]["orders"], 
            state["buy_settings"]["increment"], 
            state["total_fiat"]
        )
        state["baseline_price"] = new_price
        
    elif buys_filled > 0 and sells_filled > 0:
        reset_side = "both"
        state["sell_orders"] = build_sell_orders(new_price, state["sell_settings"]["orders"], state["sell_settings"]["increment"], state["total_asset"])
        state["buy_orders"] = build_buy_orders(new_price, state["buy_settings"]["orders"], state["buy_settings"]["increment"], state["total_fiat"])
        state["baseline_price"] = new_price

    return state, reset_side

def print_dashboard(state, current_price, reset_side=None):
    asset = state["asset"]
    filename = f"{asset}.json"
    
    net_worth = state["total_fiat"] + (state["total_asset"] * current_price)
    
    print(f"Price: ${current_price:,.2f}")
    print("-"*60)
    
    sell_header = "▼ [RESET]" if reset_side in ["sell", "both"] else "▼"
    print(sell_header)
    print("·"*60)
    
    for sell in reversed(state["sell_orders"]):
        status = "[X]" if sell["filled"] else "[O]"
        usd_value = sell["asset_allocated"] * sell["price"]
        
        rung_str = f"+{sell['rung']}%"
        rung_padded = (" " * max(0, 6 - len(rung_str))) + rung_str
        
        price_str = f"${sell['price']:,.2f}"
        price_padded = (" " * max(0, 11 - len(price_str))) + price_str
        
        asset_str = f"{sell['asset_allocated']:.8f} {asset}"
        asset_padded = (" " * max(0, 18 - len(asset_str))) + asset_str
        
        fiat_str = f"${usd_value:,.2f}"
        fiat_padded = (" " * max(0, 11 - len(fiat_str))) + fiat_str
        
        print(f"{status} {rung_padded} / {price_padded} | {asset_padded} / {fiat_padded}")
        
    print("-"*60)
    
    buy_header = "▲ [RESET]" if reset_side in ["buy", "both"] else "▲"
    print(buy_header)
    print("·"*60)
    
    for buy in state["buy_orders"]:
        status = "[X]" if buy["filled"] else "[O]"
        asset_amount = buy["fiat_allocated"] / buy["price"]
        
        rung_str = f"-{buy['rung']}%"
        rung_padded = (" " * max(0, 6 - len(rung_str))) + rung_str
        
        price_str = f"${buy['price']:,.2f}"
        price_padded = (" " * max(0, 11 - len(price_str))) + price_str
        
        asset_str = f"{asset_amount:.8f} {asset}"
        asset_padded = (" " * max(0, 18 - len(asset_str))) + asset_str
        
        fiat_str = f"${buy['fiat_allocated']:,.2f}"
        fiat_padded = (" " * max(0, 11 - len(fiat_str))) + fiat_str
        
        print(f"{status} {rung_padded} / {price_padded} | {fiat_padded} / {asset_padded}")
        
    print("-"*60)
    print("Totals")
    print("-"*60)
    print(f"${state['total_fiat']:,.2f}")
    print(f"{state['total_asset']:.8f} {asset}")
    print("·"*60)
    print(f"Net: ${net_worth:,.2f}")
    print("-"*60)
    print(f"Saved as {filename}")
    print("-"*60)

def interactive_loop():
    print("="*60)
    asset = input("Asset: ").upper().strip()
    filename = f"{asset}.json"
    
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            state = json.load(f)
        current_price = state["baseline_price"]
        print_dashboard(state, current_price)
    else:
        current_price = float(input("Price: "))
        print("-"*60)
        print("▼")
        print("·"*60)
        
        sell_amount_input = float(input("Amount: "))
        sell_amount_asset = sell_amount_input / current_price
        
        sell_orders = int(input("Orders: "))
        sell_increment = float(input("Increment: "))
        
        print("-"*60)
        print("▲")
        print("·"*60)
        buy_amount = float(input("Amount: "))
        buy_orders = int(input("Orders: "))
        buy_increment = float(input("Increment: "))
        print("="*60)
        
        state = {
            "asset": asset,
            "baseline_price": current_price,
            "total_fiat": buy_amount,
            "total_asset": sell_amount_asset,
            "sell_settings": {"orders": sell_orders, "increment": sell_increment},
            "buy_settings": {"orders": buy_orders, "increment": buy_increment},
        }
        
        state["sell_orders"] = build_sell_orders(current_price, sell_orders, sell_increment, sell_amount_asset)
        state["buy_orders"] = build_buy_orders(current_price, buy_orders, buy_increment, buy_amount)
        
        with open(filename, 'w') as f:
            json.dump(state, f, indent=4)
            
        print_dashboard(state, current_price)

    while True:
        try:
            user_input = input("Update Price: ").strip()
            print("="*60)
            if user_input.lower() in ['q', 'quit', 'exit']:
                break
                
            new_price = float(user_input)
            state, reset_side = process_price_update(state, new_price)
            
            with open(filename, 'w') as f:
                json.dump(state, f, indent=4)
                
            print_dashboard(state, new_price, reset_side)
            
        except ValueError:
            print("Invalid input")
            print("-"*60)

if __name__ == "__main__":
    print("--- H O U R G L A S S ---\n")
    interactive_loop()