import aiohttp
import asyncio
import aiofiles
import csv
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class NobatCrawler:
    BASE_URL = "https://nobat.ir"
    CITIES_API = f"{BASE_URL}/api/public/cities"
    CSV_FILE = "doctors_data.csv"
    DB_FILE = "crawler_db.json"

    def __init__(self):
        self.db = None
        self.session = None
        self.last_crawled_page = 0

    async def load_database(self):
        try:
            async with aiofiles.open(self.DB_FILE, 'r') as f:
                content = await f.read()
                self.db = json.loads(content)
                if not isinstance(self.db.get("visited_cities"), dict):
                    self.db["visited_cities"] = {}
        except FileNotFoundError:
            self.db = {"visited_cities": {}, "visited_doctors": []}

    async def save_database(self):
        async with aiofiles.open(self.DB_FILE, 'w') as f:
            await f.write(json.dumps(self.db))

    async def get_cities(self):
        async with self.session.get(self.CITIES_API) as response:
            return await response.json()

    async def extract_doctor_info(self, doctor):
        try:
            name = doctor.select_one('h2.doctor-ui-name span').text.strip()
            specialty = doctor.select_one('span.doctor-ui-specialty').text.strip()
            image_url = doctor.select_one('div.doctor-ui-profile img')['data-src']
            
            doctor_url = doctor['href']
            doctor_detail_url = urljoin(self.BASE_URL, doctor_url)
            offices = await self.get_doctor_detail_info(doctor_detail_url)
            
            return name, specialty, image_url, offices
        except Exception as e:
            print(f"Error extracting doctor info: {e}")
            return None, None, None, []

    async def get_doctor_detail_info(self, doctor_url):
        async with self.session.get(doctor_url) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            
            license_num = soup.select_one('div.doctor-code span:nth-child(2)').text.strip() if soup.select_one('div.doctor-code span:nth-child(2)') else 'N/A'
            
            offices_data = []
            offices = soup.select('div.locations-panel-item')
            for office in offices:
                city = office.select_one('strong').text.strip() if office.select_one('strong') else 'N/A'
                street_address = office.select_one('p').text.strip() if office.select_one('p') else 'N/A'
                doctor_data = soup.select_one('div.offices div.office')
                office_id = doctor_data['data-officeid'] if doctor_data else None
                phone_numbers = await self.get_phone_numbers(office_id) 
                
                waze_link = office.select_one('a[href*="waze.com"]')['href'] if office.select_one('a[href*="waze.com"]') else 'N/A'
                google_maps_link = office.select_one('a[href*="google.com/maps"]')['href'] if office.select_one('a[href*="google.com/maps"]') else 'N/A'
                
                offices_data.append({
                    "city": city,
                    "street_address": street_address,
                    "license_num": license_num,
                    "phone_numbers": ','.join(phone_numbers),
                    "waze_link": waze_link,
                    "google_maps_link": google_maps_link
                })
            
            return offices_data

    async def get_phone_numbers(self, office_id):
        phone_numbers = []
        api_url = urljoin(self.BASE_URL, "/api/public/doctor/office/tells")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "multipart/form-data; boundary=---------------------------33786845221545698634485778826",
            "Origin": "https://nobat.ir",
            "Referer": "https://nobat.ir/s",
            "Cookie": "defaultCity=1; _ga_KEKNLD11WM=GS1.1.1723455485.4.1.1723456752.0.0.0; _ga=GA1.1.649793245.1722172720; PHPSESSID=0fc9cgj37k849041msbpdqk1qr; o_reged=1723455606",
        }
        
        data = (f"""-----------------------------33786845221545698634485778826
Content-Disposition: form-data; name="office_id"

{office_id}
-----------------------------33786845221545698634485778826--"""
        )
        
        async with self.session.post(api_url, headers=headers, data=data) as response:
            if response.status == 200:
                phone_data = await response.json()
                for entry in phone_data:
                    phone_numbers.append(entry['tel'])
        
        return phone_numbers

    async def crawl_city(self, city_url,cityname, start_page=1):
        page = start_page
        while True:
            url = f"{self.BASE_URL}{city_url}/page-{page}" if page > 1 else f"{self.BASE_URL}{city_url}"
            print(f"Crawling page {page}: {url}")
            
            async with self.session.get(url) as response:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                
                empty_div = soup.select_one('div.empty')
                if empty_div:
                    print(f"Page {page} is empty, moving to next city.")
                    break
                
                doctors = soup.select('a.doctor-ui')
                if not doctors:
                    print(f"No doctors found on page {page}, moving to next city.")
                    break
                
                for doctor in doctors:
                    name, specialty, image_url, offices = await self.extract_doctor_info(doctor)
                    if name and name not in self.db["visited_doctors"]:
                        self.db["visited_doctors"].append(name)
                        for office in offices:
                            yield name, specialty, image_url, cityname, office["street_address"], office["license_num"], office["phone_numbers"], office["waze_link"], office["google_maps_link"]
            
            self.last_crawled_page = page
            page += 1
            await asyncio.sleep(2)  # Respect the server

    def get_last_crawled_page(self):
        return self.last_crawled_page

    async def run(self):
        await self.load_database()
        
        async with aiohttp.ClientSession() as self.session:
            cities = await self.get_cities()
            
            async with aiofiles.open(self.CSV_FILE, 'a', newline='', encoding='utf-8') as afile:
                writer = csv.writer(afile)
                if await afile.tell() == 0:  
                    with open(self.CSV_FILE, 'a', newline='', encoding='utf-8') as sync_file:
                        writer = csv.writer(sync_file)
                        writer.writerow(['Name', 'Specialty', 'Image URL', 'City', 'Street Address', 'License Number', 'Phone Numbers', 'Waze Link', 'Google Maps Link'])

                
                for city in cities:
                    city_url = city['url']
                    start_page = self.db["visited_cities"].get(city_url, 1)
                    print(f"Crawling {city['tit']} from page {start_page}...")
                    async for doctor_info in self.crawl_city(city_url, city['tit'],start_page=start_page):
                        async with aiofiles.open(self.CSV_FILE, 'a', newline='', encoding='utf-8') as afile:
                            async for doctor_info in self.crawl_city(city_url,city['tit'],start_page):
                                with open(self.CSV_FILE, 'a', newline='', encoding='utf-8') as sync_file:
                                    writer = csv.writer(sync_file)
                                    writer.writerow(doctor_info)
                    self.db["visited_cities"][city_url] = self.get_last_crawled_page()
                    await self.save_database()
                    print(f"Finished crawling {city['tit']} up to page {self.get_last_crawled_page()}")
                    await asyncio.sleep(2)  # Respect the server

async def main():
    crawler = NobatCrawler()
    await crawler.run()

if __name__ == "__main__":
    asyncio.run(main())
