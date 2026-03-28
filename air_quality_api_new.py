import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# AQICN_TOKEN = "e3f5c92f6396393875a96c47e0c94c136a60d2a7"
# AQICN_URL = f"https://api.waqi.info/feed/beijing/?token={AQICN_TOKEN}"


# SENDKEYS = [
#     "SCT329485T66hnPyfjKNHoPifFFuqPjJ7y" -- jason
#     "SCT329508TBq3StczVIH6VLTeg1pkppHPL",
#     "SCT329510TJicHH2eipWCDBe0Ee1gC7EiK"
# ]

AQICN_TOKEN = os.environ["AQICN_TOKEN"]
AQICN_URL = f"https://api.waqi.info/feed/beijing/?token={AQICN_TOKEN}"

SENDKEYS = [x.strip() for x in os.environ["SENDKEYS"].split(",") if x.strip()]
ALERT_THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", "125"))
ALERT_MARKER_DIR = ".alert_marker"
ALERT_MARKER_FILE = os.path.join(ALERT_MARKER_DIR, "sent.txt")


def send_wechat(message, title):
    results = []
    for key in SENDKEYS:
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {
            "title": title,
            "desp": message
        }
        resp = requests.post(url, data=data, timeout=20)
        resp.raise_for_status()
        try:
            results.append(resp.json())
        except Exception:
            results.append({"status_code": resp.status_code, "text": resp.text})
    return results

def get_beijing_now():
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def create_alert_marker(pm25_value: int):
    os.makedirs(ALERT_MARKER_DIR, exist_ok=True)
    beijing_now = get_beijing_now()
    with open(ALERT_MARKER_FILE, "w", encoding="utf-8") as f:
        f.write(
            f"date={beijing_now.strftime('%Y-%m-%d')}\n"
            f"time={beijing_now.strftime('%H:%M:%S')}\n"
            f"pm25={pm25_value}\n"
        )

###########
# 加一个“是否已发送”机制（用本地文件）
ALERT_FILE = "last_alert_date.txt"

def already_sent_today():
    file_path = os.path.abspath(ALERT_FILE)

    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return False

    with open(file_path, "r") as f:
        last_date = f.read().strip()

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"文件路径: {file_path}")
    print(f"文件中的日期: {last_date}, 今天日期: {today}")

    return last_date == today

def mark_sent_today():
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.abspath(ALERT_FILE)
    with open(file_path, "w") as f:
        f.write(today)
    print(f"已创建/更新文件: {file_path}")
###########
    

def get_aqi_level_info(aqi: int) -> dict:
    if 0 <= aqi <= 50:
        return {
            "color_cn": "绿色",
            "level_en": "Good",
            "level_cn": "良好",
            "health_implications": "空气质量令人满意，空气污染带来的风险很低或几乎没有。",
            "caution_statement": "无需特别防护，正常进行户外活动即可。"
        }
    elif 51 <= aqi <= 100:
        return {
            "color_cn": "黄色",
            "level_en": "Moderate",
            "level_cn": "中等",
            "health_implications": "空气质量总体可以接受，但对极少数对空气污染特别敏感的人群，可能存在中等程度的健康影响。",
            "caution_statement": "儿童、老年人，以及有呼吸系统疾病的人群，如哮喘患者，应减少长时间或高强度的户外活动。"
        }
    elif 101 <= aqi <= 150:
        return {
            "color_cn": "橙色",
            "level_en": "Unhealthy for Sensitive Groups",
            "level_cn": "对敏感人群不健康",
            "health_implications": "敏感人群可能受到健康影响，但普通人群通常暂时不会受到明显影响。",
            "caution_statement": "儿童、老年人、孕妇，以及患有心肺疾病的人群应减少长时间户外活动，其他人群可正常活动但应适度注意。"
        }
    elif 151 <= aqi <= 200:
        return {
            "color_cn": "红色",
            "level_en": "Unhealthy",
            "level_cn": "不健康",
            "health_implications": "所有人群都可能开始受到健康影响，敏感人群受到的影响可能更明显。",
            "caution_statement": "敏感人群应避免长时间或高强度户外活动，其他人群也应适当减少户外停留时间。"
        }
    elif 201 <= aqi <= 300:
        return {
            "color_cn": "紫色",
            "level_en": "Very Unhealthy",
            "level_cn": "非常不健康",
            "health_implications": "健康警报级别，所有人群都更有可能受到影响。",
            "caution_statement": "儿童、老年人，以及有呼吸系统疾病的人群，如哮喘患者，应避免所有户外活动；其他人群，尤其是儿童，也应尽量减少户外活动。"
        }
    else:
        return {
            "color_cn": "褐红色",
            "level_en": "Hazardous",
            "level_cn": "危险",
            "health_implications": "健康警报：所有人都可能出现更严重的健康影响。",
            "caution_statement": "所有人都应避免户外活动。"
        }


