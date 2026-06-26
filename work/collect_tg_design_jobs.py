from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Asia/Yerevan")
FRESH_HOURS = 96

SOURCES = [
    ("designer_ru", "ИЩУ_ДИЗАЙНЕРА", "ru"),
    ("designerworkchat", "ИЩУ_ДИЗАЙНЕРА чат", "ru"),
    ("designer_ru_work", "Дизайн-Рабочая", "ru"),
    ("designhunters", "Design Hunters", "ru"),
    ("uiux_job", "UI/UX Jobs", "ru"),
    ("motionhunter", "Motion designer hunter", "ru"),
    ("normrabota", "Норм работа", "ru"),
    ("promopoisk", "Вакансии с ЗП выше 50 тысяч", "ru"),
    ("dsgnworkers", "Вакансии для дизайнеров", "ru"),
    ("job_for_designers", "Вакансии и заказы на дизайн", "ru"),
    ("pravkiforyou", "Правки", "ru"),
    ("tilda_profi", "Tilda Profi", "ru"),
    ("tildajobs", "Ищу дизайнера / Сайты на Tilda", "ru"),
    ("rabota_go", "Проекты и вакансии: Дизайн & Маркетинг", "ru"),
    ("artnagrada", "Арт-награда", "ru"),
    ("ai_jobs_free", "Нейросети / Вакансии & Фриланс", "ru"),
    ("video_production_job", "Заказы на видео / YouTube / Reels", "ru"),
    ("freelance_rabota", "Фриланс-чат", "ru"),
    ("graphicdesignarm", "Graphic Designers (Armenia)", "hy"),
    ("staffamdesign", "staff.am Design jobs", "hy"),
    ("jobs_inarmenia", "Вакансии в Армении / Jobs in Armenia", "hy"),
    ("iJobAm", "iJob.am", "hy"),
    ("iJobAm_IT", "iJob.am IT", "hy"),
    ("remotejobss", "Remote Jobs", "en"),
    ("ingamejob_art", "Jobs: Art and Animation", "en"),
]

SEARCH_QUERIES = [
    "",
    "дизайнер",
    "упаковка",
    "Tilda",
    "AI",
    "graphic designer",
    "packaging",
    "դիզայներ",
    "աշխատանք",
]

REQUEST_TERMS = [
    "ищем",
    "ищет",
    "ищу",
    "нужен",
    "нужна",
    "нужны",
    "требуется",
    "вакансия",
    "заказ",
    "работа",
    "проект",
    "hiring",
    "job",
    "vacancy",
    "looking for",
    "is looking",
    "աշխատանք",
    "գործկա",
    "փնտրում",
    "անհրաժեշտ",
]

FIT_TERMS = [
    "дизайнер",
    "графичес",
    "graphic",
    "brand",
    "бренд",
    "айдентик",
    "лого",
    "упаков",
    "этикет",
    "tilda",
    "zero block",
    "лендинг",
    "landing",
    "presentation",
    "презентац",
    "illustrator",
    "photoshop",
    "figma",
    "print",
    "печати",
    "полиграф",
    "ai",
    "нейро",
    "heygen",
    "runway",
    "գրաֆիկ",
    "դիզայներ",
    "բրենդ",
    "փաթեթ",
    "պիտակ",
]

EXCLUDE_TERMS = [
    "reels",
    "рилс",
    "shorts",
    "tiktok",
    "тикток",
    "сторис",
    "stories",
    "smm",
    "смм",
    "контент-мейкер",
    "content maker",
    "ugc",
    "видеомонтаж",
    "монтажер",
    "монтажёр",
    "video editor",
    "figma web designer",
    "web designer",
    "ui designer",
    "ux/ui",
    "ui/ux",
    "motion",
    "оператор",
    "съемк",
    "съёмк",
    "одежд",
    "веб-дизайнер",
    "интерфейс",
    "интерфейсов",
    "моушн",
    "фото-видео-продакшн",
    "видео-продакшн",
    "техническое сопровождение",
    "техсопровождение",
]

