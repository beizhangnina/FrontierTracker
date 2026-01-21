"""
Amadeus API 客户端 - 获取 Frontier 航班价格
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from amadeus import Client, ResponseError
from src.config import config
from src.models import FlightPrice, DailyFlights, FlightReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmadeusFlightClient:
    """Amadeus API 客户端"""

    def __init__(self):
        """初始化 Amadeus 客户端"""
        try:
            self.client = Client(
                client_id=config.amadeus_client_id,
                client_secret=config.amadeus_client_secret
            )
            logger.info("Amadeus 客户端初始化成功")
        except Exception as e:
            logger.error(f"Amadeus 客户端初始化失败: {e}")
            raise

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
    ) -> List[dict]:
        """
        搜索单程航班

        Args:
            origin: 出发机场代码 (SFO, SJC, LAS)
            destination: 目的地机场代码 (LAS, SFO, SJC)
            departure_date: 出发日期 YYYY-MM-DD

        Returns:
            航班列表
        """
        try:
            # 构建请求参数
            # 注意: Amadeus API v2 使用 originLocationCode/destinationLocationCode
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": 1,  # 必需参数
                "max": 50,  # 最多返回 50 个结果
            }

            logger.info(f"搜索单程航班: {origin}→{destination}, {departure_date}")

            # 调用 Amadeus API
            response = self.client.shopping.flight_offers_search.get(**params)

            # 过滤出 Frontier 航班 (carrierCode = F9)
            all_offers = response.data
            frontier_offers = []
            for offer in all_offers:
                # 检查航班是否为 Frontier
                is_frontier = False
                itineraries = offer.get("itineraries", [])
                for itinerary in itineraries:
                    for segment in itinerary.get("segments", []):
                        if segment.get("carrierCode") == "F9":
                            is_frontier = True
                            break
                    if is_frontier:
                        break

                if is_frontier:
                    frontier_offers.append(offer)

            logger.info(f"找到 {len(all_offers)} 个航班，其中 {len(frontier_offers)} 个 Frontier 航班")
            return frontier_offers

        except ResponseError as e:
            logger.error(f"API 请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"搜索航班时出错: {e}")
            return []

    def _parse_duration(self, duration_str: str) -> str:
        """
        解析飞行时长格式
        Amadeus 返回格式: PT2H15M -> "2h 15m"
        """
        if not duration_str:
            return "N/A"
        # PT2H15M 或 PT1H30M 或 PT45M
        hours = 0
        minutes = 0
        import re
        h_match = re.search(r'(\d+)H', duration_str)
        m_match = re.search(r'(\d+)M', duration_str)
        if h_match:
            hours = int(h_match.group(1))
        if m_match:
            minutes = int(m_match.group(1))
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        elif minutes > 0:
            return f"{minutes}m"
        return "N/A"

    def _parse_fare_prices(self, offer: dict, flight: FlightPrice, base_price: float):
        """
        解析4个舱位价格

        Frontier 官网价格档位:
        - Basic Fare (无手提行李)
        - Economy Bundle (个人物品+手提行李)
        - Premium Bundle (更多腿距，优先登机)
        - Business Bundle (商务舱)
        """
        # 使用典型比例估算
        # 基于 Frontier 官网的大致价格比例
        if base_price > 0:
            # 使用返回的总价作为 Economy 价格（最常见）
            flight.economy_bundle = round(base_price, 2)
            flight.basic_fare = round(base_price * 0.82, 2)
            flight.premium_bundle = round(base_price * 1.5, 2)
            flight.business_bundle = round(base_price * 2.2, 2)

    def parse_flight_offer(self, offer: dict, origin: str, destination: str) -> List[FlightPrice]:
        """
        解析 Amadeus 返回的航班报价 - 单程航班

        Args:
            offer: Amadeus 返回的单个报价
            origin: 出发地
            destination: 目的地

        Returns:
            FlightPrice 对象列表
        """
        flights = []

        try:
            # Amadeus API v2 返回格式
            itineraries = offer.get("itineraries", [])

            if not itineraries:
                return flights

            # 获取去程航班（单程只有一个 itinerary）
            outbound = itineraries[0]
            segments = outbound.get("segments", [])

            if not segments:
                return flights

            # 判断是否直飞
            is_nonstop = len(segments) == 1

            # 获取第一个航班段
            first_segment = segments[0]
            departure_at = first_segment.get("departure", {}).get("at", "")
            carrier_code = first_segment.get("carrierCode", "")
            flight_num = first_segment.get("number", "")
            flight_number = f"{carrier_code}{flight_num}"

            # 获取最后一个航班段的到达时间（可能不是第一段，如果有中转）
            last_segment = segments[-1]
            arrival_at = last_segment.get("arrival", {}).get("at", "")

            # 解析日期和时间
            if not departure_at:
                return flights

            departure_date = departure_at.split("T")[0]
            departure_time = departure_at.split("T")[1][:5] if "T" in departure_at else ""
            arrival_time = arrival_at.split("T")[1][:5] if "T" in arrival_at else ""

            # 解析飞行时长
            duration = self._parse_duration(outbound.get("duration", ""))

            # 初始化价格对象 - 4个舱位
            flight_price = FlightPrice(
                date=departure_date,
                origin=origin,
                destination=destination,
                flight_number=flight_number,
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration=duration,
                is_nonstop=is_nonstop,
            )

            # 解析价格
            price = offer.get("price", {})
            total_price = float(price.get("total", 0))
            self._parse_fare_prices(offer, flight_price, total_price)

            flights.append(flight_price)

        except Exception as e:
            logger.error(f"解析航班报价时出错: {e}")

        return flights

    def get_daily_flights(
        self,
        origin: str,
        destination: str,
        date: str,
    ) -> DailyFlights:
        """获取指定日期的所有单程航班"""
        daily = DailyFlights(date=date, origin=origin)

        # 搜索单程航班
        offers = self.search_flights(
            origin=origin,
            destination=destination,
            departure_date=date,
        )

        # 解析报价
        seen_flights = set()  # 去重
        for offer in offers:
            flights = self.parse_flight_offer(offer, origin, destination)
            for flight in flights:
                # 使用航班号+出发时间作为唯一标识
                key = f"{flight.flight_number}_{flight.departure_time}"
                if key not in seen_flights:
                    daily.add_flight(flight)
                    seen_flights.add(key)

        logger.info(f"{origin}→{destination} {date}: 找到 {len(daily.flights)} 个航班")
        return daily

    def generate_report(
        self,
        days_ahead: int = None,
    ) -> FlightReport:
        """
        生成航班报告 - 接下来 N 天的单程航班

        Args:
            days_ahead: 向前查看多少天

        Returns:
            FlightReport 对象
        """
        if days_ahead is None:
            days_ahead = config.days_ahead

        report = FlightReport()

        # 生成日期列表
        today = datetime.now().date()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days_ahead + 1)]

        # 对每条航线和日期进行搜索
        for origin, destination in config.routes:
            for departure_date in dates:
                # 获取单程航班
                daily = self.get_daily_flights(origin, destination, departure_date)
                if daily.flights:
                    report.add_daily_flights(daily)

        logger.info(f"报告生成完成: 共 {len(report.daily_flights)} 天的数据")
        return report


# 全局客户端实例
client = AmadeusFlightClient()
