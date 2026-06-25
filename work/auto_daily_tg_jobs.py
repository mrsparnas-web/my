from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collect_tg_design_jobs as collector


ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
ENV_PATH = Path(os.environ.get("DESIGN_JOBS_ENV", ROOT / ".env"))
STATE_PATH = OUTPUTS / "automation_sent_urls.json"
RUNTIME_LOG = OUTPUTS / "automation_runtime.log"
LOCAL_TZ = collector.LOCAL_TZ
MAX_JOBS = 15

STRICT_EXCLUDES = (
    "motion designer",
    "моушн-дизайнер",
    "моушен дизайнер",
    "smm-специалист",
    "smm специалист",
    "reels",
    "рилс",
    "video editor",
    "видеомонтаж",
    "монтажер",
    "монтажёр",
    "ui/ux",
    "ux/ui",
    "ui designer",
    "product designer",
    "web designer",
    "веб-дизайнер",
    "figma web designer",
    "3d artist",
    "3d-дизайнер",
    "3d иллюстратор",
    "software engineer",
    "developer",
    "маркетолог",
    "sales manager",
    "менеджер по продажам",
    "стабильный поток заказов",
)

ROLE_TERMS = (
    "graphic designer",
    "графический дизайнер",
    "дизайнер",
    "illustrator",
    "иллюстратор",
    "packaging",
    "упаковк",
    "этикет",
    "brand designer",
    "бренд-дизайнер",
    "айдентик",
    "логотип",
    "presentation",
    "презентац",
    "prepress",
    "предпечат",
    "подготовк",
    "tilda",
    "zero block",
    "ai designer",
    "ии-дизайнер",
    "ai-дизайнер",
    "դիզայներ",
)

PRIORITY_TERMS = (
    "packaging",
    "упаковк",
    "этикет",
    "brand",
    "бренд",
    "айдентик",
    "логотип",
    "presentation",
    "презентац",
    "prepress",
    "предпечат",
    "печати",
    "полиграф",
    "tilda",
    "zero block",
    "ai designer",
    "ии-дизайнер",
    "ai-дизайнер",
    "midjourney",
    "runway",
    "heygen",
)

REMOTE_TERMS = (
    "remote",
    "удаленно",
    "удалённо",
    "фриланс",
    "freelance",
    "project",
    "проект",
    "part-time",
    "частичная занятость",
)

NON_YEREVAN_OFFICE = (
    "москва",
    "санкт-петербург",
    "алматы",
    "астана",
    "киев",
    "тбилиси",
    "office in london",
    "офис в москве",
    "офис, алматы",
)


def log(message: str) -> None:
    OUTPUTS.mkdir(exist_ok=True)
    stamp = datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    line = f"{stamp} {message}"
    print(line, flush=True)
    with RUNTIME_LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in (
        "BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "RU_THREAD_ID",
        "HY_THREAD_ID",
        "EN_THREAD_ID",
    ):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def load_state() -> dict[str, dict[str, str | int]]:
    if not STATE_PATH.exists():
        return {}
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {item["url"]: item for item in data if item.get("url")}


