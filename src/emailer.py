"""
邮件发送模块 - 发送航班价格报告
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from jinja2 import Template
from src.config import config
from src.models import FlightReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlightEmailer:
    """航班报告邮件发送器"""

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def _load_template(self) -> Template:
        """加载邮件模板 - 单程航班格式"""
        template_html = """<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; font-size: 13px; color: #333; }
        h1 { color: #1a365d; }
        h2 { color: #2d3748; margin-top: 20px; font-size: 16px; }
        .timestamp { color: #718096; font-size: 12px; }
        table { border-collapse: collapse; width: 100%; margin-top: 15px; font-size: 12px; }
        th { background-color: #1a365d; color: white; padding: 8px; text-align: left; font-size: 11px; }
        td { padding: 6px 8px; border-bottom: 1px solid #e2e8f0; }
        tr:nth-child(even) { background-color: #f7fafc; }
        .best-price { background-color: #c6f6d5 !important; font-weight: bold; }
        .route-sfo { color: #1a365d; font-weight: bold; }
        .route-sjc { color: #744210; font-weight: bold; }
        .route-las { color: #9b2c2c; font-weight: bold; }
        .price { font-family: monospace; font-weight: bold; }
        .price-low { color: #276749; }
        .price-mid { color: #744210; }
        .price-high { color: #9b2c2c; }
        .nonstop-badge { background-color: #276749; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
        .stop-badge { background-color: #9b2c2c; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
        .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px; }
        .gowild-link { background-color: #ed8936; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 15px; }
        .gowild-link:hover { background-color: #dd6b20; }
        .section-title { color: #1a365d; border-bottom: 2px solid #ed8936; padding-bottom: 5px; margin-top: 25px; }
    </style>
</head>
<body>
    <h1>✈️ Frontier Flight Report (One-Way)</h1>
    <p class="timestamp">Generated: {{ timestamp }}</p>

    <a href="https://www.flyfrontier.com/go-wild" class="gowild-link">🎯 Check GoWild! Pass</a>

    {# Bay Area to Las Vegas #}
    {% for route_data in by_route %}
    {% if route_data.direction == "outbound" %}
    <h2 class="section-title">{{ route_data.route }}</h2>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Flight</th>
                <th>Depart</th>
                <th>Arrive</th>
                <th>Duration</th>
                <th>Nonstop?</th>
                <th>Basic</th>
                <th>Economy</th>
                <th>Premium</th>
                <th>Business</th>
            </tr>
        </thead>
        <tbody>
            {% for flight in route_data.flights %}
            <tr {% if flight.is_best_price %}class="best-price"{% endif %}>
                <td>{{ flight.date_display }}</td>
                <td class="route-{{ flight.origin.lower() }}">{{ flight.flight_number }}</td>
                <td>{{ flight.departure_time }}</td>
                <td>{{ flight.arrival_time }}</td>
                <td>{{ flight.duration }}</td>
                <td>{% if flight.is_nonstop %}<span class="nonstop-badge">Yes</span>{% else %}<span class="stop-badge">No</span>{% endif %}</td>
                <td class="price {% if flight.basic_fare <= 50 %}price-low{% elif flight.basic_fare <= 100 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.basic_fare }}
                </td>
                <td class="price {% if flight.economy_bundle <= 70 %}price-low{% elif flight.economy_bundle <= 120 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.economy_bundle }}
                </td>
                <td class="price {% if flight.premium_bundle <= 120 %}price-low{% elif flight.premium_bundle <= 180 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.premium_bundle }}
                </td>
                <td class="price {% if flight.business_bundle <= 200 %}price-low{% elif flight.business_bundle <= 300 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.business_bundle }}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}
    {% endfor %}

    {# Las Vegas to Bay Area #}
    {% for route_data in by_route %}
    {% if route_data.direction == "return" %}
    <h2 class="section-title">{{ route_data.route }}</h2>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Flight</th>
                <th>Depart</th>
                <th>Arrive</th>
                <th>Duration</th>
                <th>Nonstop?</th>
                <th>Basic</th>
                <th>Economy</th>
                <th>Premium</th>
                <th>Business</th>
            </tr>
        </thead>
        <tbody>
            {% for flight in route_data.flights %}
            <tr {% if flight.is_best_price %}class="best-price"{% endif %}>
                <td>{{ flight.date_display }}</td>
                <td class="route-{{ flight.origin.lower() }}">{{ flight.flight_number }}</td>
                <td>{{ flight.departure_time }}</td>
                <td>{{ flight.arrival_time }}</td>
                <td>{{ flight.duration }}</td>
                <td>{% if flight.is_nonstop %}<span class="nonstop-badge">Yes</span>{% else %}<span class="stop-badge">No</span>{% endif %}</td>
                <td class="price {% if flight.basic_fare <= 50 %}price-low{% elif flight.basic_fare <= 100 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.basic_fare }}
                </td>
                <td class="price {% if flight.economy_bundle <= 70 %}price-low{% elif flight.economy_bundle <= 120 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.economy_bundle }}
                </td>
                <td class="price {% if flight.premium_bundle <= 120 %}price-low{% elif flight.premium_bundle <= 180 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.premium_bundle }}
                </td>
                <td class="price {% if flight.business_bundle <= 200 %}price-low{% elif flight.business_bundle <= 300 %}price-mid{% else %}price-high{% endif %}">
                    ${{ flight.business_bundle }}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}
    {% endfor %}

    <div class="footer">
        <p>🔷 <strong>Basic Fare:</strong> No carry-on bag, personal item only</p>
        <p>🔶 <strong>Economy Bundle:</strong> Personal item + carry-on bag</p>
        <p>🔸 <strong>Premium Bundle:</strong> Extra legroom, priority boarding</p>
        <p>💎 <strong>Business Bundle:</strong> Business class, full-service</p>
        <p style="margin-top: 15px;">Prices are estimates based on available fares. Check Frontier.com for final pricing.</p>
    </div>
</body>
</html>"""
        return Template(template_html)

    def _prepare_report_data(self, report: FlightReport) -> dict:
        """准备模板数据 - 单程航班格式"""
        # 按航线分组 (origin, destination)
        by_route = {}
        all_prices = []  # 用于计算最低价格

        for daily in report.daily_flights:
            origin = daily.origin
            for flight in daily.flights:
                # 航线标识: "SFO→LAS" 或 "LAS→SFO"
                route_key = f"{flight.origin}→{flight.destination}"
                if route_key not in by_route:
                    by_route[route_key] = []

                # 判断方向： outbound (Bay Area -> LAS) 或 return (LAS -> Bay Area)
                direction = "outbound" if flight.origin in ["SFO", "SJC"] else "return"

                # 格式化显示 - 单程航班
                flight_data = {
                    "date_display": self._format_date(flight.date),
                    "date": flight.date,
                    "origin": flight.origin,
                    "destination": flight.destination,
                    "route": route_key,
                    "flight_number": flight.flight_number,
                    "departure_time": flight.departure_time,
                    "arrival_time": flight.arrival_time,
                    "duration": flight.duration,
                    "is_nonstop": flight.is_nonstop,
                    "basic_fare": int(flight.basic_fare) if flight.basic_fare else "N/A",
                    "economy_bundle": int(flight.economy_bundle) if flight.economy_bundle else "N/A",
                    "premium_bundle": int(flight.premium_bundle) if flight.premium_bundle else "N/A",
                    "business_bundle": int(flight.business_bundle) if flight.business_bundle else "N/A",
                    "is_best_price": False,
                    "direction": direction,
                }

                by_route[route_key].append(flight_data)
                if flight.economy_bundle:
                    all_prices.append(flight.economy_bundle)

        # 计算最低价格并标记
        if all_prices:
            lowest_price = min(all_prices)
            for route_flights in by_route.values():
                for flight in route_flights:
                    if isinstance(flight["economy_bundle"], (int, float)) and flight["economy_bundle"] <= lowest_price * 1.1:
                        flight["is_best_price"] = True

        # 按日期排序
        for route in by_route:
            by_route[route].sort(key=lambda x: x["date"])

        # 转换为列表格式，按航线顺序排列
        # outbound routes first, then return routes
        route_order = ["SFO→LAS", "SJC→LAS", "LAS→SFO", "LAS→SJC"]
        by_route_list = []
        for route in route_order:
            if route in by_route:
                direction = "outbound" if route.startswith(("SFO", "SJC")) else "return"
                by_route_list.append({
                    "route": route,
                    "flights": by_route[route],
                    "direction": direction
                })

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "by_route": by_route_list,
        }

    def _format_date(self, date_str: str) -> str:
        """格式化日期显示"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%a %m/%d")  # Mon 01/21
        except:
            return date_str

    def send_email(self, report: FlightReport) -> bool:
        """
        发送航班报告邮件

        Args:
            report: FlightReport 对象

        Returns:
            是否发送成功
        """
        try:
            # 准备模板数据
            template_data = self._prepare_report_data(report)

            # 渲染 HTML
            template = self._load_template()
            html_content = template.render(**template_data)

            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Frontier Flight Report - {datetime.now().strftime('%Y-%m-%d')}"
            msg["From"] = config.gmail_user
            msg["To"] = config.to_email

            # 添加 HTML 内容
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # 发送邮件
            logger.info(f"发送邮件到 {config.to_email}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(config.gmail_user, config.gmail_app_password)
                server.send_message(msg)

            logger.info("邮件发送成功")
            return True

        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False

    def send_test_email(self) -> bool:
        """发送测试邮件"""
        try:
            msg = MIMEMultipart()
            msg["Subject"] = "Frontier Tracker - Test Email"
            msg["From"] = config.gmail_user
            msg["To"] = config.to_email

            html = """
            <html>
            <body>
                <h2>✅ Frontier Flight Tracker Test</h2>
                <p>Your email configuration is working correctly!</p>
                <p>You will receive daily flight reports at 8:00 AM PST.</p>
                <hr>
                <p><small>SFO/SJC ↔ LAS - Frontier Airlines only</small></p>
            </body>
            </html>
            """

            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(config.gmail_user, config.gmail_app_password)
                server.send_message(msg)

            logger.info("测试邮件发送成功")
            return True

        except Exception as e:
            logger.error(f"测试邮件发送失败: {e}")
            return False


# 全局邮件发送器实例
emailer = FlightEmailer()
