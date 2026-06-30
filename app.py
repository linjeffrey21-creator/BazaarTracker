import json
import math
import base64
import time
import re
from urllib.request import Request, urlopen
import ssl
from flask import Flask, render_template_string

# Some environments (notably macOS) need this to avoid SSL cert errors
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
ITEMS_URL = "https://api.hypixel.net/v2/resources/skyblock/items"
ITEM_METADATA_TTL = 60 * 60
_item_metadata_cache = {"loaded_at": 0, "items": {}}
ITEM_NAME_OVERRIDES = {
    "RED_GIFT": "Red Gift",
    "VOLCANIC_ROCK": "Volcanic Rock",
}

categorized_stones = {
    "Armor": [
        "CANDY_CORN", "DEEP_SEA_ORB", "DIAMOND_ATOM", "DRAGON_HORN", "DRAGON_SCALE",
        "END_STONE_GEODE", "FROZEN_BAUBLE", "GIANT_TOOTH", "JADERALD", "MANGROVE_GEM",
        "MANTID_CLAW", "MOLTEN_CUBE", "NECROMANCER_BROOCH", "OVERGROWN_GRASS", "PRECURSOR_GEAR",
        "PREMIUM_FLESH", "RARE_DIAMOND", "RED_NOSE", "RED_SCARF", "SADAN_BROOCH",
        "SKYMART_BROCHURE", "SUNSTONE", "TITANIUM_TESSERACT"
    ],
    "Axe and Hoe": [
        "BLESSED_FRUIT", "GOLDEN_BALL", "LARGE_WALNUT", "MOIL_LOG", "MOONGLADE_JEWEL",
        "TOIL_LOG", "HASHBROWN"
    ],
    "Bow": [
        "OPTICAL_LENS", "KALEIDOSCOPIC_MINERAL", "SPIRIT_STONE", "SALMON_OPAL"
    ],
    "Drill and Pickaxe": [
        "AMBER_MATERIAL", "ANDESITE_WHETSTONE", "BLACK_DIAMOND", "DIAMONITE", "DWARVEN_GEODE",
        "FRIGID_HUSK", "GLEAMING_CRYSTAL", "LAPIS_CRYSTAL", "PETRIFIED_STARFALL", "PURE_MITHRIL",
        "ROCK_GEMSTONE", "SCORCHED_TOPAZ"
    ],
    "Sword": [
        "BULKY_STONE", "DIRT_BOTTLE", "DRAGON_CLAW", "ENTROPY_SUPPRESSOR", "FULL_JAW_FANKING_KIT",
        "JERRY_STONE", "MIDAS_JEWEL", "SUSPICIOUS_VIAL", "WARPED_STONE", "WITHER_BLOOD"
    ],
    "Fishing Rod": [
        "HARDENED_WOOD", "KUUDRA_MANDIBLE", "LUCKY_DICE", "PITCHIN_KOI", "RUSTY_ANCHOR", "SALT_CUBE"
    ],
    "Froggles": [
        "GEOMETRIC_ODDITY"
    ],
    "Equipment": [
        "BLAZE_WAX", "BLAZEN_SPHERE", "BURROWING_SPORES", "CALCIFIED_HEART", "DWARVEN_TREASURE", "FLOWERING_BOUQUET",
        "METEOR_CHUNK", "MOONSTONE", "PRESUMED_GALLON_OF_RED_PAINT", "SEARING_STONE", "SHINY_PRISM",
        "SHRIVELED_CORNEA", "SQUEAKY_TOY", "TERRY'S_SNOWGLOBE"
    ],
    "Vacuum": [
        "BEADY_EYES", "CLIPPED_WINGS"
    ],
    "Shark Festival": [
        "BLUE_SHARK_TOOTH", "NURSE_SHARK_TOOTH", "TIGER_SHARK_TOOTH", "GREAT_WHITE_SHARK_TOOTH", "SHARK_FIN", "ENCHANTED_SHARK_FIN", "GREAT_WHITE_TOOTH_MEAL"
    ],
    "Spooky Festival": [
        "GREEN_CANDY", "PURPLE_CANDY", "DARK_CANDY", "ECTOPLASM", "PUMPKIN_GUTS", "SPOOKY_FRAGMENT", "WEREWOLF_SKIN", "SOUL_FRAGMENT", "BAT_FIREWORK", "PUMPKIN_BOMB", "HORSEMAN_CANDLE", "EXPIRED_PUMPKIN"
    ],
    "Winter Island": [
        "WHITE_GIFT", "GREEN_GIFT", "RED_GIFT", "PARTY_GIFT", "REFINED_BOTTLE_OF_JYRRE", "VOLCANIC_ROCK", "WALNUT", "BLIZZARD_BOTTLE"
    ],
    "Mythological Ritual": [
        "GRIFFIN_FEATHER", "BRAIDED_GRIFFIN_FEATHER", "DAEDALUS_STICK", "ANCIENT_CLAW", "ENCHANTED_ANCIENT_CLAW", "MYTHOS_FRAGMENT"
    ],
    "Mayor Jerry": [
        "JERRY_BOX_GREEN", "JERRY_BOX_BLUE", "JERRY_BOX_PURPLE", "JERRY_BOX_GOLDEN"
    ],
    "Minerals": [
        "REFINED_MINERAL", "GLOSSY_GEMSTONE"
    ],
    "Tickets": [
        "JACOBS_TICKET", "AGATHA_COUPON"
    ],
    "Diaz": [
        "AVARICIOUS_CHALICE", "FRESHLY_MINTED_COINS", "BLOOD_STAINED_COINS", "BLOOD_SOAKED_COINS"
    ],
    "Hoppity's Hunt": [
        "SUPREME_CHOCOLATE_BAR", "REFINED_DARK_CACAO_TRUFFLE"
    ],
    "Year of the Seal": [
        "BOUNCY_BEACH_BALL", "GIANT_BOUNCY_BEACH_BALL"
    ],
    "Feast": [
        "FEAST_FLASK", "AGGOURDIAN", "CORNUCOPIA", "CANE_KNOT", "FLORAL_GELATIN", "DESIGNER_COFFEE_BEANS",
        "SALTED_SUNFLOWER_SEEDS", "CRYSTALIZED_MOONLIGHT", "BOTROOT", "DEEPFRIES", "CARROT_ZEST",
        "FEASTFUNGUS", "CACTUS_FLOWER", "MELON_JUICE"
    ]
}


