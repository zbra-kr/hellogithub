# collectors/weather.py - 날씨 정보 수집기 (wttr.in 무료 API 사용)

import requests
from datetime import datetime
from config import WEATHER_CITIES, REQUEST_TIMEOUT

# 날씨 코드 → 한국어 설명 매핑
WEATHER_DESC_KO = {
    113: "맑음", 116: "구름 조금", 119: "흐림", 122: "흐림",
    143: "안개", 176: "소나기", 179: "진눈깨비",
    182: "진눈깨비", 185: "어는 이슬비", 200: "천둥 번개",
    227: "눈 바람", 230: "눈 바람", 248: "안개", 260: "안개",
    263: "이슬비", 266: "이슬비", 281: "어는 이슬비",
    284: "어는 이슬비", 293: "가벼운 비", 296: "가벼운 비",
    299: "보통 비", 302: "보통 비", 305: "많은 비",
    308: "많은 비", 311: "어는 비", 314: "어는 비",
    317: "진눈깨비", 320: "가벼운 눈", 323: "가벼운 눈",
    326: "가벼운 눈", 329: "보통 눈", 332: "보통 눈",
    335: "많은 눈", 338: "많은 눈", 350: "진눈깨비",
    353: "가벼운 소나기", 356: "보통 소나기", 359: "많은 소나기",
    362: "진눈깨비 소나기", 365: "진눈깨비 소나기",
    368: "눈 소나기", 371: "많은 눈 소나기", 374: "진눈깨비",
    377: "진눈깨비", 386: "천둥 소나기", 389: "천둥 소나기",
    392: "천둥 눈", 395: "많은 눈",
}


def _wind_direction(degrees: int) -> str:
    """풍향 각도 → 한국어"""
    dirs = ["북", "북북동", "북동", "동북동", "동", "동남동",
            "남동", "남남동", "남", "남남서", "남서", "서남서",
            "서", "서북서", "북서", "북북서"]
    idx = round(degrees / 22.5) % 16
    return dirs[idx]


def collect_weather(log_callback=None) -> list[dict]:
    """
    wttr.in API를 통해 주요 도시 날씨를 수집합니다.

    Returns:
        list of dict: [{"도시", "현재기온", "체감기온", "최고기온", "최저기온",
                        "날씨상태", "습도", "풍속", "풍향", "수집시각"}, ...]
    """
    results = []

    for city_info in WEATHER_CITIES:
        city_name = city_info["name"]
        city_query = city_info["query"]

        if log_callback:
            log_callback(f"[날씨] {city_name} 수집 중...")

        try:
            url = f"https://wttr.in/{city_query}?format=j1&lang=ko"
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            current = data["current_condition"][0]
            weather_code = int(current.get("weatherCode", 0))
            weather_desc = WEATHER_DESC_KO.get(weather_code, current.get("weatherDesc", [{}])[0].get("value", "알 수 없음"))

            today = data["weather"][0] if data.get("weather") else {}

            results.append({
                "도시": city_name,
                "현재기온": f"{current.get('temp_C', '-')}°C",
                "체감기온": f"{current.get('FeelsLikeC', '-')}°C",
                "최고기온": f"{today.get('maxtempC', '-')}°C",
                "최저기온": f"{today.get('mintempC', '-')}°C",
                "날씨상태": weather_desc,
                "습도": f"{current.get('humidity', '-')}%",
                "풍속": f"{current.get('windspeedKmph', '-')} km/h",
                "풍향": _wind_direction(int(current.get("winddirDegree", 0))),
                "수집시각": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

            if log_callback:
                log_callback(f"[날씨] {city_name}: {weather_desc}, {current.get('temp_C', '-')}°C")

        except Exception as e:
            if log_callback:
                log_callback(f"[날씨] {city_name} 오류: {e}")
            results.append({
                "도시": city_name,
                "현재기온": "-",
                "체감기온": "-",
                "최고기온": "-",
                "최저기온": "-",
                "날씨상태": "수집 실패",
                "습도": "-",
                "풍속": "-",
                "풍향": "-",
                "수집시각": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

    return results
