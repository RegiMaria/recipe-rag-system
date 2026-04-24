import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import yaml
import time

logger = logging.getLogger(__name__)

# 01 - O CrawlerAgent é o ponto de entrada do pipeline 
# ele é responsável por descobrir e coletar URLs que serão processadas nas etapas seguintes
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

    def _is_same_domain(self, url, base_url):
        """Verifica se a URL pertence ao mesmo domínio da fonte."""
        return urlparse(url).netloc == urlparse(base_url).netloc

    def _find_next_page(self, soup, base_url):
        """
        Detecta o link da próxima página de listagem.

        Estratégias (em ordem de prioridade):
        1. <a rel="next"> ou <link rel="next"> — padrão semântico HTML
        2. Links cujo texto seja uma variação de "próxima" ou "next"

        Apenas retorna URLs do mesmo domínio da fonte.
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
                if self._is_same_domain(href, base_url):
                    return href

        # 2. Link com texto "próxima" / "next" / "›" / "»"
        next_labels = {"próxima", "proxima", "next", "›", "»", "seguinte"}
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if text in next_labels:
                href = a["href"]
                if href.startswith("/"):
                    href = base_url + href
                if self._is_same_domain(href, base_url):
                    return href

        return None

    def _crawl_source(self, source):
        """Raspa todas as páginas de listagem de uma fonte, respeitando max_pages."""
        found = {}  # url → {url, source_name} — dict evita duplicatas mantendo contexto
        parsed = urlparse(source["url"])
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        recipe_path = source.get("recipe_path", "/receita/")
        max_pages = source.get("max_pages", 5)
        source_name = source["name"]

        current_url = source["url"]
        page = 1

        while current_url and page <= max_pages:
            logger.info("[%s] p%d/%d — %s", source_name, page, max_pages, current_url)
            try:
                response = requests.get(current_url, headers=self.headers, timeout=10)
                response.raise_for_status()
            except requests.Timeout:
                logger.warning("[%s] Timeout em %s — abortando fonte", source_name, current_url)
                break
            except requests.ConnectionError:
                logger.error("[%s] Falha de conexão em %s — abortando fonte", source_name, current_url)
                break
            except requests.HTTPError as e:
                status = e.response.status_code
                if 400 <= status < 500:
                    logger.warning("[%s] HTTP %d em %s — página inválida, abortando paginação", source_name, status, current_url)
                else:
                    logger.error("[%s] HTTP %d em %s — erro no servidor, abortando fonte", source_name, status, current_url)
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Coleta links de receitas desta página
            for a in soup.find_all("a", href=True):
                link = a["href"]
                if link.startswith("/"):
                    link = base_url + link
                if self._is_same_domain(link, base_url) and self.is_recipe_url(link, recipe_path):
                    found[link] = {"url": link, "source_name": source_name}

            # Avança para a próxima página
            next_url = self._find_next_page(soup, base_url)
            if next_url == current_url:  # evita loop infinito
                break
            current_url = next_url
            page += 1
            time.sleep(1)

        return list(found.values())

    def crawl(self):
        """
        Retorna lista de dicts com url e source_name de cada receita encontrada.

        Exemplo de saída:
            [{"url": "https://panelinha.com.br/receita/pudim", "source_name": "panelinha"}, ...]
        """
        all_entries = {}  # url → entry — deduplicação global entre fontes
        for source in self.sources:
            logger.info("--- Explorando: %s ---", source["name"])
            try:
                entries = self._crawl_source(source)
            except Exception:
                logger.exception("Falha inesperada ao processar fonte '%s' — continuando", source["name"])
                continue
            for entry in entries:
                all_entries[entry["url"]] = entry
            logger.info("%d receitas encontradas em %s", len(entries), source["name"])

        return list(all_entries.values())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    crawler = CrawlerAgent()
    entries = crawler.crawl()
    logger.info("Total de receitas encontradas: %d", len(entries))
    for e in entries[:5]:
        logger.info("  [%s] %s", e["source_name"], e["url"])