def compute_gamma(buy_price, sell_price, profit, active_buy_orders, active_sell_orders,
                   live_buy_volume, live_sell_volume):
    k = 500000
    if sell_price > 0 and profit > 0 and live_buy_volume > 0:
        gamma = math.log((live_sell_volume / (live_buy_volume * 2)) + 1) * \
                ((active_sell_orders + active_buy_orders) / 10) * \
                (((profit * (2 / (1 + math.e ** (profit / k))) / 10 ** 6)))
    else:
        gamma = 0
    return gamma
# Calculates γ to create a composite demand score, such that the user can see the true demand of an item!


def compute_omega(active_buy_orders, active_sell_orders, live_buy_volume, live_sell_volume,
                   average_market_orders):
    if (live_buy_volume + live_sell_volume) == 0:
        return 0
    obi_stability = 1 - abs((live_buy_volume - live_sell_volume) / (live_buy_volume + live_sell_volume))
    total_orders = active_buy_orders + active_sell_orders
    order_scale = math.tanh(total_orders / average_market_orders) if average_market_orders > 0 else 0
    return obi_stability * order_scale
# Calculates Ω to create a composite stability score, such that the user can determine the volatility of an item.


def clean_item_name(name):
    """Removes Minecraft and Hypixel formatting tokens from display names."""
    name = re.sub(r"(?:§|&|\$)[0-9a-fk-or]", "", name, flags=re.IGNORECASE)
    name = re.sub(r"%%[a-z0-9_]+%%", "", name, flags=re.IGNORECASE)
    return name.strip()


def pretty_item_name(item_id):
    return ITEM_NAME_OVERRIDES.get(
        item_id,
        item_id.replace("_", " ").replace("'", "").title(),
    )


def material_icon_url(material):
    if not material:
        return None
    material_name = material.lower()
    return f"https://mc.nerothe.com/img/1.20.1/{material_name}.png"


def decode_skin_url(skin):
    if not skin or not skin.get("value"):
        return None
    try:
        decoded = base64.b64decode(skin["value"]).decode("utf-8")
        texture_data = json.loads(decoded)
        return texture_data["textures"]["SKIN"]["url"].replace("http://", "https://")
    except Exception:
        return None


