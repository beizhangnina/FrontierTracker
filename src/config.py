"""
配置管理 - 从环境变量读取配置
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass
class Config:
    """应用配置"""

    # Amadeus API
    amadeus_client_id: str
    amadeus_client_secret: str

    # Gmail
    gmail_user: str
    gmail_app_password: str
    to_email: str

    # 航班参数 - 支持双向航线
    # 格式: [(出发地, 目的地), ...]
    routes: list = None  # [("SFO", "LAS"), ("SJC", "LAS"), ("LAS", "SFO"), ("LAS", "SJC")]
    airline_code: str = "F9"  # Frontier
    days_ahead: int = 14  # 查询接下来 14 天

    # 价格阈值
    price_threshold: float = 50.0

    def __post_init__(self):
        if self.routes is None:
            # 双向航线: SFO/SJC ↔ LAS
            self.routes = [
                ("SFO", "LAS"),
                ("SJC", "LAS"),
                ("LAS", "SFO"),
                ("LAS", "SJC"),
            ]


def load_config() -> Config:
    """从环境变量加载配置"""
    return Config(
        amadeus_client_id=os.getenv("AMADEUS_CLIENT_ID", ""),
        amadeus_client_secret=os.getenv("AMADEUS_CLIENT_SECRET", ""),
        gmail_user=os.getenv("GMAIL_USER", "beizhangbill@gmail.com"),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        to_email=os.getenv("TO_EMAIL", "beizhangbill@gmail.com"),
        price_threshold=float(os.getenv("PRICE_THRESHOLD", "50")),
    )


# 全局配置实例
config = load_config()
