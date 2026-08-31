from collections.abc import Callable
from pprint import pprint
from typing import Any

number = 2


def power(num: int, exp: float | None = None) -> float:
    return pow(num, 0.5 if exp is None else exp)


class City:
    def __init__(self, name, location):
        self.name = name
        self.location = location

print(power(2))
pprint(power(2))

digits: list[int] = [1, 2, 3, 4, 5]

table_5: tuple[int, ...] = (1, 2, 3, 4, 5)

city_temp: tuple[City, int] = (City("Chennai", 60028), 24)

shipment: dict[str, Any] = {
    "id": 3,
    "content": "wooden table",
    "status": "in transit",
}


def custom_fence(fence: str = "+"):
    def add_fence(func: Callable):
        def wrapper():
            print(fence * 10)
            func()
            print(fence * 10)
        return wrapper
    return add_fence

@custom_fence("=")
def log():
    print("Logged!")

log()