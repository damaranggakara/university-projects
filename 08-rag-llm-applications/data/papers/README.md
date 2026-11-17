# Source papers

`rag_research_assistant.ipynb` indexes four research papers on agentic AI and RAG. They
are **not committed**: they are third-party PDFs totalling about 8 MB, which would be
half this repository again, and their redistribution terms vary by publisher.

Drop them into this directory and the notebook will pick up every `*.pdf` it finds.

| Paper | Size |
|---|---|
| AI Insights: Agentic RAG | 0.1 MB |
| Development and Evaluation of AI Agentic Workflows in LangGraph | 6.2 MB |
| Reasoning RAG via System 1 or System 2 | 1.2 MB |
| Synergizing Reasoning and Acting in Language Models (ReAct) | 0.6 MB |

The last of these is the ReAct paper (Yao et al., 2022), [arXiv:2210.03629](https://arxiv.org/abs/2210.03629),
which is the method the agent in this project uses.

The notebook does not depend on these specific documents; any set of PDFs in this folder
will be chunked, embedded and indexed. Swapping in your own is a reasonable way to see the
pipeline work.
