import json
from typing import Any

shipments: dict[int, Any] = {}

with open("shipments.json") as json_file:
    data = json.load(json_file)  # In JSON, object keys must always be strings.

    for value in data:
        shipments[value["id"]] = value


def save():
    with open("shipments.json", "w") as json_file:
        json.dump(
            list(shipments.values()),
            json_file,
        )
