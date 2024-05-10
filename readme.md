# Akalmand.AI Discord Bot

Akalmand.AI is a sophisticated Discord bot that allows users to upload files to specific subjects and interactively ask questions about the contents of these files. Powered by OpenAI and LangChain, the bot delivers accurate answers and enhances learning experiences within Discord communities.

## Features

- **File Management**: Users can upload files/Urls which the bot categorizes into subjects.
- **Question Answering**: Powered by OpenAI and LangChain, the bot provides detailed answers to questions posed by users about the uploaded files.

## Prerequisites

- Python 3.10 or higher
- A Discord Bot Token
- Access to OpenAI and Deepgram APIs

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/abdulzain6/Akalmand.AI.git
cd Akalmand.AI
```

2. **Install the required Python packages:**

```bash
pip install -r requirements.txt
```

## Configuration

Configure the bot by setting the following environment variables in `config.py`:

```python
DEEPGRAM_API_KEY = "your_deepgram_api_key_here"
BOTTOKEN = "your_discord_bot_token_here"
OPENAI_API_KEY = "your_openai_api_key_here"
```

## Usage

Run the bot with:

```bash
python discord_bot.py
```

Add the bot to your Discord server and start uploading files and asking questions directly through Discord commands.

## Contributing

We encourage contributions to improve the bot's capabilities. Feel free to fork this repository, make your changes, and submit a pull request.
