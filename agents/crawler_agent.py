import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import yaml
import time

class CrawlerAgent:
    def __init__(self, config_path="config/sources.yaml"):
        with open(config_path, "r") as f:
            self.sources = yaml.safe_load(f)["sources"]
        
        # Identificação para os sites bloquearem a gente
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def is_recipe_url(self, url):
        """Filtra se a URL realmente parece uma página de receita."""
        keywords = ['/receita/', '/receitas/', '/prato/']
        return any(key in url.lower() for key in keywords)

    def crawl(self):
        all_urls = set() # Usamos set para evitar duplicatas automaticamente
        for source in self.sources:
            print(f"--- Explorando: {source['name']} ---")
            try:
                response = requests.get(source["url"], headers=self.headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Pegamos todos os links
                    links = [a["href"] for a in soup.find_all("a", href=True)]
                    
                    parsed = urlparse(source["url"])
                    base_url = f"{parsed.scheme}://{parsed.netloc}"

                    for link in links:
                        # Tratar links relativos (ex: /receita/123 -> https://site.com/receita/123)
                        if link.startswith('/'):
                            link = base_url + link
                        
                        if self.is_recipe_url(link):
                            all_urls.add(link)
                
                # Pausa para não sobrecarregar o site
                time.sleep(1) 
            except Exception as e:
                print(f"Erro ao acessar {source['name']}: {e}")
        
        return list(all_urls)

if __name__ == "__main__":
    crawler = CrawlerAgent()
    urls = crawler.crawl()
    print(f"\nTotal de receitas encontradas: {len(urls)}")
    for u in list(urls)[:5]: # Mostra as 5 primeiras
        print(f"Encontrada: {u}")