def get_color_emoji(color_cn: str) -> str:
    mapping = {
        "绿色": "🟢",
        "黄色": "🟡",
        "橙色": "🟠",
        "红色": "🔴",
        "紫色": "🟣",
        "褐红色": "🟤",
    }
    return mapping.get(color_cn, "⚪")


def get_mask_advice(pm25_aqi: int) -> str:
    if pm25_aqi <= 100:
        return "😄 一般无需佩戴口罩，可正常活动。"
    elif pm25_aqi <= 150:
        return "⚠️ 敏感人群建议佩戴口罩，尤其是老人、儿童及呼吸道疾病人群。"
    elif pm25_aqi <= 200:
        return "⚠️ 建议佩戴口罩，并减少户外停留时间。"
    else:
        return "🚨 强烈建议佩戴口罩，并尽量避免外出。"


def fetch_beijing_aqi() -> dict:
    resp = requests.get(AQICN_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise ValueError(f"API返回异常: {data}")

    payload = data["data"]

    pm25_aqi = payload.get("aqi")
    pm10_aqi = payload.get("iaqi", {}).get("pm10", {}).get("v")
    temp = payload.get("iaqi", {}).get("t", {}).get("v")
    humidity = payload.get("iaqi", {}).get("h", {}).get("v")
    wind = payload.get("iaqi", {}).get("w", {}).get("v")
    time_iso = payload.get("time", {}).get("iso")

    forecast_daily = payload.get("forecast", {}).get("daily", {})
    forecast_pm25 = forecast_daily.get("pm25", [])
    forecast_pm10 = forecast_daily.get("pm10", [])

    if pm25_aqi is None:
        raise ValueError("没有拿到 PM2.5 AQI")
    if pm10_aqi is None:
        raise ValueError("没有拿到 PM10 AQI")

    return {
        "pm25_aqi": int(round(pm25_aqi)),
        "pm10_aqi": int(round(pm10_aqi)),
        "temp": temp,
        "humidity": humidity,
        "wind": wind,
        "time_iso": time_iso,
        "forecast_pm25": forecast_pm25,
        "forecast_pm10": forecast_pm10,
    }


def format_datetime_chinese(time_iso: str | None) -> str:
    if not time_iso:
        now = datetime.now()
        return f"{now.month}月{now.day}日 {now.hour:02d}:{now.minute:02d}"
    
    dt = datetime.fromisoformat(time_iso)
    return f"{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}"


def format_short_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.month}月{dt.day}日"


def get_level_label(aqi: int) -> str:
    info = get_aqi_level_info(aqi)
    emoji = get_color_emoji(info["color_cn"])
    return f"{emoji}"


def get_next_3_days_forecast(aqi_data: dict) -> list:
    time_iso = aqi_data.get("time_iso")
    if time_iso:
        today = datetime.fromisoformat(time_iso).date()
    else:
        today = datetime.now().date()

    target_days = [(today + timedelta(days=i)).isoformat() for i in range(1, 4)]

    pm25_map = {item["day"]: item for item in aqi_data.get("forecast_pm25", [])}
    pm10_map = {item["day"]: item for item in aqi_data.get("forecast_pm10", [])}

    forecast_list = []
    for day in target_days:
        pm25_item = pm25_map.get(day)
        pm10_item = pm10_map.get(day)

        if pm25_item or pm10_item:
            forecast_list.append({
                "day": day,
                "pm25": pm25_item,
                "pm10": pm10_item,
            })

    return forecast_list


