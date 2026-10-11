import requests
import zipfile
import io
import json
import hashlib
from pathlib import Path


PACKS_URL = "https://api.hypixel.net/v2/resources/packs"
ITEMS_URL = "https://api.hypixel.net/v2/resources/skyblock/items"

ICON_FOLDER = Path("static/item_icons")
ICON_FOLDER.mkdir(parents=True, exist_ok=True)


## Get current SkyBlock resource pack !

def get_skyblock_pack():
    response = requests.get(
        PACKS_URL,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    for pack in data["packs"]:

        if pack["id"].lower() == "skyblock":

            # Use newest available pack format
            version = max(
                pack["versions"],
                key=lambda version: version["packFormat"]
            )

            return version

    raise Exception("Couldn't find SkyBlock resource pack.")


## Get SkyBlock items !

def get_items():
    response = requests.get(
        ITEMS_URL,
        timeout=20
    )

    response.raise_for_status()

    return response.json()["items"]


## Turn a Minecraft texture reference into its file path !

def texture_file(texture_reference):

    if ":" in texture_reference:
        namespace, path = texture_reference.split(":", 1)

    else:
        namespace = "minecraft"
        path = texture_reference

    return (
        f"assets/{namespace}/textures/"
        f"{path}.png"
    )


## Look inside a model JSON for its texture !

def find_model_texture(pack, model_reference, already_checked=None):

    if already_checked is None:
        already_checked = set()

    if model_reference in already_checked:
        return None

    already_checked.add(model_reference)


    if ":" in model_reference:
        namespace, path = model_reference.split(":", 1)

    else:
        namespace = "minecraft"
        path = model_reference


    model_file = (
        f"assets/{namespace}/models/"
        f"{path}.json"
    )


    if model_file not in pack.namelist():
        return None


    try:
        model_data = json.loads(
            pack.read(model_file)
        )

    except:
        return None


    textures = model_data.get(
        "textures",
        {}
    )


    # layer0 is normally the main inventory texture
    preferred = [
        "layer0",
        "all",
        "texture",
        "particle"
    ]


    for key in preferred:

        reference = textures.get(key)

        if (
            reference
            and isinstance(reference, str)
            and not reference.startswith("#")
        ):

            file_name = texture_file(reference)

            if file_name in pack.namelist():
                return file_name


    # Try any other texture if layer0 wasn't available

    for reference in textures.values():

        if (
            isinstance(reference, str)
            and not reference.startswith("#")
        ):

            file_name = texture_file(reference)

            if file_name in pack.namelist():
                return file_name


    # Some models inherit their texture from another model

    parent = model_data.get("parent")

    if parent:
        return find_model_texture(
            pack,
            parent,
            already_checked
        )

    return None


## Try to locate the item's official texture !

def find_item_texture(pack, item_model):

    if not item_model:
        return None


    if ":" in item_model:
        namespace, path = item_model.split(":", 1)

    else:
        namespace = "minecraft"
        path = item_model


    # Most Hypixel items have the texture at the same path
    direct_texture = (
        f"assets/{namespace}/textures/"
        f"{path}.png"
    )

    if direct_texture in pack.namelist():
        return direct_texture


    # If not, try resolving its model JSON
    return find_model_texture(
        pack,
        item_model
    )


## Build the actual icon folder !

def build_icons():

    print("Finding current SkyBlock resource pack...")

    version = get_skyblock_pack()

    print(
        "Downloading pack format",
        version["packFormat"]
    )

    response = requests.get(
        version["url"],
        timeout=60
    )

    response.raise_for_status()


    ## Make sure download wasn't corrupted

    real_hash = hashlib.sha1(
        response.content
    ).hexdigest()

    expected_hash = version["hash"]

    if real_hash != expected_hash:
        raise Exception(
            "Resource pack hash did not match!"
        )


    print("Resource pack downloaded correctly.")


    pack = zipfile.ZipFile(
        io.BytesIO(response.content)
    )


    items = get_items()

    found = 0
    missing = 0


    for item in items:

        item_id = item.get("id")
        item_model = item.get("item_model")

        if not item_id or not item_model:
            continue


        texture = find_item_texture(
            pack,
            item_model
        )


        if texture is None:
            missing += 1
            continue


        output = (
            ICON_FOLDER
            / f"{item_id}.png"
        )


        output.write_bytes(
            pack.read(texture)
        )

        found += 1


    ## Keep Hypixel's license with the assets

    if "LICENSE" in pack.namelist():

        Path(
            "static/item_icons/LICENSE"
        ).write_bytes(
            pack.read("LICENSE")
        )


    print()
    print("Done!")
    print("Official icons found:", found)
    print("Models without simple icons:", missing)
    print("Saved to:", ICON_FOLDER)


if __name__ == "__main__":
    build_icons()