def historical_urls() -> set[str]:
    urls = set(load_state())
    pattern = re.compile(r"https://t\.me/[A-Za-z0-9_]+/\d+")
    for path in OUTPUTS.glob("*.txt"):
        try:
            urls.update(pattern.findall(path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return urls


def normalized_language(text: str, source_language: str) -> str:
    armenian = len(re.findall(r"[\u0530-\u058f]", text))
    cyrillic = len(re.findall(r"[\u0400-\u04ff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if armenian > max(25, latin // 3, cyrillic):
        return "hy"
    if cyrillic >= latin:
        return "ru"
    if latin:
        return "en"
    return source_language


def is_eligible(post: collector.Post, cutoff: datetime) -> bool:
    if not post.date:
        return False
    try:
        published = datetime.fromisoformat(post.date)
    except ValueError:
        return False
    if published < cutoff:
        return False

    low = post.text.lower()
    if not any(term in low for term in ROLE_TERMS):
        return False
    if any(term in low for term in STRICT_EXCLUDES):
        return False
    if any(place in low for place in NON_YEREVAN_OFFICE):
        if not any(term in low for term in REMOTE_TERMS):
            return False
    if ("офис" in low or "on-site" in low or "onsite" in low) and not any(
        place in low for place in ("ереван", "yerevan", "երևան")
    ):
        if not any(term in low for term in REMOTE_TERMS):
            return False
    if len(post.text.strip()) < 70 and post.contacts.startswith("прямой контакт"):
        return False
    return any(term in low for term in PRIORITY_TERMS) or post.score >= 12


def translate(text: str, target: str, source: str = "auto") -> str:
    chunks = [text[index : index + 1800] for index in range(0, len(text), 1800)]
    translated: list[str] = []
    for chunk in chunks:
        params = urllib.parse.urlencode(
            {
                "client": "gtx",
                "sl": source,
                "tl": target,
                "dt": "t",
                "q": chunk,
            }
        )
        request = urllib.request.Request(
            f"https://translate.googleapis.com/translate_a/single?{params}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
        translated.append("".join(part[0] for part in payload[0] if part[0]))
        time.sleep(0.15)
    return "\n".join(translated).strip()


def category(text: str) -> str:
    low = text.lower()
    if any(term in low for term in ("упаков", "packaging", "этикет", "label")):
        return "packaging"
    if any(term in low for term in ("логотип", "айдентик", "brand", "бренд")):
        return "brand"
    if any(term in low for term in ("предпечат", "prepress", "печати", "print")):
        return "print"
    if any(term in low for term in ("ai", "ии-", "нейросет", "midjourney", "runway")):
        return "ai"
    if any(term in low for term in ("presentation", "презентац")):
        return "presentation"
    if "tilda" in low or "zero block" in low:
        return "tilda"
    return "graphic"


def russian_response(kind: str) -> str:
    responses = {
        "packaging": (
            "Здравствуйте! Я packaging- и brand-дизайнер с опытом разработки упаковки "
            "и этикеток. Создаю концепции, мокапы и готовлю финальные макеты к печати "
            "в Illustrator, Photoshop и InDesign. Готова прислать релевантные кейсы "
            "и обсудить задачу, сроки и бюджет."
        ),
        "brand": (
            "Здравствуйте! Я brand-дизайнер, занимаюсь логотипами, айдентикой и визуальными "
            "системами для коммерческих брендов. Могу предложить несколько концептуальных "
            "направлений и подготовить полный комплект файлов для digital и печати. "
            "Готова прислать портфолио и обсудить задачу."
        ),
        "print": (
            "Здравствуйте! У меня есть опыт полиграфии и предпечатной подготовки: проверяю "
            "размеры, вылеты, цветовую модель, разрешение, шрифты и требования производства. "
            "Работаю в Illustrator, Photoshop, InDesign и CorelDraw. Готова быстро подключиться."
        ),
        "ai": (
            "Здравствуйте! Я графический и AI-дизайнер. Создаю коммерческие визуалы "
            "с помощью Midjourney, ChatGPT и Runway, дорабатываю результаты в Photoshop "
            "и адаптирую их под бренд и нужные форматы. Готова прислать примеры работ."
        ),
        "presentation": (
            "Здравствуйте! Я графический дизайнер с опытом создания презентаций, визуальных "
            "концепций и брендированных материалов. Умею структурировать информацию, "
            "выстраивать композицию и готовить аккуратные редактируемые макеты. "
            "Готова прислать релевантные примеры."
        ),
        "tilda": (
            "Здравствуйте! Я дизайнер и специалист по Tilda/Zero Block. Разрабатываю "
            "структуру, визуальную концепцию и адаптивный дизайн лендингов, собираю страницы "
            "и настраиваю базовые анимации. Готова прислать примеры и обсудить объём проекта."
        ),
        "graphic": (
            "Здравствуйте! Я графический дизайнер с опытом в брендинге, презентациях, "
            "полиграфии и коммерческих визуалах. Работаю в Illustrator, Photoshop, InDesign "
            "и Figma, соблюдаю сроки и внимательно отношусь к деталям. Готова прислать портфолио."
        ),
    }
    return responses[kind]


def response_for(post: collector.Post, language: str) -> str:
    base = russian_response(category(post.text))
    if language == "ru":
        return base
    if language == "en":
        return translate(base, "en", "ru")
    return translate(base, "hy", "ru")


def clean_text(text: str) -> str:
    text = re.sub(r"\?q=%[A-Fa-f0-9%]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fit_message(
    post: collector.Post,
    language: str,
    translation: str | None,
    response: str,
) -> str:
    original = clean_text(post.text)
    contacts = post.contacts.strip() or "прямой контакт не указан"
    date_text = datetime.fromisoformat(post.date).strftime("%d.%m.%Y, %H:%M")

    def assemble(source_text: str, translated_text: str | None) -> str:
        parts = [
            f"Ссылка:\n{post.url}",
            f"Контакты:\n{contacts}",
            f"Дата публикации:\n{date_text} (Ереван)",
            f"Текст вакансии:\n{source_text}",
        ]
        if translated_text:
            parts.append(f"Перевод на русский:\n{translated_text}")
        parts.append(f"Отклик:\n{response}")
        return "\n\n".join(parts)

    message = assemble(original, translation)
    if len(message) <= 4000:
        return message

    translated_limit = 900 if translation else 0
    source_limit = 1800 if translation else 2850
    short_original = original[:source_limit].rstrip() + "\n[текст сокращён]"
    short_translation = None
    if translation:
        short_translation = translation[:translated_limit].rstrip() + "\n[перевод сокращён]"
    message = assemble(short_original, short_translation)
    if len(message) > 4000:
        message = message[:3990].rstrip()
    return message


def send_message(
    token: str,
    chat_id: str,
    threads: dict[str, int],
    language: str,
    text: str,
) -> int:
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "message_thread_id": str(threads[language]),
            "text": text,
            "disable_web_page_preview": "false",
        }
    ).encode("utf-8")
    with urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        timeout=30,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(payload)
    return int(payload["result"]["message_id"])


def save_results(
    candidates: list[collector.Post],
    records: list[dict[str, str | int]],
    messages: list[str],
) -> None:
    now = datetime.now(LOCAL_TZ)
    stamp = now.strftime("%Y-%m-%d_%H%M%S")
    candidate_path = OUTPUTS / f"automation_candidates_{stamp}.json"
    result_path = OUTPUTS / f"automation_sent_{stamp}.txt"
    candidate_path.write_text(
        json.dumps([asdict(post) for post in candidates], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2)
        + "\n\n"
        + "\n\n---\n\n".join(messages),
        encoding="utf-8",
    )
    state = list(load_state().values())
    known = {item["url"] for item in state}
    state.extend(record for record in records if record["url"] not in known)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run(dry_run: bool) -> int:
    log(f"run started dry_run={dry_run}")
    sent_urls = historical_urls()
    posts = collector.collect()
    cutoff = datetime.now(timezone.utc).astimezone(LOCAL_TZ) - timedelta(hours=48)
    selected = [
        post
        for post in posts
        if post.url not in sent_urls and is_eligible(post, cutoff)
    ][:MAX_JOBS]
    log(f"collected={len(posts)} selected={len(selected)} known_urls={len(sent_urls)}")

    settings = load_env()
    required = (
        "BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "RU_THREAD_ID",
        "HY_THREAD_ID",
        "EN_THREAD_ID",
    )
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise RuntimeError(f"Missing settings: {', '.join(missing)}")
    token = settings["BOT_TOKEN"]
    chat_id = settings["TELEGRAM_CHAT_ID"]
    threads = {
        "ru": int(settings["RU_THREAD_ID"]),
        "hy": int(settings["HY_THREAD_ID"]),
        "en": int(settings["EN_THREAD_ID"]),
    }
    records: list[dict[str, str | int]] = []
    messages: list[str] = []
    for post in selected:
        language = normalized_language(post.text, post.language)
        source_text = clean_text(post.text)
        translation = None
        if language in {"hy", "en"}:
            try:
                translation = translate(source_text[:2800], "ru", language)
            except Exception as exc:
                log(f"skip translation_failed url={post.url} error={exc!r}")
                continue
        try:
            response = response_for(post, language)
        except Exception as exc:
            log(f"skip response_failed url={post.url} error={exc!r}")
            continue
        message = fit_message(post, language, translation, response)
        if dry_run:
            message_id = 0
            log(f"dry-run language={language} url={post.url}")
        else:
            message_id = send_message(token, chat_id, threads, language, message)
            log(f"sent language={language} message_id={message_id} url={post.url}")
            time.sleep(0.7)
        records.append(
            {
                "url": post.url,
                "language": language,
                "message_id": message_id,
                "sent_at": datetime.now(LOCAL_TZ).isoformat(timespec="seconds"),
            }
        )
        messages.append(message)

    if not dry_run:
        save_results(posts, records, messages)
    log(f"run completed sent={len(records) if not dry_run else 0} candidates={len(records)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        return run(args.dry_run)
    except Exception as exc:
        log(f"run failed error={exc!r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
