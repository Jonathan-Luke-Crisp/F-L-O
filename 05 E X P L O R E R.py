import requests
from datetime import datetime
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

def get_latest_height():
    try:
        res = session.get(f"{BASE_URL}/", timeout=10).json()
        return res.get("blockbook", {}).get("bestHeight", "Unknown")
    except Exception:
        return "Unknown"

def format_time(timestamp):
    if not timestamp:
        return "Unconfirmed"
    return datetime.fromtimestamp(timestamp).strftime('%I:%M:%S %p %m/%d/%y')

def search_tx(query):
    try:
        res = session.get(f"{BASE_URL}/tx/{query}", timeout=10).json()
        if "error" in res:
            return False
            
        val_in = int(res.get("valueIn", 0)) / 100_000_000
        val_out = int(res.get("value", 0)) / 100_000_000
        fees = int(res.get("fees", 0)) / 100_000_000
        
        from_addresses = []
        for vin in res.get("vin", []):
            if vin.get("coinbase"):
                from_addresses.append("Coinbase")
            else:
                addrs = vin.get("addresses", [])
                for addr in addrs:
                    if addr not in from_addresses:
                        from_addresses.append(addr)
        if not from_addresses:
            from_addresses.append("Unknown")

        to_addresses = []
        change_addresses = []
        amount_transferred = 0.0
        is_self_tx = True
        
        for vout in res.get("vout", []):
            val = int(vout.get("value", 0)) / 100_000_000
            addrs = vout.get("addresses", [])
            
            is_change = any(addr in from_addresses for addr in addrs)
            
            if is_change:
                for addr in addrs:
                    if addr not in change_addresses:
                        change_addresses.append(addr)
            else:
                amount_transferred += val
                is_self_tx = False
                for addr in addrs:
                    if addr not in to_addresses:
                        to_addresses.append(addr)
                
        if is_self_tx and res.get("vout"):
            amount_transferred = int(res.get("vout")[0].get("value", 0)) / 100_000_000
            to_addresses = [from_addresses[0]] if from_addresses else ["Unknown"]
            change_addresses = [from_addresses[0]] if from_addresses else ["Unknown"]

        if not to_addresses:
            to_addresses.append("Unknown")

        tx_time = res.get('blockTime', res.get('time'))
        if tx_time:
            delta = datetime.now() - datetime.fromtimestamp(tx_time)
            total_seconds = max(0, int(delta.total_seconds()))
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            years, days = divmod(days, 365)
            ago_str = f"{years}y{days}d{hours}h{minutes}m Ago"
        else:
            ago_str = "Unconfirmed"

        print(f"\n{'=' * 60}")
        bh = str(res.get('blockHeight', 'Unconfirmed'))
        print(f"{bh} | {format_time(tx_time)}")
        print(f"{'-' * 60}")
        print(f"{res.get('txid')}")
        print(f"{'·' * 60}") 
        
        print(f"Amount: {amount_transferred:.8f} FLO")
        
        first_from = from_addresses[0]
        print(f"From:   {first_from[:52]}")
        for i in range(52, len(first_from), 52):
            print(f"        {first_from[i:i+52]}")
        for addr in from_addresses[1:]:
            for i in range(0, len(addr), 52):
                print(f"        {addr[i:i+52]}")
            
        first_to = to_addresses[0]
        print(f"To:     {first_to[:52]}")
        for i in range(52, len(first_to), 52):
            print(f"        {first_to[i:i+52]}")
        for addr in to_addresses[1:]:
            for i in range(0, len(addr), 52):
                print(f"        {addr[i:i+52]}")
                
        if change_addresses:
            first_change = change_addresses[0]
            print(f"Change: {first_change[:52]}")
            for i in range(52, len(first_change), 52):
                print(f"        {first_change[i:i+52]}")
            for addr in change_addresses[1:]:
                for i in range(0, len(addr), 52):
                    print(f"        {addr[i:i+52]}")
                
        print(f"In:     {val_in:.8f} FLO")
        print(f"Out:    {val_out:.8f} FLO")
        
        tx_size = res.get('size', 0)
        sat_per_byte = (fees * 100_000_000) / tx_size if tx_size > 0 else 0
        print(f"Fees:   {fees:.8f} FLO\n")
        
        print(f"{res.get('confirmations', 0)} Confirmations")
        print(f"{ago_str}")
        print(f"{res.get('size', 0)} Bytes")
        print(f"{sat_per_byte:.2f} s/B\n")
        
        flo_data = res.get("coinSpecificData", {}).get("floData") or res.get("floData")
        if flo_data:
            print(f"{flo_data}\n")
            
        print("-" * 60, end="")
        return True
    except Exception:
        return False

