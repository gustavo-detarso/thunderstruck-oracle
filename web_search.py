from serpapi import GoogleSearch
import os

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def busca_google(query, lang="pt"):
    if not SERPAPI_KEY:
        raise RuntimeError("Chave SERPAPI_KEY não encontrada nas variáveis de ambiente.")
    params = {
        "q": query,
        "hl": lang,
        "gl": "br",
        "num": 3,
        "api_key": SERPAPI_KEY,
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    snippets = []
    for res in results.get("organic_results", []):
        snippet = res.get("snippet") or res.get("title")
        link = res.get("link")
        if snippet:
            if link:
                snippets.append(f"{snippet} (Fonte: {link})")
            else:
                snippets.append(snippet)
    return "\n".join(snippets)
