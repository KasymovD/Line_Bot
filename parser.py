import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler()
    ]
)

def get_page(url, headers, retries=3):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        if retries > 0:
            logging.warning(f"Ошибка при запросе {url}: {e}. Повторная попытка ({retries})...")
            time.sleep(2)
            return get_page(url, headers, retries - 1)
        else:
            logging.error(f"Не удалось получить страницу {url} после нескольких попыток.")
            return None

def parse_page(html):
    soup = BeautifulSoup(html, 'lxml')
    products = []
    
    for item in soup.find_all('div', class_='product-item'):
        try:
            name = item.find('h2', class_='product-name').get_text(strip=True)
            price = item.find('span', class_='price').get_text(strip=True)
            image_url = item.find('img', class_='product-image')['src']
            product_url = item.find('a', class_='product-link')['href']
            
            products.append({
                'name': name,
                'price': price,
                'image_url': image_url,
                'product_url': product_url
            })
        except AttributeError as e:
            logging.warning(f"Не удалось спарсить элемент: {e}")
            continue
    return products

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    logging.info(f"Данные успешно сохранены в {filename}")

def main():
    base_url = 'https://example.com/products?page={}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/85.0.4183.102 Safari/537.36'
    }
    
    all_products = []
    total_pages = 10 

    for page in range(1, total_pages + 1):
        url = base_url.format(page)
        logging.info(f"Парсинг страницы {page}: {url}")
        html = get_page(url, headers)
        if html:
            products = parse_page(html)
            all_products.extend(products)
            logging.info(f"Найдено продуктов на странице {page}: {len(products)}")
        else:
            logging.warning(f"Пропуск страницы {page} из-за ошибки загрузки.")
        
        time.sleep(random.uniform(1, 3))
    
    save_to_csv(all_products, 'products.csv')

if __name__ == '__main__':
    main()