def search_block(query):
    try:
        res = session.get(f"{BASE_URL}/block/{query}?details=txs", timeout=10).json()
        if "error" in res:
            return False
            
        tx_list = res.get("txs", [])
        
        block_time = res.get('time')
        if block_time:
            delta = datetime.now() - datetime.fromtimestamp(block_time)
            total_seconds = max(0, int(delta.total_seconds()))
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            years, days = divmod(days, 365)
            ago_str = f"{years}y{days}d{hours}h{minutes}m Ago"
        else:
            ago_str = "Unconfirmed"
        
        print(f"\n{'=' * 60}")
        print(f"{res.get('height')} | {format_time(res.get('time'))}")
        print(f"{'-' * 60}")
        print(f"{res.get('hash')}")
        print("·" * 60)
        print(f"{res.get('txCount', 0)} TXs")
        print(f"{res.get('size', 0)} Bytes")
        print(f"{res.get('confirmations', 0)} Confirmations")
        print(f"{ago_str}")
        print(f"{float(res.get('difficulty', 0)):.13f}\n")
        
        for tx in tx_list:
            val_in = int(tx.get("valueIn", 0)) / 100_000_000
            val_out = int(tx.get("value", 0)) / 100_000_000
            fees = int(tx.get("fees", 0)) / 100_000_000
            
            from_addresses = []
            for vin in tx.get("vin", []):
                if vin.get("coinbase"):
                    from_addresses.append("Coinbase")
                else:
                    for addr in vin.get("addresses", []):
                        if addr not in from_addresses:
                            from_addresses.append(addr)
            if not from_addresses:
                from_addresses.append("Unknown")

            to_addresses = []
            change_addresses = []
            amount_transferred = 0.0
            is_self_tx = True
            
            for vout in tx.get("vout", []):
                val = int(vout.get("value", 0)) / 100_000_000
                addrs = vout.get("addresses", [])
                
                is_change = any(addr in from_addresses for addr in addrs)
                
                if is_change:
                    for addr in addrs:
                        if addr not in change_addresses:
                            change_addresses.append(addr)
                else:
                    amount_transferred += val
                    is_self_tx = False
                    for addr in addrs:
                        if addr not in to_addresses:
                            to_addresses.append(addr)
                            
            if is_self_tx and tx.get("vout"):
                amount_transferred = int(tx.get("vout")[0].get("value", 0)) / 100_000_000
                to_addresses = [from_addresses[0]] if from_addresses else ["Unknown"]
                change_addresses = [from_addresses[0]] if from_addresses else ["Unknown"]

            if not to_addresses:
                to_addresses.append("Unknown")

            print("-" * 60)
            print(f"{tx.get('txid')}")
            print("·" * 60) 
            
            print(f"Amount: {amount_transferred:.8f} FLO")
            
            first_from = from_addresses[0]
            print(f"From:   {first_from[:52]}")
            for i in range(52, len(first_from), 52):
                print(f"        {first_from[i:i+52]}")
            for addr in from_addresses[1:]:
                for i in range(0, len(addr), 52):
                    print(f"        {addr[i:i+52]}")
                
            first_to = to_addresses[0]
            print(f"To:     {first_to[:52]}")
            for i in range(52, len(first_to), 52):
                print(f"        {first_to[i:i+52]}")
            for addr in to_addresses[1:]:
                for i in range(0, len(addr), 52):
                    print(f"        {addr[i:i+52]}")
                    
            if change_addresses:
                first_change = change_addresses[0]
                print(f"Change: {first_change[:52]}")
                for i in range(52, len(first_change), 52):
                    print(f"        {first_change[i:i+52]}")
                for addr in change_addresses[1:]:
                    for i in range(0, len(addr), 52):
                        print(f"        {addr[i:i+52]}")
                
            print(f"In:     {val_in:.8f} FLO")
            print(f"Out:    {val_out:.8f} FLO")
            
            tx_size = tx.get('size', 0)
            sat_per_byte = (fees * 100_000_000) / tx_size if tx_size > 0 else 0
            print(f"Fees:   {fees:.8f} FLO\n")
            
            print(f"{tx.get('size', 0)} Bytes")
            print(f"{sat_per_byte:.2f} s/B\n")
            
            flo_data = tx.get("coinSpecificData", {}).get("floData") or tx.get("floData")
            if flo_data:
                print(f"{flo_data}\n")
                
        print("-" * 60, end="")
        return True
    except Exception:
        return False

