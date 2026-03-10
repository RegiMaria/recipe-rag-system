from bs4 import BeautifulSoup

class ProcessingAgent:
    def process(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.title.string if soup.title else "No Title"
        text = soup.get_text()
        return {"title": title, "text": text}

if __name__ == "__main__":
    processor = ProcessingAgent()
    result = processor.process("<html><title>Chicken</title><body>Recipe text</body></html>")
    print(result)