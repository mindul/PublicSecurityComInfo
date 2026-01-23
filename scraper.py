import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from urllib.parse import parse_qs, urlparse
import re

# Base URL for the list
BASE_LIST_URL = "https://isds.kisa.or.kr/kr/publish/list.do"
# Base URL for the detail view
BASE_DETAIL_URL = "https://isds.kisa.or.kr/kr/publish/publishView.do"

def fetch_company_list(max_pages=4):
    """
    Fetches the list of companies from the first `max_pages`.
    Returns a list of dictionaries: [{'name': '...', 'publish_no': '...', 'link': '...'}, ...]
    """
    company_list = []
    
    # query parameters based on user's URL 
    search_keyword = "금융 및 보험업"
    
    for page in range(1, max_pages + 1):
        params = {
            'menuNo': '204942',
            'pageIndex': page,
            'publishNo': '',
            'listFlag': 'list',
            'searchCnd': '',
            'searchWrd': search_keyword,
            'searchPublishYear': '2025',
            'searchDutyYn': '',
            'searchPublishModYn': ''
        }
        
        try:
            print(f"Fetching page {page}...")
            response = requests.get(BASE_LIST_URL, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.select(".m_title a")
            
            for link in links:
                href = link.get('href')
                # Structural Company Name Extraction
                # User requirement: Extract text located strictly between <a> tag and <img> tag (before img).
                title = ""
                for item in link.contents:
                    if item.name == 'img':
                        break
                    if isinstance(item, str):
                        title += item
                
                title = title.strip()
                if not title:
                    # Fallback if no text found via structure, use get_text
                     title = link.get_text(strip=True)

                # Extract publishNo from href using regex
                match = re.search(r'publishNo=(\d+)', href)
                if not match:
                    match = re.search(r'\d{4}', href)
                
                if match:
                    publish_no = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    
                    if publish_no:
                        company_list.append({
                            'name': title,
                            'publish_no': publish_no,
                            'link': f"{BASE_DETAIL_URL}?menuNo=204942&pageIndex=1&publishNo={publish_no}"
                        })
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            
    return company_list

def fetch_company_detail(publish_no):
    """
    Fetches the details for a specific company by publish_no.
    Returns a dictionary with 'name' and 'html_table'.
    """
    url = f"{BASE_DETAIL_URL}?menuNo=204942&pageIndex=1&publishNo={publish_no}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract Company Name
        company_name = "Unknown"
        
        # Method: Look in the first table (Corporate Info) for "기업명"
        tables = soup.find_all('table')
        if tables:
            corp_info_table = tables[0]
            for row in corp_info_table.find_all('tr'):
                # Check both th and td for "기업명" key
                cells = row.find_all(['th', 'td'])
                for i, cell in enumerate(cells):
                    if "기업명" in cell.get_text():
                        # The value should be in the next cell
                        if i + 1 < len(cells):
                            company_name = cells[i+1].get_text(strip=True)
                        break
                if company_name != "Unknown":
                    break
        
        # 2. Extract "Information Security Status" Table
        target_table_html = "<p class='error-text'>정보보호 현황 테이블을 찾을 수 없습니다.</p>"
        keywords = ["정보보호 투자 현황", "정보보호 인력 현황", "정보보호 현황"] 
        # Added "정보보호 현황" as a broad fallback if the table header itself says it.
        # But strictly, the request listed "1. 정보보호 투자 현황" etc which are likely Row Headers in the table.
        
        for table in tables:
            table_text = table.get_text()
            # Check if likely the big status table
            if "정보보호 투자 현황" in table_text or "정보보호 인력 현황" in table_text:
                # Cleanup: Remove "도움말" (Help) and "닫기" (Close) buttons/links
                # Cleanup: Remove "도움말" (Help) and "닫기" (Close) buttons/links
                for bad_text in ["도움말", "닫기"]:
                    # 1. Find elements that directy contain the text
                    # We look for any tag that contains the text
                    for element in table.find_all(string=re.compile(bad_text)):
                         # Traverse up to find a container (a, button, span, or even div if it looks like a button)
                         parent = element.parent
                         while parent and parent.name not in ['table', 'body', 'html', 'tr']:
                             # If it's a clickable-like element or a span wrapper often used for buttons
                             if parent.name in ['a', 'button', 'span', 'div']:
                                 # Double check if removing this parent removes the bad text
                                 if bad_text in parent.get_text():
                                     parent.decompose()
                                     break
                             parent = parent.parent
                    
                    # 2. Also look for images with alt text
                    for img in table.find_all('img', alt=re.compile(bad_text)):
                        img.decompose()

                if table.get('class'):
                    table['class'].append('extracted-table')
                else:
                    table['class'] = ['extracted-table']
                target_table_html = str(table)
                break
        
        return {
            'name': company_name,
            'publish_no': publish_no,
            'table_html': target_table_html
        }

    except Exception as e:
        print(f"Error fetching details for {publish_no}: {e}")
        return None

if __name__ == "__main__":
    # Test for the specific case requested by user: publishNo=3626
    print("Testing for PublishNo: 3626 ((주)우리은행)")
    details = fetch_company_detail('3626')
    if details:
        print(f"Name Found: {details['name']}")
        print(f"Table Found: {'Yes' if 'table' in details['table_html'] else 'No'}")
        print("Table Preview:")
        print(details['table_html'][:500])
    else:
        print("Failed to fetch details.")

    # Also briefly test list fetching to verify cleaning
    print("\nTesting List Fetching (Page 1)...")
    lst = fetch_company_list(max_pages=1)
    for c in lst[:5]:
        print(f"Cleaned Name: {c['name']} (ID: {c['publish_no']})")
