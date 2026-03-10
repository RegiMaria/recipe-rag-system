import requests
import time
import json
import os
from datetime import datetime

class CollectorAgent:
    def __init__(self):
        # Identidade para evitar bloqueios básicos
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _generate_filename(self, url):
        """Cria um nome de arquivo amigável baseado na URL e data."""
        # Remove https:// e transforma caracteres especiais em underscore
        clean_name = url.split('/')[-1] or "index"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{clean_name}.html"

    def collect(self, urls, save_local=True):
        """
        Baixa o HTML das URLs. 
        save_local: Se True, salva em uma pasta 'data/raw' para debug.
        """
        collected_data = []
        
        if save_local and not os.path.exists("data/raw"):
            os.makedirs("data/raw")

        for url in urls:
            try:
                print(f"📥 Coletando: {url}")
                response = requests.get(url, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    html_content = response.text
                    filename = self._generate_filename(url)
                    
                    data_entry = {
                        "url": url,
                        "html": html_content,
                        "timestamp": datetime.now().isoformat(),
                        "filename": filename
                    }
                    
                    if save_local:
                        with open(f"data/raw/{filename}", "w", encoding="utf-8") as f:
                            f.write(html_content)
                    
                    collected_data.append(data_entry)
                    
                    # Pausa essencial para não ser banido hehehe
                    time.sleep(2) 
                else:
                    print(f"⚠️ Falha ao baixar {url}: Status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Erro crítico ao coletar {url}: {e}")
        
        return collected_data

if __name__ == "__main__":
    sample_urls = [
        "https://www.panelinha.com.br/receita/pudim-de-leite",
        "https://www.tudogostoso.com.br/receita/1-bolo-de-cenoura.html"
    ]
    
    collector = CollectorAgent()
    # No pipeline real, o save_local será substituído pelo upload para o GCS
    results = collector.collect(sample_urls)
    print(f"\n✅ Coleta concluída! {len(results)} páginas baixadas.")