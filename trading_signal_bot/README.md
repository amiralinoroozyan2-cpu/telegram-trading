# ربات خصوصی تحلیل و سیگنال ارز دیجیتال

این پروژه یک ربات کاملاً خصوصی تلگرام برای **تحلیل خودکار بازار و انتشار سیگنال** است. ربات فقط دادهٔ عمومی بازار را می‌خواند و هیچ اتصال خصوصی به صرافی، سفارش‌گذاری، خرید، فروش، برداشت، واریز، کیف پول یا اهرم ندارد.

> این نرم‌افزار ابزار تحلیل خودکار است و تضمین‌کنندهٔ سود یا توصیهٔ سرمایه‌گذاری نیست.

## امکانات

- رابط و پیام‌های فارسی در Telegram
- سیستم دسترسی خصوصی با Owner
- درخواست دسترسی و تایید/رد از طریق دکمه‌های تلگرام
- دریافت کندل‌های عمومی از Binance بدون API Key
- معماری قابل تعویض برای منبع دادهٔ بازار
- شاخص‌های RSI، MACD، EMA، SMA و نسبت حجم
- جلوگیری از Signal تکراری با شناسهٔ یکتا و محدودیت دیتابیس
- چرخهٔ کامل `ACTIVE`، `CLOSED`، `STOPPED` و `EXPIRED`
- ذخیرهٔ زمان‌ها به UTC و نمایش با منطقهٔ زمانی قابل تنظیم و تقویم شمسی
- ثبت رویدادهای ورود و خروج
- Retry برای دریافت دادهٔ بازار
- ادامهٔ اجرای Scheduler در صورت خطای یک چرخه
- Health Check امن در `GET /health`
- آمادهٔ استقرار روی Render با SQLite پایدار

## ساختار

```text
trading_signal_bot/
├── main.py
├── requirements.txt
├── render.yaml
├── .env.example
├── README.md
├── bot/
│   ├── handlers.py
│   ├── keyboards.py
│   └── permissions.py
├── market/data_provider.py
├── strategy/
│   ├── indicators.py
│   └── strategy.py
├── signals/manager.py
├── database/database.py
├── config/settings.py
├── scheduler/scheduler.py
├── health/server.py
└── utils/
    ├── formatting.py
    ├── logger.py
    └── time.py
```

## راه‌اندازی محلی

### ۱. ساخت Bot و گرفتن Token از BotFather

Token همان رمز اتصال برنامه به Bot API است و باید محرمانه بماند.

1. در Telegram به `@BotFather` بروید.
2. دستور `/newbot` را ارسال کنید.
3. یک نام نمایشی برای ربات وارد کنید؛ مثل `ربات تحلیل بازار`.
4. یک Username وارد کنید که به `bot` ختم شود؛ مثل `my_market_signal_bot`.
5. BotFather پیامی شبیه نمونهٔ زیر برمی‌گرداند:

```text
123456789:AAExampleTokenReturnedByBotFather
```

6. کل این مقدار را در `TELEGRAM_BOT_TOKEN` قرار دهید.

Token را در چت عمومی، Git، Screenshot، README یا Log قرار ندهید. اگر Token لو رفت، در `@BotFather` دستور `/revoke` را اجرا کنید و Token جدید بگیرید.

### ۲. گرفتن آیدی عددی کاربر مالک

`OWNER_TELEGRAM_ID` باید آیدی عددی حساب شخصی باشد که مالک ربات است؛ Username مثل `@example` قابل استفاده نیست.

روش ساده:

1. در Telegram به `@userinfobot` بروید.
2. دکمهٔ Start را بزنید یا `/start` ارسال کنید.
3. عددی که با عنوان `Id` نمایش داده می‌شود، آیدی شماست.
4. همان عدد را در `OWNER_TELEGRAM_ID` قرار دهید.

آیدی کاربر معمولاً یک عدد مثبت است. برای نمونه:

```env
OWNER_TELEGRAM_ID=123456789
```

برای کاربران دیگر لازم نیست از این روش استفاده کنید؛ وقتی کاربر درخواست دسترسی می‌دهد، ربات آیدی عددی او را برای Owner ارسال می‌کند.

### ۳. ساخت کانال و گرفتن Channel ID

#### ساخت و دسترسی ربات

1. یک کانال بسازید یا کانال موجود را انتخاب کنید.
2. ربات را به کانال اضافه کنید.
3. ربات را Administrator کنید.
4. مجوز ارسال پیام را برای ربات فعال کنید.

#### روش سریع برای کانال عمومی

اگر کانال Username عمومی دارد، می‌توانید مقدار `@ChannelUsername` را در `TELEGRAM_CHANNEL_ID` قرار دهید:

```env
TELEGRAM_CHANNEL_ID=@my_signal_channel
```

#### روش گرفتن آیدی عددی برای کانال خصوصی یا عمومی

آیدی عددی کانال معمولاً با `-100` شروع می‌شود؛ مثل `-1001234567890`.

1. اگر ربات در حال اجراست، موقتاً آن را متوقف کنید تا `getUpdates` با Polling هم‌زمان نشود.
2. ربات را Administrator کانال کنید.
3. یک پیام آزمایشی جدید در کانال منتشر کنید.
4. دستور زیر را با Token خود اجرا کنید:

```bash
export TELEGRAM_BOT_TOKEN='توکن_واقعی_اینجا'
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates"
```

5. در پاسخ JSON به بخش `channel_post` و سپس `chat` بروید:

```json
{
  "channel_post": {
    "chat": {
      "id": -1001234567890,
      "title": "کانال سیگنال",
      "type": "channel"
    }
  }
}
```

