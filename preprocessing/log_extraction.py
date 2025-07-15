import json
import os
from datetime import datetime

def log_extraction(
    pdf_path,
    txt_path,
    parser_nome,
    input_text,
    output_chunks,
    rel_path,
    output_dir="./logs/logs_extracao",  # <- alteração aqui
    feedback=None
):
    """
    Salva log detalhado do processo de extração em arquivo JSON.
    Se feedback for passado, atualiza/adiciona no log.
    """
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.basename(pdf_path).replace('.pdf','')
    log_path = os.path.join(output_dir, f"{base}__{parser_nome}.json")

    # Monta registro base (ou atualiza se já existir)
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_entry = json.load(f)
    else:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "pdf_path": pdf_path,
            "txt_path": txt_path,
            "rel_path": rel_path,
            "parser": parser_nome,
            "input_text_sample": input_text[:2000],  # Só um trecho!
            "output_chunks_sample": output_chunks[:10],  # Até 10 chunks
            "n_chunks": len(output_chunks)
        }

    if feedback is not None:
        log_entry["feedback_humano"] = feedback

    # Sempre atualiza amostras e quantidade
    log_entry["input_text_sample"] = input_text[:2000]
    log_entry["output_chunks_sample"] = output_chunks[:10]
    log_entry["n_chunks"] = len(output_chunks)
    log_entry["last_update"] = datetime.now().isoformat()

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)

    print(f"📝 Log de extração salvo: {log_path}")

