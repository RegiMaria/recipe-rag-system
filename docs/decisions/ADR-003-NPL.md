# Architecture Decision Records#
## ADR-003-NLP ##

Data: 16-03-2026

## 1.Trocar Regex por NLP ##

**Contexto**

O **ProcessingAgent** utilizava regex puro para extrair informações das receitas.

Regex trata texto como sequência de caracteres.

NLP trata texto como linguagem com significado.

Essa diferença impactava diretamente a qualidade do pipeline de dados.

**Problemas do modelo atual (Regex)**

O uso de regex causava três falhas principais.

1. Falso positivo na classificação

`"ovo" encontrado dentro de "enovelado"`

Resultado:

receita classificada incorretamente

2. Instruções extraídas como bloco único

Entrada:

`"Misture. Adicione. Leve ao forno."`

Saída atual:

`1 string única`

Saída esperada:

`["Misture", "Adicione", "Leve ao forno"]`

3. Entidades HTML vazando para os dados

Entrada:

`"&nbsp;frango&amp;legumes"`

Resultado armazenado:

`texto sujo no GCS`

Impacto no pipeline inteiro

O problema não fica só no `ProcessingAgent`.

Dado sujo no ProcessingAgent
↓
Embedding gerado sobre texto errado (EmbeddingAgent)
↓
Busca vetorial retorna resultados ruins (Vector Store)
↓
RAGAgent responde com contexto incorreto

**Regra básica de pipelines de dados**

Lixo entra → lixo sai

Por isso NLP é a fundação da qualidade do pipeline.

| Aspecto | Regex (atual) | NLP (proposto) |
|---|---|---|
| Word boundary | ❌ substring match | ✅ `\bovo\b` → match exato |
| Limpeza HTML | ❌ não trata `&nbsp;` | ✅ `html.unescape()` + Unicode NFKC |
| Separação de passos | ❌ bloco único | ✅ lista de sentenças |
| Extração de ingredientes | ❌ depende de CSS selector | ✅ NER detecta quantidade + ingrediente |
| Custo de implementação | — | Baixo → Alto (depende do nível) |

A migração foi planejada em três níveis progressivos.

Nível 1 — Correção imediata (sem nova dependência)

Implementação simples usando Python padrão.

```html.unescape()
unicodedata.normalize("NFKC", text)
re.search(r"\bmarker\b")
```
Resolve:

limpeza de entidades HTML

correção de substring match

Impacto:

classificação correta

dados mais limpos

Esforço:

```baixo
~1 hora de implementação
```
Nível 2 — NLP leve (spaCy)

Uso de spaCy com modelo em português.
```
import spacy

nlp = spacy.load("pt_core_news_sm")
doc = nlp(texto)

passos = [sent.text for sent in doc.sents]
```

Resolve:

separação automática de sentenças

instruções como lista de passos

Impacto:
```
chunks melhores
↓
embeddings melhores
↓
busca vetorial mais precisa
```

Esforço:
```
médio
nova dependência + refatorar ProcessingAgent
```
Nível 3 — NLP completo

Pipeline totalmente semântico.
```
Extração de ingredientes via NER

Embeddings reais
Vertex AI
text-embedding-004
```
Resolve:

extração estruturada de ingredientes

similaridade semântica real

Impacto:

```RAGAgent passa a responder com contexto confiável```

Esforço:
```
alto
integração com Vertex AI + redesign do schema
```
Recomendação de implementação

```
Agora       → Nível 1 (corrige bugs críticos)
Próximo PR  → Nível 2 (desbloqueia EmbeddingAgent)
Depois      → Nível 3 (pipeline completo)
```

**Decisão de arquitetura**

A estratégia não foi substituir tudo de uma vez, mas evoluir o sistema em camadas.

Isso protege o que já está estável:

CrawlerAgent ✅

CollectorAgent ✅

Enquanto melhora gradualmente a fundação do processamento de dados.