from flask import Flask, render_template, request

from bazaar import good_items, rank_items, search_items


app = Flask(__name__)


@app.route("/")
def home():
    search = request.args.get("search", "")
    use_omega = request.args.get("omega") == "on"

    items = rank_items(
        good_items,
        use_omega=use_omega
    )

    if search:
        items = search_items(items, search)

    return render_template(
        "index.html",
        items=items[:20],
        search=search,
        use_omega=use_omega
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)