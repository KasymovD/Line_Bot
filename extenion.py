import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
import logging
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def fetch(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        logging.error(f"Ошибка при запросе {url}: {e}")
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

async def main_async():
    base_url = 'https://example.com/products?page={}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/85.0.4183.102 Safari/537.36'
    }
    total_pages = 10
    all_products = []

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for page in range(1, total_pages + 1):
            url = base_url.format(page)
            tasks.append(fetch(session, url))
        
        pages_content = await asyncio.gather(*tasks)
        
        for page_number, html in enumerate(pages_content, start=1):
            if html:
                products = parse_page(html)
                all_products.extend(products)
                logging.info(f"Найдено продуктов на странице {page_number}: {len(products)}")
            else:
                logging.warning(f"Пропуск страницы {page_number} из-за ошибки загрузки.")
            
            await asyncio.sleep(random.uniform(1, 3))
    
    df = pd.DataFrame(all_products)
    df.to_csv('products_async.csv', index=False, encoding='utf-8-sig')
    logging.info("Данные успешно сохранены в products_async.csv")

if __name__ == '__main__':
    asyncio.run(main_async())
