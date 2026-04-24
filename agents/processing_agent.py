import html
import re
import unicodedata
import numpy as np
import yaml
from bs4 import BeautifulSoup

import spacy
from sentence_transformers import SentenceTransformer

# 03 - O ProcessingAgent é o cérebro linguístico do pipeline — ele pega o HTML bruto coletado e
# transforma em texto limpo e estruturado, pronto para virar vetor.
# O que ele faz:
# Recebe os arquivos HTML do GCS (Google Cloud Storage), 
# processa com técnicas de NLP e devolve chunks de texto normalizados para o EmbeddingAgent.


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

# Quantidade: inteiro, fração (1/2), misto (1 e 1/2), decimal (0,5)
# Frações unicode (½ ¼ ¾ …) são normalizadas para "1/2" etc. por _clean_text antes de chegarem aqui
_RE_QTD  = r"(?P<quantidade>(?:\d+\s+e\s+)?\d+(?:[/,\.]\d+)?)"
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
    # Limiar de similaridade coseno para considerar match semântico
    SEMANTIC_THRESHOLD = 0.72

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

        # ── NLP: lematização (spaCy pt) ───────────────────────────────────────
        # Requer: python -m spacy download pt_core_news_sm
        self._nlp = spacy.load("pt_core_news_sm")

        # ── NLP: embeddings semânticos (sentence-transformers multilingual) ────
        # Modelo leve (~120 MB) que cobre português bem
        self._embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

        # Pré-computa embeddings de todos os markers (evita recomputar a cada receita)
        self._marker_embeddings: dict[str, dict[str, np.ndarray]] = {}
        for category, rules in self.categories.items():
            markers = rules.get("markers", [])
            if markers:
                vecs = self._embedder.encode(markers, convert_to_numpy=True, show_progress_bar=False)
                self._marker_embeddings[category] = dict(zip(markers, vecs))

    # ── Helpers NLP ──────────────────────────────────────────────────────────

    def _lemmatize(self, text: str) -> str:
        """Reduz o texto às formas lematizadas via spaCy.

        Exemplos:
            "frangos grelhados" → "frango grelhado"
            "ovos cozidos"      → "ovo cozido"
            "folhas de hortelã" → "folha de hortelã"
        """
        doc = self._nlp(text.lower())
        return " ".join(token.lemma_ for token in doc)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Similaridade coseno entre dois vetores."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    # ── Matching ─────────────────────────────────────────────────────────────

    @staticmethod
    def _matches_term(text: str, term: str) -> bool:
        """
        Busca `term` em `text` respeitando fronteiras de palavra Unicode.

        Usa lookbehind/lookahead negativos de \\w (Unicode-aware no Python 3),
        o que garante que caracteres acentuados do português não sejam tratados
        como separadores.
        """
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        return bool(re.search(pattern, text, re.UNICODE | re.IGNORECASE))

    def _matches_lemma(self, lemma_text: str, term: str) -> bool:
        """
        Match após lematização de ambos os lados.

        Casa "frangos" com o term "frango", "grelhados" com "grelhado", etc.
        """
        lemma_term = self._lemmatize(term)
        return self._matches_term(lemma_text, lemma_term)

    def _term_present(self, raw_text: str, lemma_text: str, term: str) -> bool:
        """Retorna True se `term` está presente no texto (raw OU lemmatizado)."""
        return self._matches_term(raw_text, term) or self._matches_lemma(lemma_text, term)

    # ── Classificação ────────────────────────────────────────────────────────

    def _classify(self, ingredients: list[str]) -> list[str]:
        """
        Classifica a receita com base nos ingredientes usando três camadas:

        1. Lematização  — "frangos" casa com marker/forbidden "frango"
        2. Word boundary — evita falsos positivos ("mel" ≠ "melancia")
        3. Embeddings   — "filé de frango" ≈ "peito de frango" (score proporcional)

        Scoring por categoria:
          - Match exato ou via lemma   → +1.0 por marker
          - Match semântico (≥ threshold) → +similaridade (0.72–1.0)
          - Forbidden (raw ou lemma)   → descarta categoria
              exceto se coberto por marker composto presente

        Retorna categorias ordenadas por score decrescente, ou ["geral"].
        """
        if not ingredients:
            return ["geral"]

        raw_text   = " ".join(ingredients).lower()
        lemma_text = " ".join(self._lemmatize(name) for name in ingredients)

        # Embeddings dos ingredientes para matching semântico
        ing_embeddings: np.ndarray = self._embedder.encode(
            ingredients, convert_to_numpy=True, show_progress_bar=False
        )

        scores: dict[str, float] = {}

        for category, rules in self.categories.items():
            forbidden_terms = rules.get("forbidden", [])
            marker_terms    = rules.get("markers", [])

            # ── 1. Forbidden check (raw + lemma) ─────────────────────────────
            is_forbidden = False
            for term in forbidden_terms:
                if not self._term_present(raw_text, lemma_text, term):
                    continue

                # Ignora se o termo proibido é subphrase de um marker presente
                # Ex: "leite" ⊂ "leite de coco" e "leite de coco" está no texto
                covered_by_marker = any(
                    term in marker and self._term_present(raw_text, lemma_text, marker)
                    for marker in marker_terms
                )
                if not covered_by_marker:
                    is_forbidden = True
                    break

            if is_forbidden:
                continue

            # ── 2. Scoring de markers ─────────────────────────────────────────
            score = 0.0
            cat_marker_embs = self._marker_embeddings.get(category, {})

            for marker in marker_terms:
                # Match exato ou via lemma → pontuação máxima
                if self._term_present(raw_text, lemma_text, marker):
                    score += 1.0
                    continue

                # Match semântico — pontuação proporcional à similaridade
                marker_emb = cat_marker_embs.get(marker)
                if marker_emb is not None and len(ing_embeddings) > 0:
                    sims = np.array([
                        self._cosine_similarity(marker_emb, ing_emb)
                        for ing_emb in ing_embeddings
                    ])
                    best_sim = float(sims.max())
                    if best_sim >= self.SEMANTIC_THRESHOLD:
                        score += best_sim  # ex: 0.85 pontos por match semântico

            if score > 0:
                scores[category] = score

        if not scores:
            return ["geral"]

        # Ordena por score decrescente — mais marcadores = mais confiança
        return [cat for cat, _ in sorted(scores.items(), key=lambda x: -x[1])]

    # ── Limpeza de texto ─────────────────────────────────────────────────────

    def _clean_text(self, text: str) -> str:
        """
        Pipeline de limpeza em 4 camadas:

        1. Decodifica entidades HTML  : &amp; → &, &nbsp; → espaço, ½ → ½
        2. Normalização Unicode NFKC  : unifica formas compostas/decompostas,
                                        converte \\xa0/\\u202f em espaço normal
        3. Remove caracteres de controle invisíveis (\\x00-\\x08, \\x0B-\\x1F, \\x7F-\\x9F)
           mantendo \\t (\\x09), \\n (\\x0A), \\r (\\x0D) para o passo seguinte
        4. Colapsa todo whitespace restante (\\t, \\n, \\r, espaços múltiplos) em espaço único
        """
        if not text:
            return ""

        # 1. Entidades HTML (&amp; &nbsp; &frac12; &#189; etc.)
        text = html.unescape(text)

        # 2. Unicode NFKC: \xa0 → espaço, café(NFC) == café(NFD), ﬁ → fi
        #    Efeito colateral: ½ → "1⁄2" (U+2044 FRACTION SLASH, não U+002F)
        text = unicodedata.normalize("NFKC", text)

        # 2b. Normaliza FRACTION SLASH (U+2044) → SOLIDUS (U+002F)
        #     Garante que "1⁄2", "3⁄4" etc. sejam tratados como "1/2", "3/4"
        #     pelos padrões de _RE_QTD que usam [/,.]
        text = text.replace("\u2044", "/")

        # 3. Caracteres de controle e invisíveis (zero-width, soft-hyphen, BOM…)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\u00AD\u200B-\u200D\uFEFF]", "", text)

        # 4. Colapsa whitespace múltiplo
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ── Parsing de ingrediente ───────────────────────────────────────────────

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

    # ── Extração HTML ────────────────────────────────────────────────────────

    def extract_ingredients(self, soup) -> list[dict]:
        """
        Busca a lista de ingredientes e retorna itens estruturados
        com {quantidade, unidade, nome, texto_original}.
        """
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

    # ── Pipeline principal ───────────────────────────────────────────────────

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

        # 1. Extrair Título
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

    # ── Teste 2: NLP — lemmatização e plurais ─────────────────────────────────
    print("\n=== _classify — NLP (lemma + semântica) ===")
    nlp_tests = [
        ("Plurais/formas flexionadas", ["frangos grelhados", "batatas doces", "claras de ovos"]),
        ("Semântica: filé ≈ peito de frango", ["filé de frango", "arroz integral"]),
        ("Ingrediente composto: leite de coco (não forbidden)", ["leite de coco", "linçaça"]),
        ("Forbidden via lemma: ovos → vegetarian negado", ["ovos mexidos", "tofu"]),
        ("Score múltiplos markers fitness", ["peito de frango", "batata doce", "aveia", "claras"]),
    ]
    for label, ings in nlp_tests:
        cats = processor._classify(ings)
        print(f"  {label}")
        print(f"    ingredientes : {ings}")
        print(f"    categorias   : {cats}\n")

    # ── Teste 3: pipeline completo ────────────────────────────────────────────
    print("=== process() ===")
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
