import requests
url = "https://api.hypixel.net/v2/skyblock/bazaar"

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
THErank = (ranked_profitlist[:10])

search = input("What item do you want?")
search = search.upper().replace(" ","_")

if search in products:
    item = products[search]
    if len(item["sell_summary"]) > 0:
       buy = best_sell_order(item)["pricePerUnit"]
    else:
        buy = "Unavailable"

    if len(item["buy_summary"]) > 0:
        sell = best_buy_order(item)["pricePerUnit"]
    else:
       sell = "Unavailable"

    print()
    print("Item:", search)
    print("Buy price:", buy)
    print("Sell price:", sell)

    if buy != "Unavailable" and sell != "Unavailable":
        profit = sell - buy
        print("Profit per item:", profit)

else:
    print("Item not found.")


