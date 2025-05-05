from docx import Document

def substituir_em_runs(paragraphs, dados):
    for p in paragraphs:
        for run in p.runs:
            for chave, valor in dados.items():
                placeholder = f"{{{{{chave}}}}}"
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, str(valor))

def preencher_modelo_docx(modelo_path: str, dados: dict, saida_path: str):
    doc = Document(modelo_path)
    for p in doc.paragraphs:
        for run in p.runs:
            for chave, valor in dados.items():
                if f"{{{{{chave}}}}}" in run.text:
                    run.text = run.text.replace(f"{{{{{chave}}}}}", str(valor))
    doc.save(saida_path)
