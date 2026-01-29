
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from scraper import fetch_company_list, fetch_company_detail

# Target companies


TARGET_NAMES = [
    "(주)우리은행",
    "신한은행",
    "(주) 국민은행",
    "토스뱅크㈜",
    "신한투자증권(주)",
    "한국투자증권(주)",
    "에스케이증권주식회사",
    "대신증권"
]

def clean_value(text):
    if not text:
        return "N/A"
    return text.strip()

def format_personnel(text):
    if not text or text == "N/A":
        return text
    # 1. Remove space before '명' if exists: "32.5 명" -> "32.5명"
    # 2. Add space after '명' if not end of string: "32.5명외주" -> "32.5명 외주"
    
    # Regex sub: find (text)(number) -> (text) (number)
    text = re.sub(r'([가-힣a-zA-Z])(\d)', r'\1 \2', text)
    
    # Matches a number (integer or float) followed by optional whitespace and '명'
    text = re.sub(r'(\d+(?:\.\d+)?)\s*명', r'\1명 ', text)
    
    # Cleanup: If double spaces were created, collapse them.
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

def save_as_pdf(results, filename="comparison_report.pdf"):
    try:
        # Register Korean Font
        # Try finding a standard Korean font on Mac
        font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
        pdfmetrics.registerFont(TTFont('AppleGothic', font_path)) 
        # Note: ttc files often contain multiply fonts. Index 0 is usually Regular or Bold.
        
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        elements = []
        
        # Title
        styles = getSampleStyleSheet()
        # Create a custom style for Title with Korean support if needed, but standard might fail if not set.
        # We'll use the Table mainly.
        
        data = [["Company", "IT Investment", "Security Investment", "IT Personnel", "Dedicated Personnel"]]
        
        for r in results:
            data.append([
                r['Company'],
                r['IT Investment'],
                r['Security Investment'],
                r['IT Personnel'],
                r['Security Personnel']
            ])
            
        # Table Layout
        # Calculate col widths roughly
        col_widths = [100, 110, 110, 80, 250]
        
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'AppleGothic'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (4,0), colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('WORDWRAP', (0,0), (-1,-1), True)
        ]))
        
        elements.append(Paragraph("Financial Company Security Comparison", styles['Title']))
        elements.append(t)
        
        doc.build(elements)
        print(f"PDF saved to {filename}")
        
    except Exception as e:
        print(f"Failed to save PDF: {e}")

def extract_stats(html_content, company_name):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    it_investment = "N/A"
    sec_investment = "N/A"
    it_personnel = "N/A"
    sec_personnel = "N/A"
    
    cells = soup.find_all(['th', 'td'])
    
    for i, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        
        # IT Investment
        if "정보기술부문 투자액" in text:
            siblings = cell.find_next_siblings(['td'])
            if siblings and len(siblings) > 0:
                it_investment = siblings[-1].get_text(strip=True)

        # Security Investment
        if "정보보호부문 투자액" in text:
            siblings = cell.find_next_siblings(['td'])
            if siblings and len(siblings) > 0:
                sec_investment = siblings[-1].get_text(strip=True)
        
        # IT Personnel
        if "정보기술부문 인력" in text:
             siblings = cell.find_next_siblings(['td'])
             if siblings and len(siblings) > 0:
                 it_personnel = format_personnel(siblings[-1].get_text(strip=True))

        # Security Personnel
        if "정보보호부문 전담인력" in text or "정보보호 전담인력" in text:
             siblings = cell.find_next_siblings(['td'])
             if siblings and len(siblings) > 0:
                 sec_personnel = format_personnel(siblings[-1].get_text(strip=True))
    
    return it_investment, sec_investment, it_personnel, sec_personnel

def main():
    print(f"Fetch list (checking 10 pages)...")
    all_companies = fetch_company_list(max_pages=10)
    
    print(f"Total companies found: {len(all_companies)}")
    
    results = []
    
    for target in TARGET_NAMES:
        print(f"Searching for: {target}")
        found = False
        for company in all_companies:
            # Loose matching just in case of whitespace diffs
            if company['name'].strip() == target.strip():
                print(f"  Found! Fetching details (ID: {company['publish_no']})...")
                details = fetch_company_detail(company['publish_no'])
                if details and details.get('table_html'):
                    it_inv, sec_inv, it_per, sec_per = extract_stats(details['table_html'], target)
                    results.append({
                        "Company": target,
                        "IT Investment": it_inv,
                        "Security Investment": sec_inv,
                        "IT Personnel": it_per,
                        "Security Personnel": sec_per
                    })
                else:
                    results.append({
                        "Company": target, 
                        "IT Investment": "Error", 
                        "Security Investment": "Error",
                        "IT Personnel": "Error", 
                        "Security Personnel": "Error"
                    })
                found = True
                break
        
        if not found:
            print(f"  Not found in list.")
            results.append({
                "Company": target, 
                "IT Investment": "Not Found", 
                "Security Investment": "Not Found",
                "IT Personnel": "Not Found", 
                "Security Personnel": "Not Found"
            })


    # Print Table
    df = pd.DataFrame(results)
    table_str = ""
    try:
        table_str = df.to_markdown(index=False)
    except ImportError:
        table_str = df.to_string(index=False)
    
    print("\n\n=== Comparison Table ===")
    print(table_str)
    
    with open("latest_results.md", "w", encoding="utf-8") as f:
        f.write(table_str)

    print("\n\n=== Raw Results ===")
    print(results)
    
    save_as_pdf(results, "financial_security_comparison.pdf")

if __name__ == "__main__":
    main()
