import sqlite3
from typing import Any

from app.schemas import ShipmentCreate, ShipmentUpdate


class Database:
    def __init__(self) -> None:
        # Make connection with database
        self.conn = sqlite3.connect("sqlite.db", check_same_thread=False)
        # Get cursor to execute queries and fetch data
        self.cur = self.conn.cursor()
        # Create table if not exists
        self.create_table()

    def create_table(self):
        # 1. Create a table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS shipment (
                id INTEGER PRIMARY KEY,
                content TEXT,
                weight REAL,
                destination INTEGER,
                status TEXT
            )
        """)

    def create(self, shipment: ShipmentCreate) -> int:
        # Find a new id
        self.cur.execute("SELECT MAX(id) FROM shipment ")
        result = self.cur.fetchone()

        if result[0] is None:
            new_id = 0
        else:
            new_id = result[0] + 1

        self.cur.execute(
            """
            INSERT INTO shipment
            VALUES (:id, :content, :weight, :destination, :status)
        """,
            {
                "id": new_id,
                **shipment.model_dump(),
                "status": "placed",
            },
        )

        self.conn.commit()

        return new_id

    def get(self, id: int) -> dict[str, Any] | None:
        self.cur.execute(
            """
            SELECT * FROM shipment
            WHERE id=?
        """,
            (id,),
        )

        row = self.cur.fetchone()

        return (
            {
                "id": row[0],
                "content": row[1],
                "weight": row[2],
                "destination": row[3],
                "status": row[4],
            }
            if row
            else None
        )

    def update(self, id: int, shipment: ShipmentUpdate) -> dict[str, Any] | None:
        self.cur.execute(
            """
            UPDATE shipment SET status = :status
            WHERE id = :id
        """,
            {
                "id": id,
                **shipment.model_dump(),
            },
        )

        self.conn.commit()

        return self.get(id)

    def delete(self, id: int):
        self.cur.execute(
            """
            DELETE FROM shipment
            WHERE id=?
        """,
            (id,),
        )

        self.conn.commit()

    def close(self):
        self.conn.close()