def fetch_item_metadata():
    """Pulls SkyBlock item names and texture metadata from the Hypixel API."""
    now = time.time()
    if _item_metadata_cache["items"] and now - _item_metadata_cache["loaded_at"] < ITEM_METADATA_TTL:
        return _item_metadata_cache["items"]

    req = Request(ITEMS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=10) as response:
        data = json.load(response)

    metadata = {}
    for item in data.get("items", []):
        item_id = item.get("id")
        if not item_id:
            continue

        skin_url = decode_skin_url(item.get("skin"))
        material_url = material_icon_url(item.get("material"))
        metadata[item_id] = {
            "display_name": ITEM_NAME_OVERRIDES.get(
                item_id,
                clean_item_name(item.get("name", "")) or pretty_item_name(item_id),
            ),
            "tier": item.get("tier", ""),
            "material": item.get("material", ""),
            "icon_url": skin_url or material_url,
            "icon_type": "skin" if skin_url else "material",
        }
    _item_metadata_cache["loaded_at"] = now
    _item_metadata_cache["items"] = metadata
    return metadata


def item_record(item_name, category, product_data, average_market_orders, metadata):
    item_data = product_data["quick_status"]

    # quick_status prices are volume-weighted averages. The first entries in
    # these summaries are the actual best orders currently on the Bazaar.
    sell_summary = product_data.get("sell_summary") or []
    buy_summary = product_data.get("buy_summary") or []
    sell_price = (
        sell_summary[0].get("pricePerUnit", item_data["sellPrice"])
        if sell_summary else item_data["sellPrice"]
    )
    buy_price = (
        buy_summary[0].get("pricePerUnit", item_data["buyPrice"])
        if buy_summary else item_data["buyPrice"]
    )
    profit = buy_price - sell_price
    weekly_volume = item_data["sellMovingWeek"] + item_data["buyMovingWeek"]
    active_buy_orders = item_data["buyOrders"]
    active_sell_orders = item_data["sellOrders"]
    live_buy_volume = item_data["buyVolume"]
    live_sell_volume = item_data["sellVolume"]

    gamma = compute_gamma(buy_price, sell_price, profit,
                          active_buy_orders, active_sell_orders,
                          live_buy_volume, live_sell_volume)

    omega = compute_omega(active_buy_orders, active_sell_orders,
                          live_buy_volume, live_sell_volume, average_market_orders)

    item_meta = metadata.get(item_name, {})
    return {
        "name": item_name,
        "display_name": item_meta.get("display_name", pretty_item_name(item_name)),
        "category": category,
        "tier": item_meta.get("tier", ""),
        "icon_url": item_meta.get("icon_url"),
        "icon_type": item_meta.get("icon_type", "fallback"),
        "margin": profit,
        "volume": weekly_volume,
        "active_buyers": active_buy_orders,
        "active_sellers": active_sell_orders,
        "buy_order": sell_price,
        "sell_order": buy_price,
        "gamma": gamma,
        "omega": omega,
    }


def fetch_bazaar_data():
    """Pulls the live Bazaar snapshot from the Hypixel API."""
    req = Request(BAZAAR_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=10) as response:
        return json.load(response)


def build_tracker_results():
    """
    Runs the same logic as the original script: fetches live data, computes
    gamma/omega per item, and returns (category_results, top_20_flips).
    Returns (None, None, error_message) if the fetch fails.
    """
    try:
        data = fetch_bazaar_data()
    except Exception as e:
        return None, None, f"Couldn't reach the Hypixel API: {e}"

    try:
        metadata = fetch_item_metadata()
    except Exception:
        metadata = {}

    if not data.get("success"):
        return None, None, "Hypixel API responded but reported failure."

    all_orders = [
        item_data["quick_status"]["buyOrders"] + item_data["quick_status"]["sellOrders"]
        for item_name, item_data in data["products"].items() if item_data.get("quick_status")
    ]
    average_market_orders = sum(all_orders) / len(all_orders) if all_orders else 0

    final_results = {category: [] for category in categorized_stones.keys()}

    for category, items in categorized_stones.items():
        for item_name in items:
            if item_name in data["products"]:
                product_data = data["products"][item_name]
                record = item_record(item_name, category, product_data, average_market_orders, metadata)

                # Everything-on-the-radar view: just needs to be profitable and have
                # traded at least once this week.
                if record["margin"] > 0 and record["volume"] > 0:
                    final_results[category].append(record)

    for category, items in final_results.items():
        items.sort(key=lambda x: x["gamma"], reverse=True)

    all_profitable_items = []
    for category, items in categorized_stones.items():
        for item_name in items:
            if item_name in data["products"]:
                product_data = data["products"][item_name]
                item_data = product_data["quick_status"]
                record = item_record(item_name, category, product_data, average_market_orders, metadata)

                is_profitable = record["margin"] > 10000
                # Strict gate: only items that pass this show up in the Top 20.
                is_liquid = (item_data["buyMovingWeek"] > 100 and item_data["sellMovingWeek"] > 100)

                if is_profitable and is_liquid:
                    all_profitable_items.append(record)

    all_profitable_items.sort(key=lambda x: x["gamma"], reverse=True)
    top_20_flips = all_profitable_items[:20]
    max_gamma = max((item["gamma"] for item in top_20_flips), default=1) or 1

    for item in top_20_flips:
        item["gamma_percent"] = max(3, min(100, (item["gamma"] / max_gamma) * 100))
        item["omega_percent"] = max(3, min(100, item["omega"] * 100))

    for items in final_results.values():
        for item in items:
            item["gamma_percent"] = max(3, min(100, (item["gamma"] / max_gamma) * 100))
            item["omega_percent"] = max(3, min(100, item["omega"] * 100))

    return final_results, top_20_flips, None

