# RAG and LLM Applications

Three projects from the generative-AI track of Semester 6: a retrieval-augmented research
assistant built as a LangGraph ReAct agent, structured extraction from unstructured text,
and a prompt-engineering comparison.

**These notebooks are not executed in this repository.** Every one of them calls the Gemini
API, which needs a key and bills per request, so their outputs are cleared rather than
committed, unlike the rest of the portfolio, where saved outputs let you read the results
without running anything. Set a key and they run.

## 1. Agentic RAG research assistant

`notebooks/rag_research_assistant.ipynb`, the substantial one.

A ReAct agent that answers questions about agentic AI by retrieving from a vector index of
four research papers, and cites the PDF and page it used.

```
PDFs ──▶ PyPDFLoader ──▶ RecursiveCharacterTextSplitter ──▶ HuggingFace embeddings
                              (1000 chars, 200 overlap)     (all-MiniLM-L6-v2)
                                                                    │
                                                                    ▼
         LangGraph ReAct agent ◀── rag_search tool ◀────────── FAISS index
            (Gemini 2.5 Flash)      (top-3 similarity)
```

| Component | Choice |
|---|---|
| Document loading | `PyPDFLoader`, page-level |
| Chunking | 1,000 characters, 200 overlap |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2`, run locally |
| Vector store | FAISS, in-memory |
| Retrieval | similarity search, `k=3` |
| Agent | `create_react_agent` from LangGraph |
| LLM | Gemini 2.5 Flash, `temperature=0` |

Two details worth noting. The embeddings run **locally** via sentence-transformers, so only
the generation step costs anything; indexing and retrieval work with no key at all. And
the `rag_search` tool returns source filenames and page numbers alongside the text, with
the system prompt requiring citations, which is what makes the agent's answers checkable
rather than merely fluent.

The source papers are not committed; see [`data/papers/README.md`](data/papers/README.md)
for the four titles. Any PDFs placed in that folder are indexed, so the pipeline can be
demonstrated with your own documents.

## 2. Structured extraction

`notebooks/structured_order_extraction.ipynb`

Parsing free-text restaurant orders into structured records with Gemini, the task where an
LLM earns its place over a regular expression, because the input is genuinely unstructured
("two coffees, one without sugar, and make the second a large").

## 3. Prompt engineering

`notebooks/prompt_engineering.ipynb`

Comparing prompting strategies on two tasks: article summarisation, and sentiment and theme
extraction over `data/customer_feedback.csv`. The interesting part is the contrast between
the techniques rather than any single output.

## Running it

```bash
pip install -r requirements.txt
```

Then either set the key in the environment:

```bash
export GOOGLE_API_KEY=your_key_here        # or add it to .env at the repo root
```

or paste it into the API key cell, which reads:

```python
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "INSERT-YOUR-GEMINI-API-KEY-HERE")
```

A free key comes from [Google AI Studio](https://aistudio.google.com/apikey). Without one,
the RAG notebook still loads, chunks, embeds and retrieves; only the Gemini calls fail,
and the key cell says so rather than erroring obscurely.

For the RAG notebook, also add the PDFs to `data/papers/`.

## Notes

Coursework for the Semester 6 generative-AI modules (Generative AI Foundations, Prompt
Engineering, Building AI Apps with LangChain and RAG). Individual work.

**All three notebooks originally had a Gemini API key hardcoded in a cell.** Two distinct
keys across the three files. They have been replaced with environment lookups and the keys
revoked. Saved outputs were cleared along with them, since those were produced under the
old keys.