def search_address(query):
    try:
        res = session.get(f"{BASE_URL}/address/{query}?details=txs", timeout=10).json()
        if "error" in res:
            return False
            
        bal_flo = int(res.get("balance", 0)) / 100_000_000
        total_rx = int(res.get("totalReceived", 0)) / 100_000_000
        total_tx = int(res.get("totalSent", 0)) / 100_000_000
        
        print(f"\n{'=' * 60}")
        print(f"{res.get('address')}")
        print(f"{'-' * 60}")
        print(f"Balance: {bal_flo:.8f} FLO")
        print("·" * 60)
        print(f"In:      {total_rx:.8f} FLO")
        print(f"Out:     {total_tx:.8f} FLO\n")
        print(f"{res.get('txs', 0)} TXs\n")
        
        tx_list = res.get("transactions", [])
        for tx in tx_list:
            print("-" * 60)
            bh = tx.get("blockHeight")
            block_height = str(bh) if bh and bh > 0 else "Unconfirmed"
            b_time = format_time(tx.get("blockTime", tx.get("time")))
            
            print(f"{block_height} | {b_time}")
            print("·" * 60)
            print(f"{tx.get('txid')}")
            print("·" * 60)
            
            is_sender = False
            for vin in tx.get("vin", []):
                if query in vin.get("addresses", []):
                    is_sender = True
                    break

            val_out_total = int(tx.get("value", 0)) / 100_000_000

            if is_sender:
                to_addresses = []
                has_change = False
                amount_transferred = 0.0
                
                for vout in tx.get("vout", []):
                    val = int(vout.get("value", 0)) / 100_000_000
                    addresses = vout.get("addresses", [])
                    
                    is_change = False
                    for addr in addresses:
                        if addr == query:
                            has_change = True
                            is_change = True
                        elif addr not in to_addresses:
                            to_addresses.append(addr)
                            
                    if not is_change:
                        amount_transferred += val
                        
                if to_addresses:
                    print(f"Amount:  {amount_transferred:.8f} FLO")
                    print(f"To:      {', '.join(to_addresses)}")
                    if has_change:
                        print(f"Change:  {query}")
                else:
                    if tx.get("vout"):
                        amount_transferred = int(tx.get("vout")[0].get("value", 0)) / 100_000_000
                    else:
                        amount_transferred = val_out_total
                        
                    print(f"Amount:  {amount_transferred:.8f} FLO")
                    print(f"To:      {query}")
                    print(f"Change:  {query}")
            else:
                from_addresses = []
                for vin in tx.get("vin", []):
                    if vin.get("coinbase"):
                        from_addresses.append("Coinbase")
                    else:
                        for addr in vin.get("addresses", []):
                            if addr not in from_addresses:
                                from_addresses.append(addr)
                if not from_addresses:
                    from_addresses.append("Unknown")
                    
                amount_received = 0.0
                for vout in tx.get("vout", []):
                    if query in vout.get("addresses", []):
                        amount_received += int(vout.get("value", 0)) / 100_000_000
                        
                print(f"Amount:  {amount_received:.8f} FLO")
                print(f"From:    {', '.join(from_addresses)}")
                
            val_in = int(tx.get("valueIn", 0)) / 100_000_000
            fees = int(tx.get("fees", 0)) / 100_000_000
            
            print(f"In:      {val_in:.8f} FLO")
            print(f"Out:     {val_out_total:.8f} FLO")
            
            tx_size = tx.get('size', 0)
            sat_per_byte = (fees * 100_000_000) / tx_size if tx_size > 0 else 0
            print(f"Fees:    {fees:.8f} FLO\n")
            
            tx_time = tx.get('blockTime', tx.get('time'))
            if tx_time:
                delta = datetime.now() - datetime.fromtimestamp(tx_time)
                total_seconds = max(0, int(delta.total_seconds()))
                minutes, seconds = divmod(total_seconds, 60)
                hours, minutes = divmod(minutes, 60)
                days, hours = divmod(hours, 24)
                years, days = divmod(days, 365)
                ago_str = f"{years}y{days}d{hours}h{minutes}m Ago"
            else:
                ago_str = "Unconfirmed"
                
            print(f"{tx.get('confirmations', 0)} Confirmations")
            print(f"{ago_str}")
            print(f"{tx.get('size', 0)} Bytes")
            print(f"{sat_per_byte:.2f} s/B\n")
            
            flo_data = tx.get("coinSpecificData", {}).get("floData") or tx.get("floData")
            if flo_data:
                print(f"{flo_data}\n")
                
        print("-" * 60, end="")
        return True
    except Exception:
        return False

def main():
    while True:
        current_height = get_latest_height()
        
        print("--- E X P L O R E R ---")
        print(f"Height: {current_height}")
        query = input("Search: ").strip()
        
        if not query:
            print(f"\n" + '='*60)
            break
            
        success = False
        
        if query.isdigit():
            success = search_block(query)
        elif len(query) == 64:
            success = search_tx(query)
            if not success:
                success = search_block(query)
        else:
            success = search_address(query)
            
        if not success:
            print("\nError: Could not find any match\n")

if __name__ == "__main__":
    main()
