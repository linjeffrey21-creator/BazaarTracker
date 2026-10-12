# Bazaar Tracker

Bazaar Tracker is a live Hypixel SkyBlock Bazaar tracker that helps find strong flips across the market.

It uses custom metrics I developed:
1. **Gamma** measures opportunity using profit and market activity.
2. **Omega** measures stability and can optionally be factored into rankings.

## Features

- Pulls live Hypixel Bazaar data from the API
- Search by item
- Tax settings because the Bazaar taxes transactions
- Gamma and Omega rankings
- Item icons
- Adjustable number of results
- Background picker

## To run this locally

1. First, download or clone this repository:

   `git clone https://github.com/linjeffrey21-creator/BazaarTracker.git`

   `cd BazaarTracker`

2. Install the requirements:

   `pip install -r requirements.txt`

3. Extract the item icons:

   `python -m zipfile -e static/item_icons.zip static`

4. Run the app:

   `python3 app.py`

5. Open:

   `http://localhost:5050`

## Live Demo

https://bazaar-tracker-ten.vercel.app/
