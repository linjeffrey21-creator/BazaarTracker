from pathlib import Path
from flask import Flask, render_template, request, send_from_directory
from bazaar import get_ranked_items

app = Flask(__name__)

## Tax choices (https://hypixel-skyblock.fandom.com/wiki/Bazaar)

tax_rates = {
    "default": 0.0125,
    "flipper_1": 0.01125,
    "flipper_2": 0.01
}

## Backgrounds

BACKGROUND_FOLDER = Path(__file__).parent / "static" / "backgrounds"
@app.route("/backgrounds/<path:filename>")
def serve_background(filename):
    return send_from_directory(BACKGROUND_FOLDER, filename)
    
background_credits = {
    "Japanese Station by the Sea.png":
        "Photo © 2022 Nicholas Smith",

    "Tromsø.JPG":
        "Photo: Vegard Stien / Visit Tromsø",

    "Polar Night in Norway.avif":
        "Photo: Kari Leibowitz / The Atlantic",

    "Yosemite Half-Dome Sunset.jpg":
        "Photo © Jack Brauer / WideRange Photo LLC",

    "Glacier Afternoon.jpg":
        "Photo: Courtney Childers / Travel + Leisure",

    "Pillars of Creation.jpg":
        "NASA, ESA, CSA, STScI, J. DePasquale (STScI), "
        "A. Pagan (STScI), A. M. Koekemoer (STScI)"
}


def get_backgrounds():
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

    backgrounds = [{
        "file": "none",
        "label": "No Background",
        "credit": "No photo background"
    }]

    if not BACKGROUND_FOLDER.exists():
        return backgrounds

    for file in BACKGROUND_FOLDER.iterdir():

        if file.suffix.lower() not in allowed:
            continue

        backgrounds.append({
            "file": file.name,
            "label": file.stem,
            "credit": background_credits.get(
                file.name,
                "Photo credit not added yet"
            )
        })

    return backgrounds


@app.route("/")
def home():
    search = request.args.get("search", "")
    tax_choice = request.args.get("tax", "default")
    use_omega = request.args.get("omega") == "on"

    ## Number of rows

    try:
        show_count = int(
            request.args.get("show", 20)
        )
    except ValueError:
        show_count = 20

    allowed_counts = {10, 20, 30, 50, 100}

    if show_count not in allowed_counts:
        show_count = 20


    ## Backgrounds

    backgrounds = get_backgrounds()

    files = [
        background["file"]
        for background in backgrounds
    ]

    default_background = "Japanese Station by the Sea.png"

    if default_background not in files:
        default_background = "none"

    background_choice = request.args.get(
        "background",
        default_background
    )

    if background_choice not in files:
        background_choice = default_background

    background_credit = "No photo background"

    for background in backgrounds:

        if background["file"] == background_choice:
            background_credit = background["credit"]
            break


    ## Bazaar taxes and sorting 

    tax_rate = tax_rates.get(
        tax_choice,
        0.0125
    )

    items = get_ranked_items(
        tax_rate=tax_rate,
        use_omega=use_omega,
        search=search
    )


    return render_template(
        "index.html",

        items=items[:show_count],

        search=search,

        tax_choice=tax_choice,

        use_omega=use_omega,

        show_count=show_count,

        backgrounds=backgrounds,

        background_choice=background_choice,

        background_credit=background_credit
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
