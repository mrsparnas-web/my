# Telegram Design Jobs Automation

Ежедневный поиск свежих вакансий для графического, packaging-, brand- и AI-дизайнера с автоматической отправкой в языковые темы Telegram.

## Возможности

- мониторинг публичных Telegram-каналов на русском, армянском и английском;
- фильтрация motion-, SMM-, UI/UX-, web- и нерелевантных вакансий;
- приоритет упаковки, этикеток, айдентики, логотипов, презентаций, полиграфии, Tilda и AI-визуалов;
- извлечение Telegram, email, телефона и ссылок для отклика;
- перевод английских и армянских публикаций на русский;
- готовый отклик на языке вакансии;
- отправка каждой вакансии отдельным сообщением;
- защита от повторной отправки одной ссылки;
- журнал запусков и отправленных сообщений;
- отправка готовых откликов с личного Telegram-аккаунта по прямым контактам.

## Требования

- Python 3.11 или новее;
- Windows 10/11 для запуска через Task Scheduler;
- Telegram-бот с правом отправлять сообщения в forum topics группы.

Установите зафиксированную версию Telethon:

```powershell
python -m pip install -r requirements.txt
```

## Настройка

1. Скопируйте `.env.example` в `.env`.
2. Заполните:

```env
BOT_TOKEN=токен_бота
TELEGRAM_CHAT_ID=-1000000000000
RU_THREAD_ID=1
HY_THREAD_ID=2
EN_THREAD_ID=3
TELEGRAM_API_ID=API_ID_личного_аккаунта
TELEGRAM_API_HASH=API_HASH_личного_аккаунта
PORTFOLIO_URL=https://example.com/
```

3. Проверьте без отправки:

```powershell
python .\work\auto_daily_tg_jobs.py --dry-run
```

4. Выполните реальный запуск:

```powershell
python .\work\auto_daily_tg_jobs.py
```

## Ежедневный запуск Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\work\setup_windows_task.ps1
```

Будет создана задача `Nina Design Jobs Telegram` с ежедневным запуском в 12:00 по локальному времени Windows.

## Отклики с личного Telegram

Одноразовая авторизация:

```powershell
python .\work\personal_reply_sender.py --authorize
```

Проверка новых сообщений без отправки:

```powershell
python .\work\personal_reply_sender.py --dry-run
```

Ежедневная отправка в 12:20:

```powershell
powershell -ExecutionPolicy Bypass -File .\work\setup_personal_replies_task.ps1
```

Отправщик читает только тему `RU_THREAD_ID`, использует готовый блок `Отклик`, добавляет `PORTFOLIO_URL` и пишет только одному прямому Telegram-контакту. Лимит составляет 5 новых адресатов в день. Формы, email, каналы и боты пропускаются.

## Файлы

- `work/collect_tg_design_jobs.py` — сбор и первичная оценка публикаций;
- `work/auto_daily_tg_jobs.py` — фильтрация, перевод, дедупликация и отправка;
- `work/setup_windows_task.ps1` — установка ежедневной задачи Windows;
- `work/personal_reply_sender.py` — отправка откликов с личного Telegram;
- `work/setup_personal_replies_task.ps1` — ежедневный запуск откликов;
- `outputs/automation_runtime.log` — локальный журнал, не публикуется в Git.

## Безопасность

Файлы `.env`, `secrets/`, Telegram session и runtime-логи исключены через `.gitignore`. Не добавляйте токены, API hash или session-файлы в GitHub.
