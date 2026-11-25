#!/usr/bin/env python3
"""从老版正方教务系统抓取学生课表，输出 courses.json。

凭据只从环境变量读取（JW_USER / JW_PASSWORD），不写入代码、不打印、不提交。
缺少任一凭据时脚本以 0 退出并保留现有 courses.json —— 这样 Actions 不会因
未配置 Secrets 而每天失败，用户本地跑也不会破坏数据。

桂林理工的登录路径是 /academic/affairLogin.do，课表接口路径未公开确认，
因此路径全部可由环境变量覆盖，便于实测后调整，不必改代码。
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("JW_BASE_URL", "https://jw.glut.edu.cn").rstrip("/")
LOGIN_PATH = os.environ.get("JW_LOGIN_PATH", "/academic/affairLogin.do")
USER = os.environ.get("JW_USER", "").strip()
PASSWORD = os.environ.get("JW_PASSWORD", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "courses.json")
OUTPUT_JS = os.path.join(ROOT, "courses.js")
PERIODS = [
    {"n": 1, "start": "08:30", "end": "09:15"},
    {"n": 2, "start": "09:20", "end": "10:05"},
    {"n": 3, "start": "10:25", "end": "11:10"},
    {"n": 4, "start": "11:15", "end": "12:00"},
    {"n": 5, "start": "14:30", "end": "15:15"},
    {"n": 6, "start": "15:20", "end": "16:05"},
    {"n": 7, "start": "16:25", "end": "17:10"},
    {"n": 8, "start": "17:15", "end": "18:00"},
    {"n": 9, "start": "18:30", "end": "19:15"},
    {"n": 10, "start": "19:20", "end": "20:05"},
    {"n": 11, "start": "20:15", "end": "21:00"},
    {"n": 12, "start": "21:05", "end": "21:50"},
]


def log(msg):
    # 不打印任何凭据相关内容
    print("[fetch_schedule] " + str(msg), flush=True)


def load_sdk():
    try:
        from school_api import SchoolClient
        return SchoolClient
    except ImportError:
        log("缺少依赖 School-Api，请在 requirements.txt 中安装")
        return None


def build_client(SchoolClient):
    """老版正方通用配置；桂林理工路径用环境变量覆盖。"""
    home = os.environ.get("JW_HOME_PATH", "/academic/xs_main.aspx?xh=")
    schedule = os.environ.get("JW_SCHEDULE_PATH", "/academic/xskbcx.aspx?gnmkdm=N121603&xh=")
    conf = {
        "url": BASE_URL,
        "name": "桂林理工大学",
        "code": "glut",
        "login_url_path": LOGIN_PATH,
        "exist_verify": os.environ.get("JW_HAS_CAPTCHA", "0") == "1",
        "timeout": 20,
        "url_path_list": [
            {
                "HOME_URL": home,
                "INFO_URL": os.environ.get("JW_INFO_PATH", "/academic/xsgrxx.aspx?gnmkdm=N121501&xh="),
                "SCHEDULE_URL": [schedule],
                "SCORE_URL": [],
            },
            {"HOME_URL": "", "INFO_URL": "", "SCHEDULE_URL": ["", ""]},
            {"HOME_URL": "", "SCHEDULE_URL": ["", ""]},
        ],
    }
    return SchoolClient(**conf)


def normalize(raw):
    """把 SDK 返回的课表转成页面期望的结构。字段缺失时跳过该条，不臆造。"""
    out = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        day = item.get("day") or item.get("xqj")
        period = item.get("period") or item.get("jcs")
        title = item.get("name") or item.get("kcmc")
        if day is None or period is None or not title:
            continue
        # 正方常把连堂返回成 "1-2" 或 "1,2"，拆成起止节次供页面跨节显示
        parts = [p for p in str(period).replace("—", "-").replace("~", "-").replace(",", "-").split("-") if p.strip().isdigit()]
        if not parts:
            continue
        start, end = int(parts[0]), int(parts[-1])
        if start < 1 or end > len(PERIODS) or end < start:
            continue
        out.append({
            "day": int(day) if str(day).isdigit() else str(day),
            "period": start,
            "end": end,
            "title": str(title).strip(),
            "location": str(item.get("location") or item.get("cdmc") or "").strip(),
            "teacher": str(item.get("teacher") or item.get("xm") or "").strip(),
        })
    return out


def current_term():
    now = datetime.now(timezone(timedelta(hours=8)))
    year = now.year if now.month >= 9 else now.year - 1
    term = 1 if now.month >= 9 or now.month <= 1 else 2
    return str(year), str(term)


def write_output(courses, year, term):
    payload = {
        "source": "正方教务系统",
        "syncedAt": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "year": year,
        "term": term,
        "periods": PERIODS,
        "courses": courses,
    }
    tmp = OUTPUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT)
    # 同步写一份 JS：本地 file:// 打开时浏览器禁止 fetch JSON，
    # 但允许 <script src> 加载，因此这份是离线可用的数据入口。
    tmp_js = OUTPUT_JS + ".tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write("window.COURSE_SYNC=" + json.dumps(payload, ensure_ascii=False) + ";\n")
    os.replace(tmp_js, OUTPUT_JS)
    log("已写入 courses.json 与 courses.js，课程数：" + str(len(courses)))


def main():
    if not USER or not PASSWORD:
        log("未配置 JW_USER / JW_PASSWORD，跳过抓取（保留现有数据）")
        return 0
    SchoolClient = load_sdk()
    if SchoolClient is None:
        return 2
    try:
        school = build_client(SchoolClient)
        user = school.user_login(USER, PASSWORD)
        if not user:
            log("登录失败：请核对学号/密码，或确认 login_url_path 是否正确")
            return 3
        year, term = current_term()
        raw = user.get_schedule(schedule_year=year, schedule_term=term)
        courses = normalize(raw)
        if not courses:
            log("未解析出课程：课表接口路径或返回字段可能不匹配，保留现有数据")
            return 4
        write_output(courses, year, term)
        return 0
    except Exception as exc:
        # 异常信息可能含 URL 或字段名，但不含凭据；仍避免完整堆栈外泄细节
        log("抓取异常（保留现有数据）：" + type(exc).__name__)
        return 5


if __name__ == "__main__":
    sys.exit(main())
