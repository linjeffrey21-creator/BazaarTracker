import requests
url = "https://hypixel.net"

response = requests.get(url)

print (response.status_code)

data = response.json()

products = data["products"]


def best_buy_order (product): 
 if len(product["buy_summary"]) > 0: return max(product["buy_summary"], key = lambda order: order["pricePerUnit"])
 else: return ()

   
def best_sell_order (product): 
 if len(product["sell_summary"]) > 0: return min(product["sell_summary"], key = lambda order: order["pricePerUnit"])
 else: return ()


item_info = list()

for key, item in products.items():
    if len(item["sell_summary"]) <= 0: 
        buy = "Unavailable" 
    else: 
        buy = best_sell_order(item)["pricePerUnit"]

    if len(item["buy_summary"]) <= 0: 
        sell = "Unavailable"
    else: sell = best_buy_order(item)["pricePerUnit"]

    profit = None
    if buy != "Unavailable" and sell != "Unavailable":
       profit = (sell - buy)

    item_info.append ((key, buy, sell, profit))

ranked_profitlist = sorted(item_info, key = lambda item: item[3] if item[3] is not None else -1, reverse = True)

print(len(item_info))

print(f"\n{'Item ID':<35} | {'Buy Price':<12} | {'Sell Price':<12} | {'Profit':<12}")
print("-" * 78)

for item in ranked_profitlist[:10]:
    key, buy, sell, profit = item
    
    buy_str = f"{buy:,.1f}" if isinstance(buy, (int, float)) else str(buy)
    sell_str = f"{sell:,.1f}" if isinstance(sell, (int, float)) else str(sell)
    profit_str = f"{profit:,.1f}" if isinstance(profit, (int, float)) else "N/A"
    
    print(f"{key:<35} | {buy_str:>12} | {sell_str:>12} | {profit_str:>12}")
