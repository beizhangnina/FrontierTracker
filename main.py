#!/usr/bin/env python3
"""
Frontier Flight Tracker - 主程序

追踪 SFO/SJC ↔ LAS Frontier 航班价格
周二、周四发送邮件报告

使用方法:
    python main.py run [days]    # 运行追踪并发送邮件
    python main.py test          # 测试 API (搜索一天)
    python main.py email         # 发送测试邮件
    python main.py show          # 显示配置
    python main.py should-run    # 检查今天是否应该运行 (周二/周四)
    python main.py send-all      # 发送报告给所有已验证用户
"""
import sys
import logging
from datetime import datetime

from src.config import config, load_config
from src.amadeus_client import client
from src.emailer import emailer
from src.database import db
from src.auth import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def should_run_today() -> bool:
    """
    判断今天是否应该运行定时任务
    每周二 (1) 和周四 (3) 运行
    """
    return datetime.now().weekday() in [1, 3]  # 0=Mon, 1=Tue, ..., 6=Sun


def validate_config() -> bool:
    """验证配置是否完整"""
    missing = []

    if not config.amadeus_client_id or config.amadeus_client_id == "your_client_id_here":
        missing.append("AMADEUS_CLIENT_ID")
    if not config.amadeus_client_secret or config.amadeus_client_secret == "your_client_secret_here":
        missing.append("AMADEUS_CLIENT_SECRET")
    if not config.gmail_app_password or config.gmail_app_password == "your_app_password_here":
        missing.append("GMAIL_APP_PASSWORD")

    if missing:
        logger.error(f"配置缺失: {', '.join(missing)}")
        logger.error("请在 .env 文件中设置这些变量")
        return False

    return True


def cmd_test():
    """测试命令 - 只搜索一天"""
    logger.info("=== 测试模式 ===")

    from datetime import timedelta

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info(f"测试搜索: SFO → LAS, {tomorrow}")

    # 测试单日搜索 - 单程航班
    daily = client.get_daily_flights("SFO", "LAS", tomorrow)

    logger.info(f"找到 {len(daily.flights)} 个航班:")

    for flight in daily.flights[:5]:  # 只显示前 5 个
        logger.info(f"  {flight}")

    if daily.flights:
        logger.info("✓ API 测试成功")
    else:
        logger.warning("⚠ 没有找到航班，请检查日期或 API 配置")


def cmd_email():
    """发送测试邮件"""
    logger.info("=== 发送测试邮件 ===")

    if emailer.send_test_email():
        logger.info("✓ 测试邮件发送成功")
    else:
        logger.error("✗ 测试邮件发送失败")


def cmd_run(days: int = None):
    """运行完整追踪"""
    logger.info("=== Frontier Flight Tracker 开始 ===")

    if not validate_config():
        sys.exit(1)

    # 生成报告
    logger.info(f"获取接下来 {days or config.days_ahead} 天的航班...")
    report = client.generate_report(days_ahead=days)

    # 统计
    total_flights = len(report.get_all_flights())
    total_days = len(report.daily_flights)

    logger.info(f"找到 {total_flights} 个航班，覆盖 {total_days} 天")

    if total_flights == 0:
        logger.warning("没有找到任何航班，跳过邮件发送")
        return

    # 保存到数据库
    try:
        db.save_flights(report.get_all_flights())
        logger.info("价格数据已保存到数据库")
    except Exception as e:
        logger.warning(f"保存数据库失败: {e}")

    # 发送邮件
    logger.info("发送邮件报告...")
    if emailer.send_email(report):
        logger.info("✓ 邮件报告发送成功")
    else:
        logger.error("✗ 邮件报告发送失败")
        sys.exit(1)

    logger.info("=== 追踪完成 ===")


def cmd_send_all():
    """发送报告给所有已验证用户"""
    logger.info("=== 发送报告给所有用户 ===")

    if not validate_config():
        sys.exit(1)

    # 获取所有已验证用户
    conn = get_db_connection()
    cursor = conn.execute("SELECT email FROM users WHERE verified = 1")
    users = [row["email"] for row in cursor.fetchall()]
    conn.close()

    if not users:
        logger.info("没有已验证的用户")
        return

    logger.info(f"找到 {len(users)} 个已验证用户")

    # 生成报告
    report = client.generate_report(days_ahead=config.days_ahead)
    total_flights = len(report.get_all_flights())

    if total_flights == 0:
        logger.warning("没有找到航班")
        return

    logger.info(f"找到 {total_flights} 个航班")

    # 发送报告给每个用户
    success_count = 0
    for email in users:
        try:
            original_to_email = emailer.to_email
            emailer.to_email = email
            if emailer.send_email(report):
                success_count += 1
                logger.info(f"✓ 发送到 {email}")
            else:
                logger.warning(f"✗ 发送到 {email} 失败")
            emailer.to_email = original_to_email
        except Exception as e:
            logger.error(f"发送到 {email} 时出错: {e}")

    logger.info(f"=== 完成: 发送成功 {success_count}/{len(users)} ===")


def cmd_should_run():
    """检查今天是否应该运行"""
    if should_run_today():
        logger.info("✓ 今天应该运行 (周二或周四)")
        return 0
    else:
        logger.info("✗ 今天不运行 (非周二/周四)")
        return 1


def cmd_show():
    """显示配置信息（不显示敏感信息）"""
    print("=== Frontier Flight Tracker 配置 ===")
    routes_str = ", ".join([f"{orig}→{dest}" for orig, dest in config.routes])
    print(f"航线: {routes_str}")
    print(f"航空公司代码: {config.airline_code}")
    print(f"追踪天数: {config.days_ahead}")
    print(f"发送频率: 每周二、周四")
    print(f"发送到: {config.to_email}")
    print(f"价格阈值: ${config.price_threshold}")


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("Frontier Flight Tracker")
        print("用法:")
        print("  python main.py run [days]    - 运行追踪并发送邮件")
        print("  python main.py test          - 测试 API (搜索一天)")
        print("  python main.py email         - 发送测试邮件")
        print("  python main.py show          - 显示配置")
        print("  python main.py should-run    - 检查今天是否应该运行")
        print("  python main.py send-all      - 发送报告给所有用户")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "test":
        cmd_test()
    elif command == "email":
        cmd_email()
    elif command == "run":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cmd_run(days)
    elif command == "show":
        cmd_show()
    elif command == "should-run":
        sys.exit(cmd_should_run())
    elif command == "send-all":
        cmd_send_all()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
