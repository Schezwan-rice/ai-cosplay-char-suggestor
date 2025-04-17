---

# AI Cosplay Character Suggestor

A Flask-based web application that suggests cosplay characters using AI.

## Prerequisites

- Python 3.6 or higher
- `pip` package manager

## Setup Instructions

### 1. Create a Virtual Environment

It's recommended to use a virtual environment to manage dependencies:

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

Install the required packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root directory and add your `GROQ_API_KEY`:

```
GROQ_API_KEY=your_api_key_here
```

Ensure that the `.env` file is included in your `.gitignore` to prevent exposing sensitive information.

### 4. Run the Flask Application

Start the Flask app:

```bash
python app.py
```

By default, the application will run on `http://localhost:5000/`.

### 5. Access the Application

Open your web browser and navigate to:

```
http://localhost:5000/
```

You should see the AI Cosplay Character Suggestor interface.

---