#Looks
PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bazaar Tracker HSB</title>
<style>
  :root {
    --cream: #f8efe4;
    --latte: #ead2bc;
    --mocha: #8f674d;
    --espresso: #3a2a22;
    --cocoa: #5a4034;
    --card: #dcbfa5;
    --card-light: #f5e4d3;
    --line: #bd9878;
    --text: #2c211b;
    --muted: #755f51;
    --bar-bg: #ccb49f;
    --gamma: #9d6843;
    --omega: #6f9a9b;
    --profit: #6f7f45;
    --danger: #a95743;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    min-height: 100vh;
    background:
      radial-gradient(circle at 16% 12%, rgba(255, 255, 255, 0.62), transparent 28%),
      linear-gradient(135deg, #efe0cf 0%, #d5b18f 48%, #b98e6d 100%);
    color: var(--text);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 34px 24px 60px;
  }

  .wrap {
    max-width: 1180px;
    margin: 0 auto;
  }

  .hero {
    position: relative;
    display: flex;
    justify-content: space-between;
    gap: 24px;
    align-items: flex-end;
    margin-bottom: 22px;
    min-height: 150px;
    padding-right: 238px;
  }

  .hero-mocha-stage {
    position: absolute;
    right: 8px;
    bottom: -9px;
    width: 218px;
    height: 170px;
    pointer-events: none;
  }

  .hero-mocha {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    opacity: 0;
    transform: translateY(5px) scale(0.98);
    transition: opacity 650ms ease, transform 650ms ease;
    filter: drop-shadow(0 12px 12px rgba(67, 44, 30, 0.16));
  }

  .hero-mocha.active { opacity: 1; transform: translateY(0) scale(1); }
  .hero-mocha.blend {
    mix-blend-mode: multiply;
    filter: none;
    -webkit-mask-image: radial-gradient(ellipse 78% 76% at center, #000 62%, transparent 100%);
    mask-image: radial-gradient(ellipse 78% 76% at center, #000 62%, transparent 100%);
  }

  h1 {
    margin: 12px 0 4px;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2.15rem, 4vw, 4rem);
    line-height: 0.96;
    letter-spacing: 0;
    color: var(--espresso);
  }

  .subtitle {
    max-width: 760px;
    color: var(--muted);
    font-size: 1rem;
    line-height: 1.45;
    margin: 0;
  }

  .refresh-chip {
    flex: 0 0 auto;
    color: var(--espresso);
    background: rgba(255, 250, 244, 0.62);
    border: 1px solid rgba(143, 103, 77, 0.20);
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 0.86rem;
    font-weight: 750;
    box-shadow: 0 12px 24px rgba(58, 42, 34, 0.09);
  }

  .refresh-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 7px;
    border-radius: 50%;
    background: var(--profit);
    box-shadow: 0 0 0 3px rgba(111, 127, 69, 0.14);
  }

  .tax-controls {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    margin: -8px 0 22px;
    padding-right: 238px;
    color: var(--espresso);
    font-size: 0.84rem;
    font-weight: 800;
  }

  .tax-switch {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
  }

  .tax-switch input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }

  .switch-track {
    position: relative;
    width: 42px;
    height: 24px;
    border-radius: 999px;
    background: var(--bar-bg);
    border: 1px solid rgba(143, 103, 77, 0.30);
    transition: background 180ms ease;
  }

  .switch-track::after {
    content: "";
    position: absolute;
    top: 3px;
    left: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff8ef;
    box-shadow: 0 2px 6px rgba(58, 42, 34, 0.25);
    transition: transform 180ms ease;
  }

  .tax-switch input:checked + .switch-track { background: var(--profit); }
  .tax-switch input:checked + .switch-track::after { transform: translateX(18px); }
  .tax-switch input:focus-visible + .switch-track { outline: 3px solid rgba(111, 154, 155, 0.35); }

  .tax-tier {
    color: var(--espresso);
    background: rgba(255, 250, 244, 0.72);
    border: 1px solid rgba(143, 103, 77, 0.28);
    border-radius: 8px;
    padding: 8px 10px;
    font: inherit;
  }

  .tax-tier:disabled { opacity: 0.55; }

  .error-box {
    background: #f4d8cf;
    border: 1px solid #c57f69;
    color: #7a2f22;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 24px;
    font-weight: 750;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
  }

  .flip-card {
    position: relative;
    display: grid;
    grid-template-columns: 142px minmax(0, 1fr);
    gap: 18px;
    align-items: stretch;
    background: rgba(245, 228, 211, 0.86);
    border: 1px solid rgba(143, 103, 77, 0.25);
    border-radius: 8px;
    padding: 14px;
    box-shadow: 0 18px 30px rgba(67, 44, 30, 0.14), inset 0 1px rgba(255, 255, 255, 0.65);
  }

  .item-art {
    min-height: 142px;
    border-radius: 8px;
    background: linear-gradient(145deg, #d4ad8e, #f6e4d2);
    border: 1px solid rgba(143, 103, 77, 0.28);
    box-shadow: inset 0 1px rgba(255,255,255,0.60), 0 10px 20px rgba(58,42,34,0.14);
    position: relative;
    overflow: hidden;
    display: grid;
    place-items: center;
  }

  .item-art::before,
  .item-art::after {
    content: "";
    position: absolute;
    border-radius: 999px;
    background: rgba(255,255,255,0.28);
  }
  .item-art::before { width: 86px; height: 86px; top: -26px; right: -24px; }
  .item-art::after { width: 54px; height: 54px; bottom: -20px; left: -14px; }

  .skin-icon {
    width: 86px;
    height: 86px;
    image-rendering: pixelated;
    background-repeat: no-repeat;
    background-size: 800% 800%;
    background-position: 14.2857% 14.2857%;
    border-radius: 8px;
    transform: scale(1.18);
    box-shadow: 0 8px 16px rgba(58, 42, 34, 0.18);
    position: relative;
    z-index: 1;
  }

  .material-icon {
    width: 88px;
    height: 88px;
    object-fit: contain;
    image-rendering: pixelated;
    filter: drop-shadow(0 8px 12px rgba(58, 42, 34, 0.18));
    position: relative;
    z-index: 1;
  }

  .fallback-icon {
    width: 88px;
    height: 88px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: #bb8d6d;
    color: #fff8ef;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 2rem;
    font-weight: 800;
    position: relative;
    z-index: 1;
  }

  .rank {
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 2;
    background: #fff5eb;
    color: var(--espresso);
    border: 1px solid rgba(143, 103, 77, 0.28);
    border-radius: 8px;
    padding: 4px 8px;
    font-weight: 900;
    font-size: 0.82rem;
  }

  .item-body {
    min-width: 0;
    background: rgba(255, 250, 244, 0.48);
    border-radius: 8px;
    padding: 14px 16px 12px;
  }

  .item-head {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 12px;
    margin-bottom: 8px;
  }

  .item-title {
    margin: 0;
    color: var(--espresso);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.42rem;
    line-height: 1.05;
    font-weight: 800;
    overflow-wrap: anywhere;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
    color: var(--cocoa);
    background: #ead0ba;
    border: 1px solid rgba(143, 103, 77, 0.24);
    border-radius: 999px;
    padding: 5px 9px;
    font-size: 0.72rem;
    font-weight: 850;
    text-transform: uppercase;
  }

  .id-line {
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 750;
    margin-bottom: 12px;
    overflow-wrap: anywhere;
  }

  .money-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 12px;
  }

  .money-box {
    border-top: 1px solid rgba(143, 103, 77, 0.20);
    padding-top: 8px;
  }

  .label {
    color: var(--muted);
    display: block;
    font-size: 0.72rem;
    font-weight: 850;
    text-transform: uppercase;
  }

  .value {
    display: block;
    color: var(--espresso);
    font-size: 0.98rem;
    font-weight: 900;
    margin-top: 2px;
  }

  .value.profit { color: var(--profit); }
  .value.profit.loss { color: var(--danger); }

  .bars {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .bar-card {
    min-width: 0;
  }

  .bar-top {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    color: var(--cocoa);
    font-size: 0.79rem;
    font-weight: 900;
    margin-bottom: 5px;
  }

  .metric-label {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .help-tip {
    position: relative;
    display: inline-grid;
    place-items: center;
    width: 15px;
    height: 15px;
    border: 1px solid rgba(90, 64, 52, 0.48);
    border-radius: 50%;
    color: var(--cocoa);
    background: rgba(255, 250, 244, 0.72);
    font: 900 10px/1 ui-sans-serif, system-ui, sans-serif;
    cursor: help;
    outline: none;
  }

  .help-tip:focus-visible {
    box-shadow: 0 0 0 3px rgba(111, 154, 155, 0.28);
  }

  .help-bubble {
    position: absolute;
    z-index: 20;
    left: 50%;
    bottom: calc(100% + 9px);
    width: 220px;
    padding: 9px 10px;
    border: 1px solid rgba(143, 103, 77, 0.32);
    border-radius: 6px;
    background: #fff8ef;
    color: var(--espresso);
    box-shadow: 0 10px 24px rgba(58, 42, 34, 0.18);
    font-size: 0.76rem;
    font-weight: 700;
    line-height: 1.35;
    text-align: left;
    transform: translate(-50%, 4px);
    opacity: 0;
    visibility: hidden;
    transition: opacity 150ms ease, transform 150ms ease;
    pointer-events: none;
  }

  .help-tip:hover .help-bubble,
  .help-tip:focus .help-bubble {
    opacity: 1;
    visibility: visible;
    transform: translate(-50%, 0);
  }

  .track {
    height: 14px;
    background: var(--bar-bg);
    border-radius: 999px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(58, 42, 34, 0.18);
  }

  .fill {
    height: 100%;
    border-radius: inherit;
    min-width: 8px;
  }
  .fill.gamma { background: linear-gradient(90deg, #b77a50, #8f5e3d); }
  .fill.omega { background: linear-gradient(90deg, #86bbb8, #5f8e91); }

  details {
    position: relative;
    margin-top: 28px;
    background: rgba(255, 250, 244, 0.42);
    border: 1px solid rgba(143, 103, 77, 0.22);
    border-radius: 8px;
    padding: 16px;
  }

  summary {
    cursor: pointer;
    font-weight: 900;
    color: var(--espresso);
  }

  .category-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-top: 18px;
  }

  .category-block {
    min-width: 0;
  }

  .category-title {
    color: var(--cocoa);
    font-size: 0.86rem;
    font-weight: 950;
    margin-bottom: 8px;
    text-transform: uppercase;
  }

  .mini-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    color: var(--espresso);
    font-size: 0.84rem;
    padding: 7px 0;
    border-bottom: 1px solid rgba(143, 103, 77, 0.18);
  }

  .mini-item:last-child { border-bottom: none; }
  .mini-name { overflow-wrap: anywhere; font-weight: 750; }
  .mini-stats { color: var(--muted); white-space: nowrap; font-weight: 750; }

  footer {
    margin-top: 28px;
    color: var(--cocoa);
    font-size: 0.84rem;
    text-align: center;
    font-weight: 750;
  }

  @media (max-width: 900px) {
    .grid, .category-grid { grid-template-columns: 1fr; }
    .hero { align-items: start; flex-direction: column; padding-right: 190px; }
    .tax-controls { justify-content: flex-start; padding-right: 190px; }
    .hero-mocha-stage { width: 178px; height: 150px; }
  }

  @media (max-width: 620px) {
    body { padding: 22px 12px 44px; }
    .hero { min-height: 0; padding-right: 0; padding-bottom: 94px; }
    .tax-controls { justify-content: flex-start; flex-wrap: wrap; padding-right: 0; }
    .hero-mocha-stage { width: 132px; height: 108px; right: 2px; }
    .flip-card { grid-template-columns: 104px minmax(0, 1fr); gap: 12px; padding: 10px; }
    .item-art { min-height: 116px; }
    .skin-icon, .material-icon, .fallback-icon { width: 68px; height: 68px; }
    .item-title { font-size: 1.1rem; }
    .item-head, .money-row, .bars { grid-template-columns: 1fr; }
    .item-head { display: grid; }
    .money-row { display: grid; }
    .bars { display: grid; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div>
      <h1>Bazaar Tracker</h1>
      <p class="subtitle">Find live Hypixel SkyBlock Bazaar flips, ranked by demand, stability, and profit margin.</p>
    </div>
    <div class="refresh-chip" aria-live="polite"><span class="refresh-dot" aria-hidden="true"></span>Live prices · refresh in <span id="refresh-countdown">20</span>s</div>
    <div class="hero-mocha-stage" aria-label="Mocha bear">
      <img class="hero-mocha active" src="{{ url_for('static', filename='mocha-bear-reading.png') }}" alt="Mocha bear reading">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-selfie.png') }}" alt="Mocha bear taking a photo">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-silly.png') }}" alt="Mocha bear being silly">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-hearts.png') }}" alt="Mocha bear with hearts">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-nom.png') }}" alt="Mocha bear eating fruit">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-donuts.png') }}" alt="Mocha bear carrying donuts">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-pizza.png') }}" alt="Mocha bear eating pizza">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-awkward.png') }}" alt="Mocha bear looking awkward">
      <img class="hero-mocha blend" src="{{ url_for('static', filename='mocha-angel.png') }}" alt="Mocha bear dressed as an angel">
      <img class="hero-mocha" src="{{ url_for('static', filename='mocha-bear-studying.png') }}" alt="Mocha bear studying">
      <img class="hero-mocha" src="{{ url_for('static', filename='mocha-bear-coffee.png') }}" alt="Mocha bear reading with a drink">
    </div>
  </header>

  <div class="tax-controls" aria-label="Bazaar tax settings">
    <label class="tax-switch">
      <input id="tax-toggle" type="checkbox">
      <span class="switch-track" aria-hidden="true"></span>
      <span>Include Bazaar tax</span>
    </label>
    <select id="tax-tier" class="tax-tier" aria-label="Bazaar tax reduction level" disabled>
      <option value="0.0125">No upgrade · 1.25%</option>
      <option value="0.01125">Bazaar Flipper I · 1.125%</option>
      <option value="0.01">Bazaar Flipper II · 1.0%</option>
    </select>
  </div>

  {% if error %}
    <div class="error-box">{{ error }}</div>
  {% else %}
    <section class="grid" aria-label="Top 20 liquid flips">
      {% for item in top_20 %}
        <article class="flip-card">
          <div class="item-art">
            <div class="rank">#{{ loop.index }}</div>
            {% if item.icon_url and item.icon_type == "skin" %}
              <div class="skin-icon" style="background-image: url('{{ item.icon_url }}');" role="img" aria-label="{{ item.display_name }} icon"></div>
            {% elif item.icon_url %}
              <img class="material-icon" src="{{ item.icon_url }}" alt="{{ item.display_name }} icon" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='grid';">
              <div class="fallback-icon" style="display:none;">{{ item.display_name[:1] }}</div>
            {% else %}
              <div class="fallback-icon">{{ item.display_name[:1] }}</div>
            {% endif %}
          </div>

          <div class="item-body">
            <div class="item-head">
              <h2 class="item-title">{{ item.display_name }}</h2>
              <span class="tag">{{ item.category }}</span>
            </div>
            <div class="id-line">{{ item.name }}{% if item.tier %} · {{ item.tier.title() }}{% endif %}</div>

            <div class="money-row">
              <div class="money-box">
                <span class="label profit-label">Gross profit</span>
                <span class="value profit profit-value" data-buy="{{ item.buy_order }}" data-sell="{{ item.sell_order }}">{{ "{:,.0f}".format(item.margin) }}c</span>
              </div>
              <div class="money-box">
                <span class="label">Buy order</span>
                <span class="value">{{ "{:,.0f}".format(item.buy_order) }}</span>
              </div>
              <div class="money-box">
                <span class="label">Sell order</span>
                <span class="value">{{ "{:,.0f}".format(item.sell_order) }}</span>
              </div>
            </div>

            <div class="bars">
              <div class="bar-card">
                <div class="bar-top"><span class="metric-label">Gamma <span class="help-tip" tabindex="0" aria-label="What Gamma means">?<span class="help-bubble" role="tooltip">Demand score: higher values suggest stronger buyer activity and profit potential.</span></span></span><span>{{ "%.3f"|format(item.gamma) }}</span></div>
                <div class="track"><div class="fill gamma" style="width: {{ '%.2f'|format(item.gamma_percent) }}%;"></div></div>
              </div>
              <div class="bar-card">
                <div class="bar-top"><span class="metric-label">Omega <span class="help-tip" tabindex="0" aria-label="What Omega means">?<span class="help-bubble" role="tooltip">Stability score from 0 to 1: higher values suggest a more balanced, less volatile market.</span></span></span><span>{{ "%.3f"|format(item.omega) }}</span></div>
                <div class="track"><div class="fill omega" style="width: {{ '%.2f'|format(item.omega_percent) }}%;"></div></div>
              </div>
            </div>
          </div>
        </article>
      {% endfor %}
    </section>

    <details>
      <summary>Full category breakdown</summary>
      <div class="category-grid">
        {% for category, items in categories.items() %}
          {% if items %}
          <div class="category-block">
            <div class="category-title">{{ category }}</div>
            {% for item in items %}
              <div class="mini-item">
                <span class="mini-name">{{ item.display_name }}</span>
                <span class="mini-stats">γ {{ "%.2f"|format(item.gamma) }} · Ω {{ "%.2f"|format(item.omega) }} · <span class="mini-profit profit-value" data-buy="{{ item.buy_order }}" data-sell="{{ item.sell_order }}">{{ "{:,.0f}".format(item.margin) }}c</span></span>
              </div>
            {% endfor %}
          </div>
          {% endif %}
        {% endfor %}
      </div>
    </details>
  {% endif %}

  <footer>Data refreshes on every page load · Source: Hypixel Bazaar API and SkyBlock item resources</footer>
