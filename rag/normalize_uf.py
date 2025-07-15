import re

# Dicionário das UFs brasileiras
UF_MAP = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins"
}

def normaliza_siglas_uf(texto):
    # Normaliza ".MA", ";MA", ", MA", "MA." para "MA"
    for uf in UF_MAP.keys():
        texto = re.sub(rf'[\.\;\,\s]+{uf}[\.\;\,\s]+', f' {uf} ', texto)
        texto = re.sub(rf'[\.\;\,\s]+{uf}[\s]', f' {uf} ', texto)
        texto = re.sub(rf'[\s]+{uf}[\.\;\,]', f' {uf} ', texto)
        texto = re.sub(rf'[\s\.]{uf}[\s\.]', f' {uf} ', texto)
    # Remove múltiplos espaços
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

