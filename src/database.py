"""
数据库管理 - SQLite 存储价格历史
"""
import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from src.models import FlightPrice
from src.config import config


class FlightDatabase:
    """航班价格数据库 - 单程航班"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # 确保 data 目录存在
            os.makedirs("data", exist_ok=True)
            db_path = "data/flights.db"
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flight_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    flight_number TEXT,
                    departure_time TEXT,
                    arrival_time TEXT,
                    duration TEXT,
                    is_nonstop INTEGER DEFAULT 1,
                    basic_fare REAL,
                    economy_bundle REAL,
                    premium_bundle REAL,
                    business_bundle REAL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_date_origin
                ON flight_prices(date, origin)
            """)
            conn.commit()

    def save_flight(self, flight: FlightPrice):
        """保存单个航班价格"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO flight_prices
                (date, origin, destination, flight_number, departure_time, arrival_time, duration, is_nonstop,
                 basic_fare, economy_bundle, premium_bundle, business_bundle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flight.date,
                flight.origin,
                flight.destination,
                flight.flight_number,
                flight.departure_time,
                flight.arrival_time,
                flight.duration,
                1 if flight.is_nonstop else 0,
                flight.basic_fare,
                flight.economy_bundle,
                flight.premium_bundle,
                flight.business_bundle,
            ))
            conn.commit()

    def save_flights(self, flights: List[FlightPrice]):
        """批量保存航班价格"""
        with self.get_connection() as conn:
            for flight in flights:
                conn.execute("""
                    INSERT OR REPLACE INTO flight_prices
                    (date, origin, destination, flight_number, departure_time, arrival_time, duration, is_nonstop,
                     basic_fare, economy_bundle, premium_bundle, business_bundle)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    flight.date,
                    flight.origin,
                    flight.destination,
                    flight.flight_number,
                    flight.departure_time,
                    flight.arrival_time,
                    flight.duration,
                    1 if flight.is_nonstop else 0,
                    flight.basic_fare,
                    flight.economy_bundle,
                    flight.premium_bundle,
                    flight.business_bundle,
                ))
            conn.commit()

    def get_price_history(self, origin: str, date: str, days: int = 7) -> List[dict]:
        """获取某个航班的价格历史"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM flight_prices
                WHERE origin = ? AND date = ?
                ORDER BY scraped_at DESC
                LIMIT ?
            """, (origin, date, days))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_prices(self, origin: str, start_date: str, end_date: str) -> List[dict]:
        """获取指定日期范围内最新价格"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM flight_prices
                WHERE origin = ? AND date BETWEEN ? AND ?
                AND scraped_at = (
                    SELECT MAX(scraped_at)
                    FROM flight_prices f2
                    WHERE f2.date = flight_prices.date
                    AND f2.origin = flight_prices.origin
                    AND f2.flight_number = flight_prices.flight_number
                )
                ORDER BY date, departure_time
            """, (origin, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]


# 全局数据库实例
db = FlightDatabase()
