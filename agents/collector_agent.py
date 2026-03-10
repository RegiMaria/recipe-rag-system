import requests

class CollectorAgent:
    def collect(self, urls):
        data = []
        for url in urls:
            response = requests.get(url)
            data.append({"url": url, "html": response.text})
        return data

if __name__ == "__main__":
    sample_urls = ["https://www.panelinha.com.br/receita/arroz-caldoso-com-file-mignon-suino-e-quiabo-na-pressao",
    "https://www.panelinha.com.br/receita/pudim-de-leite"]
    collector = CollectorAgent()
    collected = collector.collect(sample_urls)
    print(collected)