AI_VIDEO_KEEP_TERMS = [
    "ai",
    "нейро",
    "ии",
    "heygen",
    "runway",
    "elevenlabs",
    "субтитр",
    "плашк",
    "визуаль",
    "дизайн",
]


@dataclass
class Post:
    source: str
    username: str
    post_id: str
    url: str
    date: str
    language: str
    contacts: str
    score: int
    reason: str
    text: str


class TelegramSParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.posts: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_text = False
        self._text_depth = 0
        self._text_parts: list[str] = []
        self._message_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = attr.get("class", "")
        if tag == "div" and "tgme_widget_message" in classes and attr.get("data-post"):
            self._current = {"data_post": attr["data-post"], "text": "", "datetime": ""}
            self._message_depth = 1
            return
        if self._current is None:
            return
        if tag == "div":
            self._message_depth += 1
        if tag == "div" and "tgme_widget_message_text" in classes:
            self._capture_text = True
            self._text_depth = 1
            self._text_parts = []
            return
        if self._capture_text:
            if tag in {"div", "span", "a", "b", "i", "strong", "em"}:
                self._text_depth += 1
            if tag == "a" and attr.get("href") and not attr["href"].startswith("?q="):
                self._text_parts.append(f" {attr['href']} ")
            if tag == "br":
                self._text_parts.append("\n")
        if tag == "time":
            self._current["datetime"] = attr.get("datetime", "") or self._current["datetime"]

    def handle_data(self, data: str) -> None:
        if self._capture_text:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if self._capture_text:
            if tag in {"div", "span", "a", "b", "i", "strong", "em"}:
                self._text_depth -= 1
            if self._text_depth <= 0:
                self._current["text"] = "".join(self._text_parts)
                self._capture_text = False
                self._text_parts = []
        if tag == "div":
            self._message_depth -= 1
            if self._message_depth <= 0:
                if self._current.get("text"):
                    self.posts.append(self._current)
                self._current = None


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_channel(username: str, query: str) -> str:
    params = f"?q={urllib.parse.quote(query)}" if query else ""
    url = f"https://t.me/s/{urllib.parse.quote(username)}{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=14) as response:
        return response.read().decode("utf-8", errors="replace")


