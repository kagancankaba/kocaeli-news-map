# Kocaeli Local News Map

A desktop application that automatically scrapes, classifies, and visualizes local news from Kocaeli province on an interactive Google Maps interface. Developed with Python using a modular architecture.

## What It Does

Scrapes news from 4 local Kocaeli news sources (Çağdaş Kocaeli, Özgür Kocaeli, Ses Kocaeli, Bizim Yaka) for the last 1-3 days. Each article is cleaned, classified into one of 5 categories using keyword scoring, and geolocated using Google Geocoding API. Duplicate articles from different sources are merged using TF-IDF cosine similarity. All data is stored in MongoDB and displayed on an interactive map with color-coded markers.

## News Categories

- Traffic Accident — red markers
- Fire — orange markers
- Power Outage — yellow markers
- Theft — purple markers
- Cultural Events — green markers

## Tech Stack

- Python, Tkinter, tkintermapview
- BeautifulSoup (web scraping)
- MongoDB (storage + geocoding cache)
- Google Geocoding API + Google Maps Tiles
- Scikit-learn TF-IDF (duplicate detection)

## Project Structure

- `scraper.py` — Archive page scraping and article extraction
- `preprocessor.py` — HTML cleaning and text normalization
- `classifier.py` — Keyword-based news classification
- `konum_bulucu.py` — Location extraction and geocoding
- `database.py` — MongoDB operations
- `similarity.py` — TF-IDF cosine similarity for duplicate detection
- `app.py` — Main GUI application
- `report.pdf` — Full project report

## Setup

1. Install dependencies:

pip install -r requirements.txt

2. Create a `.env` file in the project root with your credentials:

MONGODB_URI=your_mongodb_connection_string
GOOGLE_API_KEY=your_google_api_key

3. Run the application:

python app.py