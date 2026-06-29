from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError, PeerFloodError
from telethon.tl.types import User


ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
ENV_PATH = Path(os.environ.get("DESIGN_JOBS_ENV", ROOT / ".env"))
SESSION_PATH = ROOT / "secrets" / "telegram_user"
STATE_PATH = OUTPUTS / "personal_reply_state.json"
LOG_PATH = OUTPUTS / "personal_reply_runtime.log"
MAX_DAILY_REPLIES = 5

CONTACTS_RE = re.compile(
    r"Контакты:[ \t]*\n(.*?)(?=\n\n(?:Дата публикации|Текст вакансии):)",
    re.IGNORECASE | re.DOTALL,
)
RESPONSE_RE = re.compile(r"Отклик:[ \t]*\n(.+)\Z", re.IGNORECASE | re.DOTALL)
USERNAME_RE = re.compile(r"(?<![\w/])@([A-Za-z0-9_]{4,32})")
TME_RE = re.compile(r"https?://t\.me/([A-Za-z0-9_]{4,32})", re.IGNORECASE)


def log(message: str) -> None:
    OUTPUTS.mkdir(exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{stamp} {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as stream:
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
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_CHAT_ID",
        "RU_THREAD_ID",
        "PORTFOLIO_URL",
    ):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def required_settings() -> dict[str, str]:
    settings = load_env()
    required = (
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_CHAT_ID",
        "RU_THREAD_ID",
        "PORTFOLIO_URL",
    )
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise RuntimeError(f"Missing settings: {', '.join(missing)}")
    return settings


def load_state() -> dict[str, object]:
    if not STATE_PATH.exists():
        return {
            "last_seen_message_id": 0,
            "sent_source_message_ids": [],
            "daily_counts": {},
        }
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, object]) -> None:
    OUTPUTS.mkdir(exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_ru_topic_message(message: object, thread_id: int) -> bool:
    reply_to = getattr(message, "reply_to", None)
    if reply_to is None:
        return False
    top_id = getattr(reply_to, "reply_to_top_id", None)
    reply_id = getattr(reply_to, "reply_to_msg_id", None)
    return top_id == thread_id or reply_id == thread_id


def parse_vacancy_message(text: str) -> tuple[list[str], str] | None:
    if "Ссылка:" not in text or "Текст вакансии:" not in text:
        return None
    contacts_match = CONTACTS_RE.search(text)
    response_match = RESPONSE_RE.search(text)
    if not contacts_match or not response_match:
        return None

    contacts = contacts_match.group(1)
    usernames = {
        match.group(1)
        for pattern in (USERNAME_RE, TME_RE)
        for match in pattern.finditer(contacts)
    }
    blocked = {
        "nina_job_finder_bot",
        "designerworkchat",
        "designer_ru",
        "designer_ru_work",
        "designhunters",
        "graphicdesignarm",
        "ijobam",
        "ijobam_it",
    }
    usernames = {name for name in usernames if name.lower() not in blocked}
    response = response_match.group(1).strip()
    return sorted(usernames), response


def response_with_portfolio(response: str, portfolio_url: str) -> str:
    portfolio_url = portfolio_url.rstrip("/") + "/"
    if portfolio_url.lower() in response.lower():
        return response
    return f"{response}\n\nПортфолио: {portfolio_url}"


async def authorize(client: TelegramClient, chat_id: int) -> int:
    await client.start()
    me = await client.get_me()
    if getattr(me, "bot", False):
        raise RuntimeError("Personal Telegram authorization is required, not a bot.")
    chat = await client.get_entity(chat_id)
    latest = await client.get_messages(chat, limit=1)
    state = load_state()
    if latest and not state.get("last_seen_message_id"):
        state["last_seen_message_id"] = latest[0].id
        save_state(state)
    print(f"\nАвторизация завершена: {me.first_name} (id={me.id})")
    print("Существующие сообщения отмечены как просмотренные; отправка начнётся с новых вакансий.")
    input("\nНажмите Enter, чтобы закрыть окно...")
    return 0


async def send_replies(client: TelegramClient, settings: dict[str, str], dry_run: bool) -> int:
    if not SESSION_PATH.with_suffix(".session").exists():
        raise RuntimeError("Telegram user session is missing. Run with --authorize first.")

    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram user session expired. Run with --authorize again.")

    chat_id = int(settings["TELEGRAM_CHAT_ID"])
    thread_id = int(settings["RU_THREAD_ID"])
    portfolio_url = settings["PORTFOLIO_URL"]
    chat = await client.get_entity(chat_id)
    state = load_state()
    last_seen = int(state.get("last_seen_message_id", 0))
    sent_ids = {int(value) for value in state.get("sent_source_message_ids", [])}
    daily_counts = dict(state.get("daily_counts", {}))
    today = datetime.now().astimezone().date().isoformat()
    sent_today = int(daily_counts.get(today, 0))
    sent_now = 0

    async for message in client.iter_messages(chat, min_id=last_seen, reverse=True):
        state["last_seen_message_id"] = max(
            int(state.get("last_seen_message_id", 0)),
            message.id,
        )
        if message.id in sent_ids or not is_ru_topic_message(message, thread_id):
            save_state(state)
            continue
        text = message.raw_text or ""
        parsed = parse_vacancy_message(text)
        if not parsed:
            save_state(state)
            continue
        usernames, response = parsed
        if len(usernames) != 1:
            log(f"skip source_message_id={message.id} contact_count={len(usernames)}")
            save_state(state)
            continue
        if sent_today + sent_now >= MAX_DAILY_REPLIES:
            log("daily limit reached")
            save_state(state)
            break

        username = usernames[0]
        try:
            entity = await client.get_entity(username)
        except Exception as exc:
            log(f"skip source_message_id={message.id} username=@{username} resolve={exc!r}")
            save_state(state)
            continue
        if not isinstance(entity, User) or getattr(entity, "bot", False):
            log(f"skip source_message_id={message.id} username=@{username} not_human_user")
            save_state(state)
            continue

        outbound = response_with_portfolio(response, portfolio_url)
        if dry_run:
            log(f"dry-run source_message_id={message.id} username=@{username}")
        else:
            try:
                await client.send_message(entity, outbound, link_preview=False)
            except FloodWaitError as exc:
                log(f"flood_wait seconds={exc.seconds}")
                save_state(state)
                break
            except PeerFloodError:
                log("peer_flood: Telegram blocked further outreach; stopping")
                save_state(state)
                break
            except Exception as exc:
                log(f"send_failed source_message_id={message.id} username=@{username} error={exc!r}")
                save_state(state)
                continue
            sent_ids.add(message.id)
            state["sent_source_message_ids"] = sorted(sent_ids)
            sent_now += 1
            daily_counts[today] = sent_today + sent_now
            state["daily_counts"] = daily_counts
            save_state(state)
            log(f"sent source_message_id={message.id} username=@{username}")
            await asyncio.sleep(random.randint(35, 75))

    save_state(state)
    log(f"completed sent={sent_now} dry_run={dry_run}")
    return 0


async def async_main(args: argparse.Namespace) -> int:
    settings = required_settings()
    SESSION_PATH.parent.mkdir(exist_ok=True)
    client = TelegramClient(
        str(SESSION_PATH),
        int(settings["TELEGRAM_API_ID"]),
        settings["TELEGRAM_API_HASH"],
    )
    if args.authorize:
        async with client:
            return await authorize(client, int(settings["TELEGRAM_CHAT_ID"]))
    try:
        return await send_replies(client, settings, args.dry_run)
    finally:
        await client.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorize", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        log(f"failed error={exc!r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
