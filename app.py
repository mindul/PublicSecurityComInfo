from flask import Flask, render_template, jsonify
import scraper
import json
import os

app = Flask(__name__)

# Cache for company list to avoid re-scraping on every reload
# In a real app, this might be a database or Redis
COMPANY_LIST_CACHE = []

def get_companies():
    global COMPANY_LIST_CACHE
    if not COMPANY_LIST_CACHE:
        # Try to load from json if exists
        # Or scrape fresh
        print("Scraping company list...")
        # Scrape 4 pages as requested
        COMPANY_LIST_CACHE = scraper.fetch_company_list(max_pages=4)
    return COMPANY_LIST_CACHE

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/home')
def home():
    companies = get_companies()
    return render_template('home.html', companies=companies)

@app.route('/api/company/<publish_no>')
def company_detail(publish_no):
    try:
        details = scraper.fetch_company_detail(publish_no)
        if details:
            return jsonify(details)
        else:
            return jsonify({'error': 'Details not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