def detect_language(text: str, source_language: str) -> str:
    armenian = len(re.findall(r"[\u0530-\u058f]", text))
    cyrillic = len(re.findall(r"[А-Яа-яЁё]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if armenian > 8:
        return "hy"
    if cyrillic >= latin:
        return "ru"
    if latin > 0:
        return "en"
    return source_language


def score_text(text: str) -> tuple[int, str]:
    low = text.lower()
    has_request = any(term in low for term in REQUEST_TERMS)
    has_fit = any(term in low for term in FIT_TERMS)
    if not has_request or not has_fit:
        return -20, "нет явной вакансии/заказа по профилю"

    excluded = [term for term in EXCLUDE_TERMS if term in low]
    has_priority_core = any(
        term in low
        for term in [
            "упаков",
            "этикет",
            "packaging",
            "label",
            "айдентик",
            "бренд",
            "brand",
            "лого",
            "presentation",
            "презентац",
            "tilda",
            "zero block",
            "полиграф",
            "печати",
            "print",
            "ai",
            "нейро",
            "heygen",
            "runway",
            "midjourney",
        ]
    )
    if excluded and not has_priority_core:
        return -50, "отсечено как SMM/reels/video-only"

    score = 0
    reasons: list[str] = []
    for term in FIT_TERMS:
        if term in low:
            score += 1
    if any(term in low for term in ["упаков", "этикет", "packaging", "պիտակ", "փաթեթ"]):
        score += 6
        reasons.append("упаковка/этикетки")
    if any(term in low for term in ["айдентик", "бренд", "brand", "лого", "բրենդ"]):
        score += 5
        reasons.append("брендинг/айдентика")
    if any(term in low for term in ["tilda", "zero block", "лендинг", "landing"]):
        score += 5
        reasons.append("Tilda/лендинги")
    if any(term in low for term in ["illustrator", "photoshop", "figma", "print", "печати", "полиграф"]):
        score += 4
        reasons.append("профильные инструменты/печать")
    if any(term in low for term in ["ai", "нейро", "heygen", "runway", "elevenlabs"]):
        score += 4
        reasons.append("AI/нейросети")
    if any(term in low for term in ["remote", "удален", "удалён", "հեռավար", "freelance", "фриланс", "project"]):
        score += 3
        reasons.append("удаленно/проектно")
    if any(term in low for term in ["yerevan", "armenia", "ереван", "армени", "երևան", "հայաստան"]):
        score += 2
        reasons.append("Армения/Ереван")

    if not reasons:
        reasons.append("графический дизайн по профилю")
    return score, "; ".join(reasons[:3])


def extract_contacts(text: str) -> str:
    contacts: list[str] = []
    for email in re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}", text):
        contacts.append(email)
    for username in re.findall(r"(?<![\w/])@[A-Za-z0-9_]{4,32}", text):
        contacts.append(username)
    for link in re.findall(r"https?://[^\s)>\]]+", text):
        clean = link.rstrip(".,;:!?)»")
        lowered = clean.lower()
        if any(
            marker in lowered
            for marker in [
                "t.me",
                "wa.me",
                "whatsapp",
                "forms.",
                "docs.google",
                "designer.ru",
                "geekjob",
                "staff.am",
                "ijob.am",
                "hh.ru",
                "notion.site",
                "typeform",
            ]
        ):
            contacts.append(clean)
    for phone in re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", text):
        compact = re.sub(r"\D", "", phone)
        if len(compact) >= 9:
            contacts.append(phone.strip())
    seen: set[str] = set()
    unique: list[str] = []
    for contact in contacts:
        if contact not in seen:
            seen.add(contact)
            unique.append(contact)
    return "\n".join(unique) if unique else "прямой контакт не указан"


def title_for(text: str) -> str:
    lines = [line.strip(" -•–—:") for line in clean_text(text).splitlines() if line.strip()]
    for line in lines:
        if len(line) > 4:
            return (line[:97] + "...") if len(line) > 100 else line
    return "Дизайн-вакансия / проект"


def collect() -> list[Post]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESH_HOURS)
    by_url: dict[str, Post] = {}
    for username, source_name, source_language in SOURCES:
        for query in SEARCH_QUERIES:
            try:
                page = fetch_channel(username, query)
            except Exception as exc:
                if not query:
                    print(f"SKIP {username}: {exc}")
                continue
            parser = TelegramSParser()
            parser.feed(page)
            for item in parser.posts:
                data_post = item.get("data_post", "")
                if "/" not in data_post:
                    continue
                post_username, post_id = data_post.split("/", 1)
                date = parse_date(item.get("datetime", ""))
                if date and date < cutoff:
                    continue
                text = clean_text(item.get("text", ""))
                if not text:
                    continue
                score, reason = score_text(text)
                if score < 6:
                    continue
                url = f"https://t.me/{post_username}/{post_id}"
                language = detect_language(text, source_language)
                current = by_url.get(url)
                if current and current.score >= score:
                    continue
                by_url[url] = Post(
                    source=source_name,
                    username=post_username,
                    post_id=post_id,
                    url=url,
                    date=date.astimezone(LOCAL_TZ).isoformat(timespec="minutes") if date else "",
                    language=language,
                    contacts=extract_contacts(text),
                    score=score,
                    reason=reason,
                    text=text,
                )
            time.sleep(0.12)
    posts = list(by_url.values())
    posts.sort(key=lambda post: (post.score, post.date), reverse=True)
    return posts


def write_outputs(posts: list[Post]) -> None:
    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)
    date_stamp = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    json_path = out_dir / f"telegram_design_candidates_{date_stamp}.json"
    csv_path = out_dir / f"telegram_design_candidates_{date_stamp}.csv"
    json_path.write_text(json.dumps([asdict(post) for post in posts], ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(posts[0]).keys()) if posts else ["source", "url"])
        writer.writeheader()
        for post in posts:
            writer.writerow(asdict(post))
    print(f"Collected {len(posts)} candidates")
    print(json_path)
    print(csv_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    write_outputs(collect())


if __name__ == "__main__":
    main()
