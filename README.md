# Resume Parser Bot

A Telegram bot that parses resumes from Work.ua and Robota.ua.

## Prerequisites

Make sure you have the following installed: Python 3.12 or later, pip (Python package manager), and Git.

## Getting Started

Follow these steps to set up and run the project on your local machine.

### 1. Clone the Repository
Run the following commands in your terminal:
```bash
git clone https://github.com/bodick1love/vacancy_scaper.git
cd resume-parser-bot
```

### 2. Create a Virtual Environment
Run the following command to create a virtual environment:
```bash
python -m venv .venv
```

Then activate the virtual environment:
- On Windows: `venv\Scripts\activate`
- On macOS/Linux: `source venv/bin/activate`

### 3. Install Requirements
Install the required dependencies by running:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root, copy content from .env.example and fill the following fields
```
ROBOTA_UA_USERNAME
ROBOTA_UA_PASSWORD
SCRAPER_API_KEY
TELEGRAM_BOT_TOKEN
```

### 5. Run the Bot
Run the bot using the following command:
```bash
python src/main.py
```


## Features

- Parses resumes from two specified websites.
- Extracts and formats relevant data for easier processing.

## Contributing

Feel free to fork the repository and submit pull requests with improvements or additional features.