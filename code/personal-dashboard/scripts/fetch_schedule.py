#!/usr/bin/env python3
"""从桂林理工大学 Java 正方教务系统抓取当前学期课表，输出 courses.json。

凭据只从环境变量读取（JW_USER / JW_PASSWORD），不写入代码、不打印、不提交。
缺少任一凭据时脚本以 0 退出并保留现有 courses.json —— 这样 Actions 不会因
未配置 Secrets 而失败，用户本地跑也不会破坏数据。

登录与课表路径参考开源项目 Jacknic/glut（MIT）：
  https://github.com/Jacknic/glut
- 登录：POST /academic/j_acegi_security_check，明文密码，无验证码
- 课表：GET /academic/student/currcourse/currcourse.jsdo（GBK 编码 HTML）
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("[fetch_schedule] 缺少依赖 requests，请安装 requirements.txt", flush=True)
    sys.exit(2)

BASE_URL = os.environ.get("JW_BASE_URL", "https://jw.glut.edu.cn").rstrip("/")
USER = os.environ.get("JW_USER", "").strip()
PASSWORD = os.environ.get("JW_PASSWORD", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "courses.json")
OUTPUT_JS = os.path.join(ROOT, "courses.js")
TIMEOUT = int(os.environ.get("JW_TIMEOUT", "20"))
SCHEDULE_PATH = "/academic/student/currcourse/currcourse.jsdo"

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


def log(msg):
    # 不打印任何凭据相关内容
    print("[fetch_schedule] " + str(msg), flush=True)


def norm(s):
    return re.sub(r"\s+", "", s or "")


def strip_tags(s):
    return norm(re.sub(r"<[^>]+>", " ", s))


def day_number(text):
    """星期文字转数字 1-7。"""
    m = re.search(r"星期([一二三四五六日天])", norm(text))
    if not m:
        return None
    return "一二三四五六日天".index(m.group(1)) + 1


def period_range(text):
    """'第5、6节' / '第7-8节' / '5-8' 转成 (start, end)。"""
    t = norm(text).replace("第", "").replace("节", "")
    t = t.replace("—", "-").replace("~", "-").replace("、", ",").replace("，", ",")
    nums = [int(x) for x in re.findall(r"\d+", t)]
    if not nums:
        return None
    start, end = min(nums), max(nums)
    if start < 1 or end > len(PERIODS) or end < start:
        return None
    return start, end


def weeks_hit(weeks_text, week):
    """判断周次描述是否包含指定周；不合法返回 False。"""
    t = norm(weeks_text)
    if not t:
        return False
    for seg in re.split(r"[,，;；]", t):
        m = re.match(r"^(\d+)-(\d+)周?$", seg)
        if m:
            if int(m.group(1)) <= week <= int(m.group(2)):
                return True
            continue
        m = re.match(r"^第?(\d+)周?$", seg)
        if m and int(m.group(1)) == week:
            return True
    return False


def current_week():
    """返回 (年份, 学期, 当前教学周)。无开学日配置时返回 None 周，不过滤。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    year = now.year if now.month >= 9 else now.year - 1
    term = 1 if now.month >= 9 or now.month <= 1 else 2
    start = os.environ.get("JW_TERM_START", "").strip()
    if not start:
        return year, term, None
    try:
        d0 = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=8)))
        week = (now - d0).days // 7 + 1
        return year, term, max(1, week)
    except ValueError:
        log("JW_TERM_START 格式错误（应为 YYYY-MM-DD），忽略周次过滤")
        return year, term, None


def login(session):
    session.get(BASE_URL + "/academic/affairLogin.do", timeout=TIMEOUT, headers=HEADERS)
    resp = session.post(
        BASE_URL + "/academic/j_acegi_security_check",
        data={"j_username": USER, "j_password": PASSWORD, "j_captcha": ""},
        headers=HEADERS, allow_redirects=False, timeout=TIMEOUT,
    )
    location = resp.headers.get("Location", "")
    if "login_error" in location:
        log("登录失败：请核对学号与密码")
        return False
    if resp.status_code in (302, 303) and location:
        return True
    if resp.status_code == 200 and "j_acegi_security_check" not in resp.url:
        return True
    log("登录状态未知（HTTP " + str(resp.status_code) + "）")
    return False


