"""
数据模型 - 航班价格数据结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class FlightPrice:
    """单个航班价格信息 - 单程航班"""

    date: str  # 出发日期 YYYY-MM-DD
    origin: str  # SFO/SJC/LAS
    destination: str  # LAS/SFO/SJC
    flight_number: str  # 航班号
    departure_time: str  # 出发时间 HH:MM
    arrival_time: str  # 到达时间 HH:MM
    duration: str  # 飞行时长，如 "1h 30m"
    is_nonstop: bool = True  # 是否直飞

    # 四个舱位价格
    basic_fare: Optional[float] = None
    economy_bundle: Optional[float] = None
    premium_bundle: Optional[float] = None
    business_bundle: Optional[float] = None

    def __str__(self) -> str:
        basic = f"${self.basic_fare}" if self.basic_fare else "N/A"
        econ = f"${self.economy_bundle}" if self.economy_bundle else "N/A"
        prem = f"${self.premium_bundle}" if self.premium_bundle else "N/A"
        bus = f"${self.business_bundle}" if self.business_bundle else "N/A"
        nonstop = "Nonstop" if self.is_nonstop else "Stop"
        return f"{self.date} {self.origin}→{self.destination} {self.departure_time}-{self.arrival_time} ({self.duration}) {nonstop}: Basic={basic}, Econ={econ}, Prem={prem}, Bus={bus}"


@dataclass
class DailyFlights:
    """某一天的所有航班"""
    date: str
    origin: str
    flights: List[FlightPrice] = field(default_factory=list)

    def add_flight(self, flight: FlightPrice):
        self.flights.append(flight)

    def get_lowest_prices(self) -> dict:
        """获取当天最低价格"""
        prices = {
            "basic_fare": float("inf"),
            "economy_bundle": float("inf"),
            "premium_bundle": float("inf"),
            "business_bundle": float("inf")
        }
        for flight in self.flights:
            if flight.basic_fare and flight.basic_fare < prices["basic_fare"]:
                prices["basic_fare"] = flight.basic_fare
            if flight.economy_bundle and flight.economy_bundle < prices["economy_bundle"]:
                prices["economy_bundle"] = flight.economy_bundle
            if flight.premium_bundle and flight.premium_bundle < prices["premium_bundle"]:
                prices["premium_bundle"] = flight.premium_bundle
            if flight.business_bundle and flight.business_bundle < prices["business_bundle"]:
                prices["business_bundle"] = flight.business_bundle
        return prices


@dataclass
class FlightReport:
    """航班报告 - 包含多天的数据"""
    report_date: datetime = field(default_factory=datetime.now)
    daily_flights: List[DailyFlights] = field(default_factory=list)

    def add_daily_flights(self, daily: DailyFlights):
        self.daily_flights.append(daily)

    def get_all_flights(self) -> List[FlightPrice]:
        """获取所有航班平铺列表"""
        all_flights = []
        for daily in self.daily_flights:
            all_flights.extend(daily.flights)
        return all_flights
