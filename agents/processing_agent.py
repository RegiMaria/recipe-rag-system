import html
import re
import unicodedata
import yaml
from bs4 import BeautifulSoup

# ── Constantes para parsing de ingredientes ───────────────────────────────────
# Unidades de medida em português (ordem: mais longas primeiro — evita match parcial)
_UNITS = "|".join([
    r"colheres?\s+de\s+sopa",
    r"colheres?\s+de\s+chá",
    r"xícaras?\s+de\s+chá",
    r"xícaras?",
    r"copos?",
    r"litros?",
    r"quilogramas?",
    r"kg",
    r"mililitros?",
    r"ml",
    r"gramas?",
    r"g\b",
    r"latas?",
    r"pacotes?",
    r"caixinhas?",
    r"sachês?",
    r"unidades?",
    r"peças?",
    r"fatias?",
    r"pedaços?",
    r"dentes?",
    r"folhas?",
    r"ramos?",
    r"pitadas?",
    r"fio\s+de",
    r"a\s+gosto",
    r"q\.b\.",
])

# Quantidade: inteiro, fração (1/2), misto (1 e 1/2), decimal (0,5), unicode (½ ¼ ¾ …)
_RE_QTD  = r"(?P<quantidade>(?:\d+\s+e\s+)?\d+(?:[/,\.]\d+)?|[½¼¾⅓⅔⅛⅜⅝⅞])"
_RE_UNIT = r"(?P<unidade>" + _UNITS + r")"
_RE_CONN = r"(?:\s+d[eo]s?\s+|\s+)"   # "de ", "da ", "do ", "das ", "dos " ou só espaço

# Padrões em ordem de especificidade decrescente
_INGREDIENT_PATTERNS = [
    # 1. "200g de chocolate"   — qtd colada à unidade (sem espaço)
    re.compile(
        r"^\s*(?P<quantidade>\d+(?:[,.]\d+)?)\s*" + _RE_UNIT + r"\s*(?:d[eo]s?\s+)?(?P<nome>.+?)\s*$",
        re.IGNORECASE | re.UNICODE,
    ),
    # 2. "2 xícaras de farinha" / "1 e 1/2 xícara de açúcar" / "½ xícara de leite"
    re.compile(
        r"^\s*" + _RE_QTD + r"\s+" + _RE_UNIT + _RE_CONN + r"(?P<nome>.+?)\s*$",
        re.IGNORECASE | re.UNICODE,
    ),
    # 3. "2 peitos de frango"  — qtd presente, sem unidade reconhecida
    re.compile(
        r"^\s*" + _RE_QTD + r"\s+(?P<nome>.+?)\s*$",
        re.IGNORECASE | re.UNICODE,
    ),
    # 4. "pitada de sal" / "fio de azeite"  — unidade no início, sem qtd
    re.compile(
        r"^\s*" + _RE_UNIT + r"\s+(?:d[eo]s?\s+)?(?P<nome>.+?)\s*$",
        re.IGNORECASE | re.UNICODE,
    ),
    # 5. "sal a gosto" / "azeite q.b."  — nome seguido de marcador de quantidade indefinida
    re.compile(
        r"^\s*(?P<nome>.+?)\s+(?P<unidade>a\s+gosto|q\.b\.)\s*$",
        re.IGNORECASE | re.UNICODE,
    ),
]
# ─────────────────────────────────────────────────────────────────────────────


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

    def _parse_ingredient(self, text: str) -> dict:
        """
        Separa um item de ingrediente em quantidade, unidade e nome.

        Aplica os padrões de _INGREDIENT_PATTERNS em ordem de especificidade.
        Retorna sempre o texto original para rastreabilidade.

        Exemplos:
            "2 xícaras de farinha"   → {quantidade: "2",   unidade: "xícaras", nome: "farinha"}
            "200g de chocolate"      → {quantidade: "200", unidade: "g",       nome: "chocolate"}
            "1 e 1/2 xícara de leite"→ {quantidade: "1 e 1/2", unidade: "xícara", nome: "leite"}
            "pitada de sal"          → {quantidade: None,  unidade: "pitada",  nome: "sal"}
            "sal a gosto"            → {quantidade: None,  unidade: "a gosto", nome: "sal"}
            "2 peitos de frango"     → {quantidade: "2",   unidade: None,      nome: "peitos de frango"}
            "tofu"                   → {quantidade: None,  unidade: None,      nome: "tofu"}
        """
        cleaned = self._clean_text(text)
        base = {"quantidade": None, "unidade": None, "texto_original": cleaned}

        if not cleaned:
            return {**base, "nome": ""}

        for pattern in _INGREDIENT_PATTERNS:
            m = pattern.match(cleaned)
            if m:
                groups = m.groupdict()
                return {
                    "quantidade": groups.get("quantidade"),
                    "unidade":    groups.get("unidade"),
                    "nome":       (groups.get("nome") or "").strip(),
                    "texto_original": cleaned,
                }

        # Fallback: nenhum padrão casou — texto completo como nome
        return {**base, "nome": cleaned}

    def extract_ingredients(self, soup) -> list[dict]:
        """
        Busca a lista de ingredientes e retorna itens estruturados
        com {quantidade, unidade, nome, texto_original}.
        """
        # Tenta por seletores conhecidos
        for selector in self.ingredient_selectors:
            found = soup.select(selector)
            if found:
                items = found[0].find_all('li')
                if items:
                    return [self._parse_ingredient(i.get_text()) for i in items]

        # Fallback: Procura por um cabeçalho que contenha 'Ingredientes'
        header = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'ingredientes' in tag.get_text().lower())
        if header:
            sibling = header.find_next(['ul', 'div'])
            if sibling:
                return [self._parse_ingredient(li.get_text()) for li in sibling.find_all('li')]

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

        # _classify opera sobre nomes limpos (sem quantidade/unidade)
        ingredient_names = [i["nome"] for i in ingredients if i.get("nome")]

        return {
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "metadata": {
                "source": source_name,
                "url": url,
                "category": self._classify(ingredient_names)
            }
        }

