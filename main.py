# --- requirements: playwright, requests ---
# 이 스크립트는 AA 달력에서 AUH-LHR / AUH-CDG 검색 후
# 페이지 내에 "A380" 텍스트가 보이면 텔레그램으로 알림을 보냅니다.
import os, re, time
import requests
from playwright.sync_api import sync_playwright

ROUTES = [("AUH", "LHR"), ("AUH", "CDG")]   # 필요시 여기에 노선 추가
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def notify(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def check_route(p, origin, dest):
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()
    try:
        page.goto("https://www.aa.com/", timeout=60000)
        # 마일 사용 체크
        page.get_by_label(re.compile("Redeem miles", re.I)).check()
        # 출발/도착
        page.get_by_label(re.compile("^From", re.I)).fill(origin)
        page.get_by_role("option").filter(has_text=origin).first.click()
        page.get_by_label(re.compile("^To", re.I)).fill(dest)
        page.get_by_role("option").filter(has_text=dest).first.click()
        # 캐빈: First
        page.get_by_label(re.compile("Cabin", re.I)).click()
        page.get_by_role("option", name=re.compile("First", re.I)).click()
        # 날짜: Flexible(달력)
        page.get_by_label(re.compile("Dates", re.I)).click()
        page.get_by_role("button", name=re.compile("Flexible", re.I)).click()
        # 임의 기준일: 오늘로 검색
        page.get_by_role("button", name=re.compile("Search", re.I)).click()
        page.wait_for_load_state("networkidle", timeout=60000)

        # 페이지 텍스트에 A380 포함 여부 검사 (간단판)
        text = page.content()
        found = ("A380" in text) or ("Airbus A380" in text) or ("A380-800" in text)

        return found
    except Exception as e:
        notify(f"[Etihad A380 Watch] {origin}-{dest} 체크 중 오류: {e}")
        return False
    finally:
        ctx.close(); browser.close()

def main():
    any_found = []
    with sync_playwright() as p:
        for (o, d) in ROUTES:
            ok = check_route(p, o, d)
            if ok:
                any_found.append(f"{o}-{d}")
            time.sleep(2)  # 사이트 부하 방지

    if any_found:
        notify(f"✅ A380 First 보임: {', '.join(any_found)} (AA 달력 기준)")
    else:
        # 조용히 지나가도 되지만 최초엔 동작 확인용으로 남깁니다.
        print("No A380 F found this run.")

if __name__ == "__main__":
    main()
