import asyncio
import time

from rich import print


async def endpoint(route: str) -> str:
    print(f">> handling {route}")

    await asyncio.sleep(1)

    print(f"<< response {route}")

    return route


async def server():
    tests = {
        "GET /shipments?id=1",
        "PATCH /shipments?id=5",
        "GET /shipments?id=3",
    }

    start = time.perf_counter()

    requests = [asyncio.create_task(endpoint(route)) for route in tests]

    done, _ = await asyncio.wait(requests)

    for task in done:
        print("Result back:", task.result())

    end = time.perf_counter()

    print(f"Time taken: {end - start:.2f}s")


asyncio.run(server())
