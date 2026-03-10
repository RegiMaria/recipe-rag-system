import requests
from bs4 import BeautifulSoup
import yaml

class CrawlerAgent:
    def __init__(self, config_path="config/sources.yaml"):
        with open(config_path, "r") as f:
            self.sources = yaml.safe_load(f)["sources"]

    def crawl(self):
        all_urls = []
        for source in self.sources:
            response = requests.get(source["url"])
            soup = BeautifulSoup(response.text, "html.parser")
            urls = [a["href"] for a in soup.find_all("a", href=True)]
            all_urls.extend(urls)
        return all_urls

if __name__ == "__main__":
    crawler = CrawlerAgent()
    urls = crawler.crawl()
    print("Found URLs:", urls)