def fetch_schedule(session, year, term):
    params = {}
    if os.environ.get("JW_USE_TERM_PARAM", "0") == "1":
        # Java 正方：year = 年份-1980，term = 1春/2秋
        params = {"year": str(year - 1980), "term": str(term)}
    resp = session.get(BASE_URL + SCHEDULE_PATH, params=params, headers=HEADERS, timeout=TIMEOUT)
    if resp.status_code != 200:
        log("课表页 HTTP " + str(resp.status_code))
        return None
    if "login.jsp" in resp.url:
        log("课表页跳转到登录页，会话失效")
        return None
    try:
        return resp.content.decode("gbk")
    except UnicodeDecodeError:
        return resp.content.decode("utf-8", errors="replace")


def parse_schedule(html, week):
    """从课表 HTML 提取课程块。外层行是课程，内层 none 表是上课安排。"""
    out = []
    rows = re.split(r'<tr\s+class="infolist_common"', html)[1:]
    for row in rows:
        head = row.split("<table", 1)[0]
        title_m = re.search(r'class="infolist"[^>]*>([^<]+)</a>', head)
        teacher_m = re.search(r"showTeacherInfoItem[^>]*>([^<]+)</a>", head)
        title = norm(title_m.group(1)) if title_m else ""
        teacher = norm(teacher_m.group(1)) if teacher_m else ""
        if not title:
            continue
        for tr in re.findall(r"<tr>(.*?)</tr>", row, re.S):
            tds = [strip_tags(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(tds) < 4:
                continue
            weeks, day_text, period_text, loc = tds[0], tds[1], tds[2], tds[3]
            day = day_number(day_text)
            period = period_range(period_text)
            if not day or not period:
                continue
            if week and not weeks_hit(weeks, week):
                continue
            if day > 5:
                continue  # 页面不排周末
            out.append({
                "day": day,
                "period": period[0],
                "end": period[1],
                "title": title[:24],
                "location": loc[:24],
                "teacher": teacher[:12],
            })
    # 去重：同一课程同星期同节次同教室只保留一条
    seen, uniq = set(), []
    for c in out:
        key = (c["day"], c["period"], c["end"], c["title"], c["location"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return sorted(uniq, key=lambda c: (c["day"], c["period"]))


def write_output(courses, year, term):
    payload = {
        "source": "正方教务系统",
        "syncedAt": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "year": str(year),
        "term": str(term),
        "periods": PERIODS,
        "courses": courses,
    }
    tmp = OUTPUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT)
    # 本地 file:// 打开时浏览器禁止 fetch JSON，但允许 <script src>，故同步写 JS
    tmp_js = OUTPUT_JS + ".tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write("window.COURSE_SYNC=" + json.dumps(payload, ensure_ascii=False) + ";\n")
    os.replace(tmp_js, OUTPUT_JS)
    log("已写入 courses.json 与 courses.js，课程数：" + str(len(courses)))


def main():
    if not USER or not PASSWORD:
        log("未配置 JW_USER / JW_PASSWORD，跳过抓取（保留现有数据）")
        return 0
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        if not login(session):
            return 3
        year, term, week = current_week()
        html = fetch_schedule(session, year, term)
        if html is None:
            return 4
        courses = parse_schedule(html, week)
        if not courses:
            log("未解析出课程：课表页结构可能变化，保留现有数据")
            if os.environ.get("JW_DEBUG_HTML", "0") == "1":
                debug = os.path.join(ROOT, "courses_debug.html")
                with open(debug, "w", encoding="utf-8") as f:
                    f.write(html)
                log("已保存调试页面 courses_debug.html（请勿提交）")
            return 4
        write_output(courses, year, term)
        return 0
    except requests.RequestException as exc:
        log("网络异常（保留现有数据）：" + type(exc).__name__)
        return 5
    except Exception as exc:
        log("抓取异常（保留现有数据）：" + type(exc).__name__)
        return 5


if __name__ == "__main__":
    sys.exit(main())