def build_forecast_section(aqi_data: dict) -> str:
    forecast_list = get_next_3_days_forecast(aqi_data)

    if not forecast_list:
        return "暂无未来三天预测数据"

    lines = []

    for item in forecast_list:
        day_text = format_short_date(item["day"])

        pm25 = item.get("pm25")
        pm10 = item.get("pm10")

        lines.append(f"\n**{day_text}**")

        if pm25:
            pm25_avg = int(round(pm25["avg"]))
            pm25_label = get_level_label(pm25_avg)
            lines.append(f"PM2.5：{pm25_avg}  （{pm25_label}）")

        if pm10:
            pm10_avg = int(round(pm10["avg"]))
            pm10_label = get_level_label(pm10_avg)
            lines.append(f"PM10：{pm10_avg}  （{pm10_label}）")

    return "\n".join(lines)


def build_message(aqi_data: dict) -> str:
    pm25_aqi = aqi_data["pm25_aqi"]
    pm10_aqi = aqi_data["pm10_aqi"]
    level_info = get_aqi_level_info(pm25_aqi)
    date_text = format_datetime_chinese(aqi_data.get("time_iso"))

    temp_text = f"{aqi_data['temp']}°C" if aqi_data.get("temp") is not None else "暂无"
    humidity_text = f"{aqi_data['humidity']}%" if aqi_data.get("humidity") is not None else "暂无"
    wind_text = f"{aqi_data['wind']}" if aqi_data.get("wind") is not None else "暂无"
    mask_advice = get_mask_advice(pm25_aqi)

    color_emoji = get_color_emoji(level_info["color_cn"])
    forecast_text = build_forecast_section(aqi_data)

    return f"""
### 🕒 实时监测：{date_text}

### 🔥 PM2.5 AQI：{pm25_aqi}

### 🌫️ PM10 AQI：{pm10_aqi}

### 📊 今日评级：{level_info['level_cn']}{color_emoji}

### 🌡️ 天气：{temp_text} | 💧 {humidity_text} | 💨 {wind_text}

---------------

🔹 **健康影响: **

{level_info['health_implications']}

🔹 **今日建议: **

{level_info['caution_statement']}

🔹 **口罩建议: **

{mask_advice}

---------------

🔹 **未来三天 PM2.5 / PM10 预测**
{forecast_text}

---------------

📊 **AQI 评级参考**

🟢 0–50：良好 -- 空气质量令人满意，可正常户外活动

🟡 51–100：中等 -- 敏感人群减少长时间户外活动

🟠 101–150：对敏感人群不健康 -- 老人、儿童、哮喘人群注意防护

🔴 151–200：不健康 -- 尽量减少户外活动，建议佩戴口罩

🟣 201–300：非常不健康 -- 避免户外活动，外出建议佩戴口罩

🟤 300+：危险 -- 所有人避免外出
""".strip()


def main():
    beijing_now = get_beijing_now()

    # 只在北京时间 05:00–21:59 之间运行
    if not (5 <= beijing_now.hour < 22):
        print("不在推送时间范围（北京时间 05:00–21:59），跳过。")
        return

    aqi_data = fetch_beijing_aqi()
    pm25 = aqi_data["pm25_aqi"]

    if pm25 < ALERT_THRESHOLD:
        print(f"PM2.5={pm25}，低于阈值 {ALERT_THRESHOLD}，不发送。")
        return

    title = f"北京PM2.5偏高提醒：{pm25}，出门建议佩戴口罩!（实时）"
    message = build_message(aqi_data)

    result = send_wechat(message=message, title=title)
    print("发送结果：", result)

    create_alert_marker(pm25)
    print(f"已创建当日预警标记：{ALERT_MARKER_FILE}")


if __name__ == "__main__":
    main()
