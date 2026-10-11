import requests
import math
import base64
import json
from pathlib import Path

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
ITEMS_URL = "https://api.hypixel.net/v2/resources/skyblock/items"

## Get Bazaar Data !

def fetch_bazaar():
    response = requests.get(BAZAAR_URL, timeout=10)
    response.raise_for_status()
    return response.json()["products"]


## Get Item Information !

def fetch_item_data():
    response = requests.get(ITEMS_URL, timeout=10)
    response.raise_for_status()
    return response.json()["items"]


products = fetch_bazaar()
item_data = fetch_item_data()


## Organize Item Information !

def build_item_lookup(items):
    lookup = {}

    for item in items:
        item_id = item.get("id")

        if item_id:
            lookup[item_id] = item

    return lookup


item_lookup = build_item_lookup(item_data)


## Item Icons !

ICON_FOLDER = Path(__file__).parent / "static" / "item_icons"


def decode_skin_url(skin):
    if not skin or not skin.get("value"):
        return None

    try:
        decoded = base64.b64decode(skin["value"]).decode("utf-8")
        data = json.loads(decoded)

        return data["textures"]["SKIN"]["url"].replace(
            "http://",
            "https://"
        )

    except:
        return None


def get_item_icon(item_id, info):

    ## Official SkyBlock texture

    local_icon = ICON_FOLDER / f"{item_id}.png"

    if local_icon.exists():
        return (
            "/static/item_icons/" + item_id + ".png",
            "material"
        )


    ## Player head texture

    skin_url = decode_skin_url(info.get("skin"))

    if skin_url:
        return skin_url, "skin"


    ## Enchantments

    if item_id.startswith("ENCHANTMENT_"):
        return (
            "https://mc.nerothe.com/img/1.20.1/enchanted_book.png",
            "material"
        )


    ## Shards

    if item_id.startswith("SHARD_") or "_SHARD" in item_id:
        return (
            "https://mc.nerothe.com/img/1.20.1/echo_shard.png",
            "material"
        )


    ## Normal Minecraft model

    item_model = info.get("item_model")

    if item_model and item_model.startswith("minecraft:"):
        model_name = item_model.split(":", 1)[1]

        return (
            "https://mc.nerothe.com/img/1.20.1/"
            + model_name
            + ".png",
            "material"
        )


    ## Base material

    material = info.get("material")

    if material:
        return (
            "https://mc.nerothe.com/img/1.20.1/"
            + material.lower()
            + ".png",
            "material"
        )


    return None, "none"


## Price Functions !

def get_buy_order_price(item):
    if not item["sell_summary"]:
        return None

    return item["sell_summary"][0]["pricePerUnit"]


def get_sell_order_price(item):
    if not item["buy_summary"]:
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

    return profit / buy_price * 100


## My personal scaling functions !

def compute_gamma(profit, buy_orders, sell_orders, buy_volume, sell_volume):
    k = 500000

    if profit <= 0 or buy_volume <= 0:
        return 0

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


## Average amount of orders !

def get_average_market_orders(products):
    total_orders = 0
    item_count = 0

    for item in products.values():
        quick = item["quick_status"]

        total_orders += (
            quick["buyOrders"]
            + quick["sellOrders"]
        )

        item_count += 1

    if item_count == 0:
        return 0

    return total_orders / item_count


average_market_orders = get_average_market_orders(products)


## Backup name !

def pretty_item_name(item_id):
    return item_id.replace("_", " ").title()


## Analyze Item !

def analyze_item(name, item, average_market_orders, item_lookup):
    buy_price = get_buy_order_price(item)
    sell_price = get_sell_order_price(item)
    gross_profit = get_profit(item)
    margin = get_margin(item)

    quick = item["quick_status"]

    buy_volume = quick["buyVolume"]
    sell_volume = quick["sellVolume"]

    buy_orders = quick["buyOrders"]
    sell_orders = quick["sellOrders"]

    buy_week = quick["buyMovingWeek"]
    sell_week = quick["sellMovingWeek"]

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


    icon_url, icon_type = get_item_icon(name, info)


    omega = compute_omega(
        buy_orders,
        sell_orders,
        buy_volume,
        sell_volume,
        average_market_orders
    )


    return {
        "name": name,
        "display_name": display_name,
        "category": category,
        "tier": tier,

        "icon_url": icon_url,
        "icon_type": icon_type,

        "buy_price": buy_price,
        "sell_price": sell_price,

        "gross_profit": gross_profit,
        "profit": gross_profit,
        "margin": margin,

        "buy_volume": buy_volume,
        "sell_volume": sell_volume,

        "buy_orders": buy_orders,
        "sell_orders": sell_orders,

        "buy_week": buy_week,
        "sell_week": sell_week,

        "gamma": 0,
        "omega": omega
    }


## Analyze Bazaar !

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


## Bazaar Tax !

def apply_tax(items, tax_rate):
    taxed_items = []

    for item in items:
        buy_price = item["buy_price"]
        sell_price = item["sell_price"]

        if buy_price is None or sell_price is None:
            continue

        money_after_tax = sell_price * (1 - tax_rate)
        profit = money_after_tax - buy_price

        if buy_price > 0:
            margin = profit / buy_price * 100
        else:
            margin = 0

        gamma = compute_gamma(
            profit,
            item["buy_orders"],
            item["sell_orders"],
            item["buy_volume"],
            item["sell_volume"]
        )

        new_item = item.copy()

        new_item["profit"] = profit
        new_item["margin"] = margin
        new_item["gamma"] = gamma
        new_item["tax_rate"] = tax_rate

        taxed_items.append(new_item)

    return taxed_items


## Remove dead markets !

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


## Rank Items !

def rank_items(items, use_omega=False):

    if not use_omega:

        return sorted(
            items,
            key=lambda item: item["gamma"],
            reverse=True
        )


    return sorted(
        items,
        key=lambda item: item["gamma"] * item["omega"],
        reverse=True
    )


## Search !

def search_items(items, search):
    search = search.lower().strip()
    results = []

    for item in items:

        if (
            search in item["name"].lower()
            or search in item["display_name"].lower()
            or search in item["category"].lower()
            or search in item["tier"].lower()
        ):
            results.append(item)

    return results


## Final website list !

def get_ranked_items(
    tax_rate=0.0125,
    use_omega=False,
    search=""
):
    items = apply_tax(all_items, tax_rate)
    items = filter_good_items(items)
    items = rank_items(items, use_omega)

    if search:
        items = search_items(items, search)

    return items