</div>
<script>
  const mochaPoses = Array.from(document.querySelectorAll('.hero-mocha'));
  let mochaIndex = 0;
  if (mochaPoses.length > 1 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.setInterval(() => {
      mochaPoses[mochaIndex].classList.remove('active');
      mochaIndex = (mochaIndex + 1) % mochaPoses.length;
      mochaPoses[mochaIndex].classList.add('active');
    }, 3600);
  }

  const refreshCountdown = document.getElementById('refresh-countdown');
  let secondsUntilRefresh = 20;
  window.setInterval(() => {
    secondsUntilRefresh -= 1;
    if (secondsUntilRefresh <= 0) {
      window.location.reload();
      return;
    }
    refreshCountdown.textContent = secondsUntilRefresh;
  }, 1000);

  const taxToggle = document.getElementById('tax-toggle');
  const taxTier = document.getElementById('tax-tier');
  const profitValues = Array.from(document.querySelectorAll('.profit-value'));
  const profitLabels = Array.from(document.querySelectorAll('.profit-label'));
  const savedTaxEnabled = window.localStorage.getItem('bazaar-tax-enabled') === 'true';
  const savedTaxRate = window.localStorage.getItem('bazaar-tax-rate');

  taxToggle.checked = savedTaxEnabled;
  if (savedTaxRate && Array.from(taxTier.options).some(option => option.value === savedTaxRate)) {
    taxTier.value = savedTaxRate;
  }

  const formatCoins = value => `${Math.round(value).toLocaleString()}c`;

  function updateTaxedProfits() {
    const includeTax = taxToggle.checked;
    const taxRate = Number(taxTier.value);
    taxTier.disabled = !includeTax;

    profitLabels.forEach(label => {
      label.textContent = includeTax ? 'Net profit' : 'Gross profit';
    });

    profitValues.forEach(value => {
      const buyPrice = Number(value.dataset.buy);
      const sellPrice = Number(value.dataset.sell);
      const profit = includeTax
        ? (sellPrice * (1 - taxRate)) - buyPrice
        : sellPrice - buyPrice;
      value.textContent = formatCoins(profit);
      value.classList.toggle('loss', profit < 0);
    });

    window.localStorage.setItem('bazaar-tax-enabled', String(includeTax));
    window.localStorage.setItem('bazaar-tax-rate', taxTier.value);
  }

  taxToggle.addEventListener('change', updateTaxedProfits);
  taxTier.addEventListener('change', updateTaxedProfits);
  updateTaxedProfits();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    categories, top_20, error = build_tracker_results()
    return render_template_string(
        PAGE_TEMPLATE,
        categories=categories or {},
        top_20=top_20 or [],
        error=error,
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