if __name__ == "__main__":
    import json

    processor = ProcessingAgent()

    # ── Teste 1: parsing estruturado de ingredientes ──────────────────────────
    print("=== _parse_ingredient ===")
    samples = [
        "2 xícaras de farinha de trigo",
        "200g de chocolate meio amargo",
        "1 e 1/2 xícara de açúcar",
        "½ xícara de leite de coco",
        "pitada de sal",
        "sal a gosto",
        "azeite a gosto",
        "2 peitos de frango",
        "3 dentes de alho",
        "1 lata de leite condensado",
        "tofu",
        "cogumelos",
    ]
    for s in samples:
        parsed = processor._parse_ingredient(s)
        print(f"  {s!r:45} → qtd={parsed['quantidade']!r:12} unid={parsed['unidade']!r:22} nome={parsed['nome']!r}")

    # ── Teste 2: pipeline completo com classificação ──────────────────────────
    print("\n=== process() ===")
    tests = [
        {
            "label": "Frango grelhado → fitness",
            "entry": {
                "url": "https://tudogostoso.com.br/receita/123",
                "source_name": "tudogostoso",
                "html": (
                    "<html><h1>Frango Grelhado</h1>"
                    "<ul class='ingredients-list'>"
                    "<li>2 peitos de frango</li>"
                    "<li>batata doce</li>"
                    "<li>2 colheres de sopa de azeite</li>"
                    "</ul><div class='instructions'>Grelhe.</div></html>"
                ),
            },
        },
        {
            "label": "Tofu com cogumelos → vegetarian",
            "entry": {
                "url": "https://veganismo.org.br/receitas-veganas/tofu",
                "source_name": "veganismo",
                "html": (
                    "<html><h1>Tofu Salteado</h1>"
                    "<ul class='ingredients-list'>"
                    "<li>200g de tofu</li>"
                    "<li>cogumelos a gosto</li>"
                    "<li>1 colher de sopa de azeite</li>"
                    "</ul><div class='instructions'>Saltear.</div></html>"
                ),
            },
        },
    ]

    for t in tests:
        result = processor.process(t["entry"])
        print(f"\n{t['label']}")
        print("  ingredients:")
        for ing in result["ingredients"]:
            print(f"    {ing}")
        print("  metadata:", json.dumps(result["metadata"], indent=4, ensure_ascii=False))