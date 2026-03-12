import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import yaml
import time


class CrawlerAgent:
    def __init__(self, config_path="config/sources.yaml"):
        with open(config_path, "r") as f:
            self.sources = yaml.safe_load(f)["sources"]

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def is_recipe_url(self, url, recipe_path):
        """Filtra se a URL pertence ao padrão de receita da fonte."""
        return recipe_path.lower() in url.lower()

    def _find_next_page(self, soup, base_url):
        """
        Detecta o link da próxima página de listagem.

        Estratégias (em ordem de prioridade):
        1. <a rel="next"> ou <link rel="next"> — padrão semântico HTML
        2. Links cujo texto seja uma variação de "próxima" ou "next"
        """
        # 1. rel="next" em <a> ou <link>
        for tag in soup.find_all(["a", "link"], rel=True):
            rels = tag.get("rel", [])
            if isinstance(rels, str):
                rels = [rels]
            if "next" in rels and tag.get("href"):
                href = tag["href"]
                if href.startswith("/"):
                    href = base_url + href
                return href

        # 2. Link com texto "próxima" / "next" / "›" / "»"
        next_labels = {"próxima", "proxima", "next", "›", "»", "seguinte"}
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if text in next_labels:
                href = a["href"]
                if href.startswith("/"):
                    href = base_url + href
                return href

        return None

    def _crawl_source(self, source):
        """Raspa todas as páginas de listagem de uma fonte, respeitando max_pages."""
        found_urls = set()
        parsed = urlparse(source["url"])
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        recipe_path = source.get("recipe_path", "/receita/")
        max_pages = source.get("max_pages", 5)

        current_url = source["url"]
        page = 1

        while current_url and page <= max_pages:
            print(f"  [p{page}/{max_pages}] {current_url}")
            try:
                response = requests.get(current_url, headers=self.headers, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"  [ERROR] {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Coleta links de receitas desta página
            for a in soup.find_all("a", href=True):
                link = a["href"]
                if link.startswith("/"):
                    link = base_url + link
                if self.is_recipe_url(link, recipe_path):
                    found_urls.add(link)

            # Avança para a próxima página
            next_url = self._find_next_page(soup, base_url)
            if next_url == current_url:  # evita loop infinito
                break
            current_url = next_url
            page += 1
            time.sleep(1)

        return found_urls

    def crawl(self):
        all_urls = set()
        for source in self.sources:
            print(f"--- Explorando: {source['name']} ---")
            urls = self._crawl_source(source)
            print(f"    {len(urls)} receitas encontradas em {source['name']}")
            all_urls.update(urls)

        return list(all_urls)


if __name__ == "__main__":
    crawler = CrawlerAgent()
    urls = crawler.crawl()
    print(f"\nTotal de receitas encontradas: {len(urls)}")
    for u in urls[:5]:
        print(f"  {u}")
