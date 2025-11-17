from broker import BrokerInterface
import os

os.chdir("/root/dai-trader")
broker = BrokerInterface()
positions = broker.get_positions()

print("\n=== OPEN POSITIONS ===")
if positions:
    total_pl = 0
    for p in positions:
        if isinstance(p, dict):
            symbol = p.get('symbol', 'N/A')
            qty = p.get('qty', 0)
            avg_price = p.get('avg_entry_price', 0)
            current = p.get('current_price', 0)
            pl = float(p.get('unrealized_pl', 0))
            pl_pct = p.get('unrealized_plpc', 0)
        else:
            symbol = p.symbol
            qty = p.qty
            avg_price = p.avg_entry_price
            current = p.current_price
            pl = float(p.unrealized_pl)
            pl_pct = p.unrealized_plpc
        total_pl += pl
        print(f"{symbol}: {qty} shares @ ${avg_price} | Current: ${current} | P/L: ${pl:.2f} ({pl_pct}%)")
    print(f"\nTOTAL UNREALIZED P/L: ${total_pl:.2f}")
else:
    print("No open positions")
