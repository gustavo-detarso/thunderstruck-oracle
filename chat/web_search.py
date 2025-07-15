# web_search.py

from serpapi import GoogleSearch
import os

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def busca_google(query, lang="pt", limite=3):
    if not SERPAPI_KEY:
        raise RuntimeError("Chave SERPAPI_KEY não encontrada nas variáveis de ambiente.")

    try:
        params = {
            "q": query,
            "hl": lang,
            "gl": "br",
            "num": limite,
            "api_key": SERPAPI_KEY,
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            raise RuntimeError(f"Erro do SerpAPI: {results['error']}")

        snippets = []
        for res in results.get("organic_results", []):
            snippet = res.get("snippet") or res.get("title") or ""
            link = res.get("link")
            if snippet.strip():
                texto = snippet.strip()
                if link:
                    texto += f" (Fonte: {link})"
                snippets.append(texto)

        if not snippets:
            return None

        # Limita tamanho final do contexto (máx. 2000 caracteres por segurança)
        contexto = "\n\n".join(snippets)
        return contexto[:2000]

    except Exception as e:
        print(f"[ERRO] Falha na busca Google: {e}")
        return None

