# --- requirements: playwright, requests ---
# 이 스크립트는 AA 달력에서 AUH-LHR / AUH-CDG 검색 후
# 페이지 내에 "A380" 텍스트가 보이면 텔레그램으로 알림을 보냅니다.
from playwright.sync_api import sync_playwright
import os, re, time, urllib.parse
import requests

ROUTES = [("AUH", "LHR"), ("AUH", "CDG")]   # 필요시 여기에 노선 추가
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

def notify(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def aa_search_url(origin, dest):
    # AA의 신규 검색 페이지 쿼리로 바로 진입(편도/마일/퍼스트)
    # 날짜는 오늘 기준으로 달력 보기가 열리도록 최소 파라미터만 사용
    q = {
        "tripType": "oneway",
        "from": origin,
        "to": dest,
        "adult": "1",
        "cabin": "FIRST",
        "award": "true"
    }
    return "https://www.aa.com/booking/find-flights?" + urllib.parse.urlencode(q)

def check_route(p, origin, dest):
    # 1) HTTP/2 비활성(플래그) + UA/헤더 고정
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-http2", "--no-sandbox"]
    )
    ctx = browser.new_context(
        locale="en-US",
        user_agent=UA,
        ignore_https_errors=True,
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    # 2) 이미지/폰트 차단(속도/안정성↑)
    ctx.route("**/*", lambda route: (
        route.abort()
        if route.request.resource_type in {"image", "font", "media"} else route.continue_()
    ))

    page = ctx.new_page()
    try:
        url = aa_search_url(origin, dest)
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_load_state("networkidle", timeout=90000)

        # 페이지 전체 HTML에서 A380 문자열 탐지(간단판)
        html = page.content()
        return ("A380" in html) or ("Airbus A380" in html) or ("A380-800" in html)

    except Exception as e:
        notify(f"[Etihad A380 Watch] {origin}-{dest} 체크 중 오류: {e}")
        return False
    finally:
        ctx.close(); browser.close()

def main():
    hits = []
    with sync_playwright() as p:
        for o, d in ROUTES:
            if check_route(p, o, d):
                hits.append(f"{o}-{d}")
            time.sleep(1.5)
    if hits:
        notify("✅ A380 First 보임: " + ", ".join(hits) + " (AA 검색 페이지)")
    else:
        print("No A380 F found this run.")

if __name__ == "__main__":
    main()
