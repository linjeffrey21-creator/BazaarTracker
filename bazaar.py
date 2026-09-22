import requests

## Above is random reqs

def fetch_bazaar():
    response = requests.get("https://api.hypixel.net/v2/skyblock/bazaar")
    data = response.json()
    return (data["products"])

products = fetch_bazaar()

def get_buy_order_price(item):
    if len(item["sell_summary"]) == 0:
        return None
    return item["sell_summary"][0]["pricePerUnit"]


def get_sell_order_price(item):
    if len(item["buy_summary"]) == 0:
        return None
    return item["buy_summary"][0]["pricePerUnit"]

def get_profit(item):
    buy_price = get_buy_order_price(item)
    sell_price = get_sell_order_price(item)

    if buy_price is None or sell_price is None:
        return None

    return (sell_price - buy_price)

def get_margin(item):
    buy_price = get_buy_order_price(item)
    profit = get_profit(item)

    if buy_price is None or profit is None:
        return None
    return (profit/buy_price) * 100

def analyze_item(name, item):
    buy_price = get_buy_order_price(item)
    sell_price = get_sell_order_price(item)
    profit = get_profit(item)
    margin = get_margin(item)

    return{
        "name": name,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "profit": profit,
        "margin": margin
    }

def analyze_all_items(products):
    analyzed_items=[]

    for name, item in products.items():
        analyzed = analyze_item(name, item)

        if analyzed["profit"] is not None:
            analyzed_items.append(analyzed)
    return analyzed_items

all_items = analyze_all_items(products)

ranked_items = sorted(all_items, key=lambda item: item["profit"], reverse = True)

print(ranked_items[:10])
