import os
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError


class GCSClient:
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or os.environ["GCS_BUCKET_NAME"]
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def upload_html(self, html_content: str, gcs_path: str) -> str:
        """
        Faz upload de conteúdo HTML para o GCS.

        Args:
            html_content: conteúdo HTML como string
            gcs_path: caminho dentro do bucket (ex: raw/html/panelinha/2026-03-12/receita.html)

        Returns:
            URI completa do objeto no GCS (gs://bucket/path)
        """
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(html_content, content_type="text/html; charset=utf-8")
        return f"gs://{self.bucket_name}/{gcs_path}"

    def blob_exists(self, gcs_path: str) -> bool:
        """Verifica se um objeto já existe no GCS (evita re-coleta)."""
        return self.bucket.blob(gcs_path).exists()
