# Nobat Doctor Crawler

## Description
This project is a web crawler that collects information about doctors from [nobat.ir](https://nobat.ir/). It efficiently extracts and saves the data of around 30,000 doctors, organized by city, into a CSV file. The crawler captures the following details:

- Name
- Specialty
- Profile Image URL
- City
- Street Address
- License Number
- Phone Numbers
- Waze Link
- Google Maps Link

## Features
- Fast CSV storage of doctor data
- Handles pagination for extensive city listings
- Respects server request limits to avoid overloading

## Requirements
- Python 3.7+
- aiohttp
- aiofiles
- BeautifulSoup4

## Installation
1. Clone this repository:
  
       git clone https://github.com/yourusername/Nobat-Doctor-Crawler.git
       cd Nobat-Doctor-Crawler
   
2. Install the required packages:
  
       pip install -r requirements.txt
   
## Usage
Run the crawler using the following command:


    python crawler.py

The extracted data will be stored in doctors_data.csv and the crawler's state in crawler_db.json.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.