6. مقدار `chat.id` را در `TELEGRAM_CHANNEL_ID` قرار دهید.
7. بعد از پایان کار، مقدار Token را از متغیر محیطی و تاریخچهٔ Shell پاک کنید و ربات را دوباره اجرا کنید.

اگر پاسخ `result` خالی بود، مطمئن شوید پیام آزمایشی را بعد از Administrator شدن ربات منتشر کرده‌اید و ربات موقتاً متوقف است. Token را در URL عمومی، Screenshot یا پیام برای دیگران ارسال نکنید.

### ۴. تنظیم Environment Variables

فایل `.env.example` را به `.env` کپی کنید و مقادیر واقعی را فقط در محیط اجرا وارد کنید:

```bash
cp trading_signal_bot/.env.example trading_signal_bot/.env
```

حداقل متغیرهای لازم:

- `TELEGRAM_BOT_TOKEN` — Token دریافت‌شده از `@BotFather`
- `OWNER_TELEGRAM_ID` — آیدی عددی حساب مالک
- `TELEGRAM_CHANNEL_ID` — آیدی عددی کانال، یا Username کانال عمومی

نمونهٔ کامل بدون Secret واقعی:

```env
TELEGRAM_BOT_TOKEN=123456789:AAExampleToken
OWNER_TELEGRAM_ID=123456789
TELEGRAM_CHANNEL_ID=-1001234567890
TIMEZONE=Asia/Tehran
CHECK_INTERVAL_SECONDS=300
```

در Replit این مقادیر را در Secrets/Environment Variables قرار دهید. در Render از بخش Environment سرویس استفاده کنید. فایل `.env` فقط برای اجرای محلی است.

فایل `.env` را Commit نکنید.

### ۵. نصب و اجرای محلی

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r trading_signal_bot/requirements.txt
python -m trading_signal_bot.main
```

در Windows فعال‌سازی محیط مجازی با `.venv\Scripts\activate` انجام می‌شود.

### ۶. تست سیستم دسترسی

1. Owner `/start` را ارسال کند.
2. یک کاربر دیگر `/start` را ارسال کند و دکمهٔ «درخواست دسترسی» را بزند.
3. Owner پیام درخواست را همراه دکمه‌های تایید و رد دریافت می‌کند.
4. پس از تایید، کاربر اجازهٔ مشاهدهٔ وضعیت و سیگنال‌ها را دارد.
5. Owner می‌تواند با `/deny TELEGRAM_ID` دسترسی را حذف کند.

### ۷. تست دریافت داده و Signal

در اجرای عادی، اولین بررسی بازار پس از شروع سرویس انجام می‌شود و سپس طبق `CHECK_INTERVAL_SECONDS` تکرار می‌شود. برای بررسی وضعیت:

```text
/status
/signals
/settings
```

منطق نسخهٔ اول فقط سیگنال‌های Long را تولید می‌کند. آستانهٔ تحلیل و حدهای خروج در `strategy/strategy.py` متمرکز هستند.

اجرای تست‌های هسته:

```bash
python -m unittest discover -s trading_signal_bot/tests -p "test_*.py"
```

## Deploy روی Render

فایل `trading_signal_bot/render.yaml` یک Web Service تعریف می‌کند تا هم ربات و Scheduler اجرا شوند و هم Render بتواند `/health` را بررسی کند. این سرویس از راهکار مصنوعی برای بیدار نگه‌داشتن Render استفاده نمی‌کند.

1. Repository را به Render متصل کنید.
2. Blueprint را از روی `render.yaml` بسازید.
3. مقادیر Secret زیر را در Environment Variables سرویس وارد کنید:
   - `TELEGRAM_BOT_TOKEN`
   - `OWNER_TELEGRAM_ID`
   - `TELEGRAM_CHANNEL_ID`
4. Deploy را اجرا کنید.
5. مسیر `https://YOUR_RENDER_HOST/health` باید این پاسخ را بدهد:

```json
{"status": "ok"}
```

SQLite روی Disk متصل‌شده در `/var/data/signals.db` ذخیره می‌شود. برای اجرای چند نمونهٔ هم‌زمان از این نسخه استفاده نکنید؛ SQLite این پیاده‌سازی برای یک Worker فعال طراحی شده است.

## تنظیمات مهم

| متغیر | مقدار پیش‌فرض | توضیح |
|---|---:|---|
| `TIMEZONE` | `Asia/Tehran` | منطقهٔ زمانی نمایش پیام |
| `CHECK_INTERVAL_SECONDS` | `300` | فاصلهٔ بررسی بازار |
| `MARKET_SYMBOL` | `BTCUSDT` | نماد عمومی بازار |
| `MARKET_INTERVAL` | `5m` | بازهٔ کندل |
| `MARKET_LIMIT` | `200` | تعداد کندل دریافتی |
| `SIGNAL_EXPIRY_HOURS` | `24` | مدت اعتبار Signal |

برای بررسی هر ۱۰ دقیقه مقدار `CHECK_INTERVAL_SECONDS=600` قرار دهید.

## امنیت و محدودیت‌ها

- Tokenها فقط از Environment Variables خوانده می‌شوند.
- Token یا Secret در Log چاپ نمی‌شود.
- Permission Check روی Command و Callback انجام می‌شود.
- همهٔ داده‌های زمان‌دار در SQLite به UTC ذخیره می‌شوند.
- هیچ کلید خصوصی صرافی و هیچ Endpoint معاملاتی در پروژه وجود ندارد.
- نتیجهٔ Signal به صورت درصدی محاسبه می‌شود و سود قطعی ادعا نمی‌کند.
