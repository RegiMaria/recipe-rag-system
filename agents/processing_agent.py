import html
import re
import unicodedata
import yaml
from bs4 import BeautifulSoup

class ProcessingAgent:
    def __init__(self, categories_path: str = "config/categories.yaml"):
        # Seletores comuns para sites de receitas (ajustável no config futuramente)
        self.ingredient_selectors = [
            '.ingredients-list', '.it-ingredientes', '[itemprop="recipeIngredient"]',
            'ul.lista-ingredientes', '.ingredient-items'
        ]
        self.instruction_selectors = [
            '.instructions', '.it-preparo', '[itemprop="recipeInstructions"]',
            'ol.passo-a-passo', '.preparation-steps'
        ]

        with open(categories_path, "r") as f:
            self.categories = yaml.safe_load(f)["categories"]

    @staticmethod
    def _matches_term(text: str, term: str) -> bool:
        """
        Busca `term` em `text` respeitando fronteiras de palavra Unicode.

        Usa lookbehind/lookahead negativos de \w (Unicode-aware no Python 3),
        o que garante que caracteres acentuados do português não sejam tratados
        como separadores.

        Exemplos:
            "mel"      NÃO casa em "melancia"   (falso positivo evitado)
            "leite"    NÃO casa em "leite de coco" *quando coberto por marker*
            "frango"   casa em "2 peitos de frango"
        """
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        return bool(re.search(pattern, text, re.UNICODE | re.IGNORECASE))

    def _classify(self, ingredients: list[str]) -> list[str]:
        """
        Classifica a receita com base nos ingredientes usando markers e forbidden
        definidos em categories.yaml.

        Regras:
          - forbidden: descarta a categoria, EXCETO se o termo proibido for
                       subphrase de um marker presente (ex: "leite" é proibido
                       em vegan, mas "leite de coco" é marker → não descarta)
          - markers:   ao menos uma ocorrência confirma a categoria
          - Uma receita pode pertencer a múltiplas categorias

        Retorna lista de categorias ou ["geral"] se nenhuma regra casar.
        """
        text = " ".join(ingredients).lower()
        matched = []

        for category, rules in self.categories.items():
            forbidden_terms = rules.get("forbidden", [])
            marker_terms   = rules.get("markers", [])

            # Verifica forbidden com word boundary e prioridade de phrase
            is_forbidden = False
            for term in forbidden_terms:
                if not self._matches_term(text, term):
                    continue
                # Ignora se o termo proibido é subphrase de um marker que também está presente
                # Ex: "leite" ⊂ "leite de coco" e "leite de coco" está no texto → não proibido
                covered_by_marker = any(
                    term in marker and self._matches_term(text, marker)
                    for marker in marker_terms
                )
                if not covered_by_marker:
                    is_forbidden = True
                    break

            if is_forbidden:
                continue

            if any(self._matches_term(text, marker) for marker in marker_terms):
                matched.append(category)

        return matched if matched else ["geral"]

    def _clean_text(self, text: str) -> str:
        """
        Pipeline de limpeza em 4 camadas:

        1. Decodifica entidades HTML  : &amp; → &, &nbsp; → espaço, ½ → ½
        2. Normalização Unicode NFKC  : unifica formas compostas/decompostas,
                                        converte \xa0/\u202f em espaço normal
        3. Remove caracteres de controle invisíveis (\x00-\x08, \x0B-\x1F, \x7F-\x9F)
           mantendo \t (\x09), \n (\x0A), \r (\x0D) para o passo seguinte
        4. Colapsa todo whitespace restante (\t, \n, \r, espaços múltiplos) em espaço único
        """
        if not text:
            return ""

        # 1. Entidades HTML (&amp; &nbsp; &frac12; &#189; etc.)
        text = html.unescape(text)

        # 2. Unicode NFKC: \xa0 → espaço, café(NFC) == café(NFD), ﬁ → fi
        text = unicodedata.normalize("NFKC", text)

        # 3. Caracteres de controle e invisíveis (zero-width, soft-hyphen, BOM…)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\u00AD\u200B-\u200D\uFEFF]", "", text)

        # 4. Colapsa whitespace múltiplo
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract_ingredients(self, soup):
        """Busca a lista de ingredientes usando seletores ou busca por texto."""
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
        """Busca o modo de preparo. Retorna string vazia se não encontrado."""
        for selector in self.instruction_selectors:
            found = soup.select(selector)
            if found:
                return self._clean_text(found[0].get_text(separator=" "))

        return ""

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
                "category": self._classify(ingredients)
            }
        }

if __name__ == "__main__":
    import json

    tests = [
        {
            "label": "Frango grelhado → fitness",
            "entry": {
                "url": "https://tudogostoso.com.br/receita/123",
                "source_name": "tudogostoso",
                "html": "<html><h1>Frango Grelhado</h1><ul class='ingredients-list'><li>2 peitos de frango</li><li>batata doce</li></ul><div class='instructions'>Grelhe.</div></html>"
            }
        },
        {
            "label": "Tofu com cogumelos → vegetarian",
            "entry": {
                "url": "https://veganismo.org.br/receitas-veganas/tofu",
                "source_name": "veganismo",
                "html": "<html><h1>Tofu Salteado</h1><ul class='ingredients-list'><li>tofu</li><li>cogumelos</li><li>azeite</li></ul><div class='instructions'>Saltear.</div></html>"
            }
        },
    ]

    processor = ProcessingAgent()
    for t in tests:
        result = processor.process(t["entry"])
        print(f"\n{t['label']}")
        print(json.dumps(result["metadata"], indent=2, ensure_ascii=False))