---
name: processing_agent NLP pipeline status
description: Status das funcionalidades NLP implementadas no ProcessingAgent
type: project
---

O `agents/processing_agent.py` tem NLP completo implementado e testado (2026-03-16).

**Why:** O pipeline de classificação original usava apenas regex simples, sem lidar com plurais, formas flexionadas ou similaridade semântica entre ingredientes.

**How to apply:** Ao sugerir melhorias no ProcessingAgent, considerar que lematização (spaCy), embeddings (sentence-transformers) e scoring por categoria já estão implementados — não propor reimplementar essas camadas.

## Funcionalidades implementadas e validadas

- `_clean_text`: HTML unescape → NFKC → remoção de chars invisíveis → colapso whitespace
- `_parse_ingredient`: 5 padrões regex em ordem de especificidade, retorna {quantidade, unidade, nome, texto_original}
- `_lemmatize`: spaCy `pt_core_news_sm` — "frangos grelhados" → "frango grelhado"
- `_classify`: 3 camadas — lemma match + word boundary + cosine similarity (threshold 0.72)
- Forbidden check também lematizado — "ovos cozidos" dispara forbidden "ovo"
- `covered_by_marker` logic mantida — "leite de coco" não dispara forbidden "leite"
- Scoring por categoria (soma de pontos por marker) — mais markers = maior confiança
- Embeddings dos markers pré-computados no `__init__` (paraphrase-multilingual-MiniLM-L12-v2)

## Dependências adicionadas ao requirements.txt
- `spacy>=3.7`
- `sentence-transformers>=3.0`
- Modelo spaCy: `python -m spacy download pt_core_news_sm`
