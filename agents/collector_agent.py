import re
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

from storage.gcs_client import GCSClient


class CollectorAgent:
    """
    Recebe entradas do CrawlerAgent ({url, source_name}), baixa o HTML de cada página
    e armazena no GCS como Data Lake bruto.

    Estrutura no GCS:
        raw/html/{source_name}/{YYYY-MM-DD}/{slug}.html
    """

    REQUEST_TIMEOUT = 15  # segundos
    RATE_LIMIT_DELAY = 2  # segundos entre requisições

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        self.gcs = GCSClient()

    def _url_to_slug(self, url: str) -> str:
        """Converte URL em slug legível para nome do arquivo no GCS."""
        path = urlparse(url).path.strip("/")
        slug = path.split("/")[-1] or "index"
        slug = re.sub(r"[^a-z0-9\-]", "-", slug.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug[:120]

    def _gcs_path(self, url: str, source_name: str, date_str: str) -> str:
        """Monta o caminho do objeto no GCS."""
        slug = self._url_to_slug(url)
        return f"raw/html/{source_name}/{date_str}/{slug}.html"

    def collect(self, entries: list[dict]) -> list[dict]:
        """
        Baixa e armazena o HTML de cada entrada no GCS.

        Args:
            entries: saída do CrawlerAgent — lista de {url, source_name}

        Returns:
            Lista de dicts com metadados de cada coleta:
            {url, source_name, gcs_uri, timestamp, status}
        """
        results = []
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for entry in entries:
            url = entry["url"]
            source_name = entry["source_name"]
            gcs_path = self._gcs_path(url, source_name, date_str)

            # Pula se já foi coletado hoje (idempotência)
            if self.gcs.blob_exists(gcs_path):
                print(f"[SKIP] Já existe no GCS: {gcs_path}")
                results.append({"url": url, "source_name": source_name, "status": "skipped", "gcs_uri": f"gs://{self.gcs.bucket_name}/{gcs_path}"})
                continue

            try:
                print(f"[GET] [{source_name}] {url}")
                response = requests.get(url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()

                gcs_uri = self.gcs.upload_html(response.text, gcs_path)
                timestamp = datetime.now(timezone.utc).isoformat()

                print(f"[OK]  Salvo em {gcs_uri}")
                results.append({
                    "url": url,
                    "source_name": source_name,
                    "gcs_uri": gcs_uri,
                    "timestamp": timestamp,
                    "status": "collected",
                })

            except requests.HTTPError as e:
                print(f"[WARN] HTTP {e.response.status_code} em {url}")
                results.append({"url": url, "source_name": source_name, "status": f"http_error_{e.response.status_code}"})

            except requests.RequestException as e:
                print(f"[ERROR] Falha de rede em {url}: {e}")
                results.append({"url": url, "source_name": source_name, "status": "network_error"})

            time.sleep(self.RATE_LIMIT_DELAY)

        collected = sum(1 for r in results if r["status"] == "collected")
        print(f"\nColeta concluída: {collected}/{len(entries)} páginas salvas no GCS.")
        return results


if __name__ == "__main__":
    sample_entries = [
        {"url": "https://www.panelinha.com.br/receita/pudim-de-leite", "source_name": "panelinha"},
        {"url": "https://www.tudogostoso.com.br/receita/1-bolo-de-cenoura.html", "source_name": "tudogostoso"},
    ]
    agent = CollectorAgent()
    results = agent.collect(sample_entries)
