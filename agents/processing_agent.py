import re
from bs4 import BeautifulSoup

class ProcessingAgent:
    def __init__(self):
        # Seletores comuns para sites de receitas (ajustável no config futuramente)
        self.ingredient_selectors = [
            '.ingredients-list', '.it-ingredientes', '[itemprop="recipeIngredient"]',
            'ul.lista-ingredientes', '.ingredient-items'
        ]
        self.instruction_selectors = [
            '.instructions', '.it-preparo', '[itemprop="recipeInstructions"]',
            'ol.passo-a-passo', '.preparation-steps'
        ]

    def _clean_text(self, text):
        """Remove espaços excessivos e quebras de linha inúteis."""
        if not text: return ""
        return re.sub(r'\s+', ' ', text).strip()

    def extract_ingredients(self, soup):
        """Busca a lista de ingredientes usando seletores ou busca por texto."""
        ingredients = []
        # Tenta por seletores conhecidos
        for selector in self.ingredient_selectors:
            found = soup.select(selector)
            if found:
                # Extrai cada item da lista (li) se existir
                items = found[0].find_all('li')
                if items:
                    return [self._clean_text(i.get_text()) for i in items]
        
        # Fallback: Procura por um cabeçalho que contenha 'Ingredientes'
        header = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'ingredientes' in tag.get_text().lower())
        if header:
            sibling = header.find_next(['ul', 'div'])
            if sibling:
                return [self._clean_text(li.get_text()) for li in sibling.find_all('li')]
        
        return []

    def extract_instructions(self, soup):
        """Busca o modo de preparo."""
        for selector in self.instruction_selectors:
            found = soup.select(selector)
            if found:
                return self._clean_text(found[0].get_text(separator=" "))
        
        return "Instruções não encontradas."

    def process(self, entry: dict) -> dict:
        """
        Processa uma entrada do CollectorAgent.

        Args:
            entry: dict com {url, source_name, gcs_uri, timestamp, html}

        Returns:
            dict com {title, ingredients, instructions, metadata}
        """
        html_content = entry["html"]
        url = entry.get("url", "")
        source_name = entry.get("source_name", "desconhecido")

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extrair Título (Tenta H1 primeiro, depois title tag)
        title_tag = soup.find('h1') or soup.title
        title = self._clean_text(title_tag.get_text()) if title_tag else "Sem Título"

        # 2. Extrair Ingredientes e Instruções
        ingredients = self.extract_ingredients(soup)
        instructions = self.extract_instructions(soup)

        return {
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "metadata": {
                "source": source_name,
                "url": url,
                "category": "geral"
            }
        }

if __name__ == "__main__":
    mock_entry = {
        "url": "https://tudogostoso.com.br/receita/123",
        "source_name": "tudogostoso",
        "html": """
        <html>
            <h1>Frango Grelhado</h1>
            <ul class="ingredients-list">
                <li>2 peitos de frango</li>
                <li>Sal a gosto</li>
            </ul>
            <div class="instructions">Tempere o frango e grelhe no fogo médio.</div>
        </html>
        """
    }
    processor = ProcessingAgent()

    import json
    result = processor.process(mock_entry)
    print(json.dumps(result, indent=2, ensure_ascii=False))