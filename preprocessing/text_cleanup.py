import re

def corrigir_nome_fragmentado(texto):
    # Troca todos tipos de espaço (espaço normal, não-quebrável, etc) por espaço comum
    texto = re.sub(r'[\u00A0\u2000-\u200D]', ' ', texto)
    # Regex: encontra 2 ou mais letras (A-Z, acentuadas), cada uma separada por 1+ espaços
    # Aceita casos no começo, meio ou fim de frase
    padrao = re.compile(
        r'((?:[A-ZÀ-Ü]{1,2}\s){2,}[A-ZÀ-Ü]{1,2})'
    )

    def junta(m):
        return m.group(0).replace(' ', '')

    return padrao.sub(junta, texto)

