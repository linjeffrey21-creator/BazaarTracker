import requests
import math

## Above is random reqs

def fetch_bazaar():
    response = requests.get("https://api.hypixel.net/v2/skyblock/bazaar")
    data = response.json()
    return data["products"]

products = fetch_bazaar()


## Price Functions !

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

    return sell_price - buy_price


def get_margin(item):
    buy_price = get_buy_order_price(item)
    profit = get_profit(item)

    if buy_price is None or profit is None:
        return None

    return (profit / buy_price) * 100


## My personal scaling functions !

def compute_gamma(profit, buy_orders, sell_orders, buy_volume, sell_volume):
    k = 500000

    if profit <= 0 or buy_volume <= 0:
        return 0

    # Same formula idea as before, but this makes sure huge profits don't crash Python
    x = profit / k
    decay = math.exp(-x)

    gamma = (
        math.log((sell_volume / (buy_volume * 2)) + 1)
        * ((sell_orders + buy_orders) / 10)
        * (profit * ((2 * decay) / (1 + decay)) / 10**6)
    )

    return gamma


def compute_omega(buy_orders, sell_orders, buy_volume, sell_volume, average_market_orders):
    if buy_volume + sell_volume == 0:
        return 0

    volume_balance = 1 - abs(
        (buy_volume - sell_volume)
        / (buy_volume + sell_volume)
    )

    total_orders = buy_orders + sell_orders

    if average_market_orders > 0:
        order_scale = math.tanh(total_orders / average_market_orders)
    else:
        order_scale = 0

    return volume_balance * order_scale


## Find average amount of orders in the Bazaar !

def get_average_market_orders(products):
    total_orders = 0
    item_count = 0

    for name, item in products.items():
        quick = item["quick_status"]

        total_orders += quick["buyOrders"] + quick["sellOrders"]
        item_count += 1

    if item_count == 0:
        return 0

    return total_orders / item_count


average_market_orders = get_average_market_orders(products)


## Analyze each item !

def analyze_item(name, item, average_market_orders):
    buy_price = get_buy_order_price(item)
    sell_price = get_sell_order_price(item)
    profit = get_profit(item)
    margin = get_margin(item)

    # This bottom will be for checking if there volume & demand
    quick = item["quick_status"]

    buy_volume = quick["buyVolume"]
    sell_volume = quick["sellVolume"]
    buy_orders = quick["buyOrders"]
    sell_orders = quick["sellOrders"]

    if profit is None:
        gamma = 0
    else:
        gamma = compute_gamma(
            profit,
            buy_orders,
            sell_orders,
            buy_volume,
            sell_volume
        )

    omega = compute_omega(
        buy_orders,
        sell_orders,
        buy_volume,
        sell_volume,
        average_market_orders
    )

    return {
        "name": name,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "profit": profit,
        "margin": margin,
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "buy_orders": buy_orders,
        "sell_orders": sell_orders,
        "gamma": gamma,
        "omega": omega
    }


## Analyze everything in the Bazaar !

def analyze_all_items(products, average_market_orders):
    analyzed_items = []

    for name, item in products.items():
        analyzed = analyze_item(name, item, average_market_orders)

        if analyzed["profit"] is not None:
            analyzed_items.append(analyzed)

    return analyzed_items


all_items = analyze_all_items(products, average_market_orders)


## Rank Items !

ranked_items = sorted(
    all_items,
    key=lambda item: item["gamma"],
    reverse=True
)

print(ranked_items[:10])
