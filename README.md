# Product Photoshoot Bot

Telegram bot for generating professional product photography using AI.

## Features

- 📸 **AI Product Photography**: Converts product photos into professional shots in various styles (Lifestyle, Studio, Interior, Creative).
- 🎨 **Style Generation**: Automatically analyzes the product and generates suitable styles, or generates random creative styles.
- 🤖 **AI-Powered**: Uses Anthropic Claude for prompt generation and Gemini/OpenRouter for image generation.
- 📂 **Style Management**: Save your favorite styles and re-use them later.
- 📦 **Packages & Payments**: Integrated payment system via YooKassa.
- 👥 **Referral Program**: Invite friends and earn free photoshoots.

## Tech Stack

- **Python 3.11+**
- **aiogram 3.x**
- **PostgreSQL** (SQLAlchemy + Alembic)
- **OpenRouter API** (Claude 3.5 Sonnet + Gemini 2.0 Flash)
- **YooKassa** (Payments)

## Setup

1. **Clone the repository**
2. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your credentials.
   Required: `BOT_TOKEN`, `OPENROUTER_API_KEY`, `DATABASE_URL`.

3. **Run with Docker**:
   ```bash
   docker-compose up -d
   ```

4. **Run Locally**:
   ```bash
   pip install -r requirements.txt
   alembic upgrade head
   python -m app.bot
   ```

## License

MIT
