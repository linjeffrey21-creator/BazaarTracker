import requests
import math

## Above is random reqs

## Get Bazaar Data..

def fetch_bazaar():
    response = requests.get(
        "https://api.hypixel.net/v2/skyblock/bazaar",
        timeout=10
    )

    response.raise_for_status()

    data = response.json()
    return data["products"]


## Get Item Information !

def fetch_item_data():
    response = requests.get(
        "https://api.hypixel.net/v2/resources/skyblock/items",
        timeout=10
    )

    response.raise_for_status()

    data = response.json()
    return data["items"]


products = fetch_bazaar()
item_data = fetch_item_data()


## Organize Item Information !

def build_item_lookup(item_data):
    item_lookup = {}

    for item in item_data:
        item_id = item.get("id")

        if item_id is not None:
            item_lookup[item_id] = item

    return item_lookup


item_lookup = build_item_lookup(item_data)


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

    # Same formula idea but prevents huge profits from crashing Python
    x = profit / k
    decay = math.exp(-x)

    gamma = (
        math.log((sell_volume / (buy_volume * 2)) + 1)
        * ((sell_orders + buy_orders) / 10)
        * (profit * ((2 * decay) / (1 + decay)) / 10**6)
    )

    return gamma


def compute_omega(
    buy_orders,
    sell_orders,
    buy_volume,
    sell_volume,
    average_market_orders
):
    if buy_volume + sell_volume == 0:
        return 0

    volume_balance = 1 - abs(
        (buy_volume - sell_volume)
        / (buy_volume + sell_volume)
    )

    total_orders = buy_orders + sell_orders

    if average_market_orders > 0:
        order_scale = math.tanh(
            total_orders / average_market_orders
        )

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


## Backup name maker !

def pretty_item_name(item_id):
    return item_id.replace("_", " ").title()


## Analyze each item !

def analyze_item(name, item, average_market_orders, item_lookup):
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

    buy_week = quick["buyMovingWeek"]
    sell_week = quick["sellMovingWeek"]

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

    ## Get actual Hypixel item information

    info = item_lookup.get(name, {})

    display_name = info.get(
        "name",
        pretty_item_name(name)
    )

    category = info.get("category")

    if category is None:
        category = "Other"

    else:
        category = category.replace("_", " ").title()

    tier = info.get("tier")

    if tier is None:
        tier = "Unknown"

    else:
        tier = tier.replace("_", " ").title()

    return {
        "name": name,
        "display_name": display_name,
        "category": category,
        "tier": tier,

        "buy_price": buy_price,
        "sell_price": sell_price,

        "profit": profit,
        "margin": margin,

        "buy_volume": buy_volume,
        "sell_volume": sell_volume,

        "buy_orders": buy_orders,
        "sell_orders": sell_orders,

        "buy_week": buy_week,
        "sell_week": sell_week,

        "gamma": gamma,
        "omega": omega
    }


## Analyze everything in the Bazaar !

def analyze_all_items(products, average_market_orders, item_lookup):
    analyzed_items = []

    for name, item in products.items():

        analyzed = analyze_item(
            name,
            item,
            average_market_orders,
            item_lookup
        )

        if analyzed["profit"] is not None:
            analyzed_items.append(analyzed)

    return analyzed_items


all_items = analyze_all_items(
    products,
    average_market_orders,
    item_lookup
)


## Filter out dead markets !

def filter_good_items(items):
    good_items = []

    for item in items:

        if (
            item["profit"] > 0
            and item["buy_week"] > 100
            and item["sell_week"] > 100
        ):
            good_items.append(item)

    return good_items


good_items = filter_good_items(all_items)


## Rank Items !

def rank_items(items, use_omega=False):

    # Default ranking is only Gamma
    if use_omega == False:

        return sorted(
            items,
            key=lambda item: item["gamma"],
            reverse=True
        )

    # Player can choose to factor Omega into ranking later
    else:

        return sorted(
            items,
            key=lambda item: item["gamma"] * item["omega"],
            reverse=True
        )


ranked_items = rank_items(good_items)


## Search Items !

def search_items(items, search):
    search = search.lower().strip()

    results = []

    for item in items:

        name = item["name"].lower()
        display_name = item["display_name"].lower()
        category = item["category"].lower()
        tier = item["tier"].lower()

        if (
            search in name
            or search in display_name
            or search in category
            or search in tier
        ):
            results.append(item)

    return results


## Testing !

print("Bazaar items:", len(products))
print("SkyBlock item data:", len(item_data))
print("Analyzed items:", len(all_items))
print("Good items:", len(good_items))

print()

for item in ranked_items[:10]:

    print(
        item["display_name"],
        "| Category:", item["category"],
        "| Tier:", item["tier"],
        "| Profit:", round(item["profit"]),
        "| Margin:", round(item["margin"], 2),
        "| Gamma:", round(item["gamma"], 3),
        "| Omega:", round(item["omega"], 3)
    )
