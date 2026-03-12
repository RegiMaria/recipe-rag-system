import re
import time
import yaml
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

from storage.gcs_client import GCSClient


class CollectorAgent:
    """
    Recebe URLs de receitas (vindas do CrawlerAgent), baixa o HTML de cada página
    e armazena no GCS como Data Lake bruto.

    Estrutura no GCS:
        raw/html/{source_name}/{YYYY-MM-DD}/{slug}.html
    """

    REQUEST_TIMEOUT = 15  # segundos
    RATE_LIMIT_DELAY = 2  # segundos entre requisições

    def __init__(self, config_path: str = "config/sources.yaml"):
        with open(config_path, "r") as f:
            sources = yaml.safe_load(f)["sources"]

        # Mapeia domínio → nome da fonte para organizar o GCS
        # ex: "tudogostoso.com.br" → "tudogostoso"
        self._domain_to_source = {
            urlparse(s["url"]).netloc.lstrip("www."): s["name"]
            for s in sources
        }

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        self.gcs = GCSClient()

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _source_name(self, url: str) -> str:
        """Resolve o nome da fonte a partir do domínio da URL."""
        netloc = urlparse(url).netloc.lstrip("www.")
        # Tenta match exato, depois match parcial (subdomínio ou path diferente)
        if netloc in self._domain_to_source:
            return self._domain_to_source[netloc]
        for domain, name in self._domain_to_source.items():
            if domain in netloc:
                return name
        return "desconhecido"

    def _url_to_slug(self, url: str) -> str:
        """Converte URL em slug legível para nome do arquivo no GCS."""
        path = urlparse(url).path.strip("/")
        slug = path.split("/")[-1] or "index"
        slug = re.sub(r"[^a-z0-9\-]", "-", slug.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug[:120]  # limita tamanho

    def _gcs_path(self, url: str, date_str: str) -> str:
        """Monta o caminho do objeto no GCS."""
        source = self._source_name(url)
        slug = self._url_to_slug(url)
        return f"raw/html/{source}/{date_str}/{slug}.html"

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def collect(self, urls: list[str]) -> list[dict]:
        """
        Baixa e armazena o HTML de cada URL no GCS.

        Args:
            urls: lista de URLs de receitas (saída do CrawlerAgent)

        Returns:
            Lista de dicts com metadados de cada coleta:
            {url, source, gcs_uri, timestamp, status}
        """
        results = []
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for url in urls:
            gcs_path = self._gcs_path(url, date_str)

            # Pula se já foi coletado hoje (idempotência)
            if self.gcs.blob_exists(gcs_path):
                print(f"[SKIP] Já existe no GCS: {gcs_path}")
                results.append({"url": url, "status": "skipped", "gcs_uri": f"gs://{self.gcs.bucket_name}/{gcs_path}"})
                continue

            try:
                print(f"[GET] {url}")
                response = requests.get(url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()

                gcs_uri = self.gcs.upload_html(response.text, gcs_path)
                timestamp = datetime.now(timezone.utc).isoformat()

                print(f"[OK]  Salvo em {gcs_uri}")
                results.append({
                    "url": url,
                    "source": self._source_name(url),
                    "gcs_uri": gcs_uri,
                    "timestamp": timestamp,
                    "status": "collected",
                })

            except requests.HTTPError as e:
                print(f"[WARN] HTTP {e.response.status_code} em {url}")
                results.append({"url": url, "status": f"http_error_{e.response.status_code}"})

            except requests.RequestException as e:
                print(f"[ERROR] Falha de rede em {url}: {e}")
                results.append({"url": url, "status": "network_error"})

            time.sleep(self.RATE_LIMIT_DELAY)

        collected = sum(1 for r in results if r["status"] == "collected")
        print(f"\nColeta concluída: {collected}/{len(urls)} páginas salvas no GCS.")
        return results


if __name__ == "__main__":
    # Teste rápido com URLs reais de receitas
    sample_urls = [
        "https://www.panelinha.com.br/receita/pudim-de-leite",
        "https://www.tudogostoso.com.br/receita/1-bolo-de-cenoura.html",
    ]
    agent = CollectorAgent()
    results = agent.collect(sample_urls)
