import json
import hashlib
from typing import List

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

import GET
from POST import ChecklistCreator

def _extract_exec_id(payload: dict) -> str | None:
    """Extrai o ID da empresa de execução do payload do webhook."""
    try:
        return payload.get("execution_company_id", {}).get("$oid")
    except (AttributeError, TypeError):
        return None

def extrair_informacoes_planejamento(data: dict) -> dict:
    """
    Extrai e formata as informações do payload real do webhook, lendo
    a estrutura correta do subformulário "Itens".
    """
    info = {
        "identificador": None, "data_prevista": None, "contrato_concessao": None,
        "concessionaria": None, "gerar_checklist_manual": False, "gerar_itens_auto": False,
        "itens_ft": [], "itens_fa": [], "itens_fo": [], "itens_gc": [], "itens_vc": [],
        "user_id": None
    }
    
    TIPO_MAP = {
        "Fiscalização Técnica - FT": "FT",
        "Fiscalização Administrativa - FA": "FA",
        "Fiscalização de Obras (COPEA) - FO": "FO",
        "Gestão do Contrato - GC": "GC",
        "Verificador de Conformidade - VC": "VC"
    }

    info['user_id'] = data.get('user_id', {}).get('$oid')

    for question in data.get("template_questions", []):
        q_text = question.get("question")
        q_value = question.get("value")

        # Extrai os campos de identificação e flags de controle
        if q_text == "Identificador": info["identificador"] = q_value
        elif q_text == "Data prevista para a realização do checklist": info["data_prevista"] = q_value
        elif q_text == "Contrato de concessão": info["contrato_concessao"] = q_value
        elif q_text == "Concessionária": info["concessionaria"] = q_value
        elif q_text == "Gerar checklist": info["gerar_checklist_manual"] = q_value == "true"
        elif q_text == "Gerar Itens": info["gerar_itens_auto"] = q_value == "true"
        
        # --- LÓGICA CORRETA PARA LER O SUBFORMULÁRIO "ITENS" ---
        elif q_text == "Itens" and "sub_checklists" in question:
            for sub_entry in question.get("sub_checklists", []):
                item_valor = None
                tipos_selecionados = []
                
                for sub_col in sub_entry.get('sub_checklist_questions', []):
                    if sub_col.get('question') == 'Item':
                        item_valor = sub_col.get('value')
                    elif sub_col.get('question') == 'Enviar para Execução':
                        # Itera na lista de "options" para encontrar os valores "true"
                        for option in sub_col.get('options', []):
                            if option.get('value') == 'true':
                                tipos_selecionados.append(option.get('text'))
                
                if item_valor and tipos_selecionados:
                    for tipo_str in tipos_selecionados:
                        tipo_abbr = TIPO_MAP.get(tipo_str.strip())
                        if tipo_abbr:
                            info[f'itens_{tipo_abbr.lower()}'].append({
                                "item": item_valor,
                                "habilitado": True,
                                "tipo": tipo_abbr
                            })
    return info

def get_total_itens_habilitados(info: dict) -> int:
    """Calcula o total de itens habilitados."""
    total = 0
    for tipo_key in ['itens_ft', 'itens_fa', 'itens_fo', 'itens_gc', 'itens_vc']:
        total += len(info.get(tipo_key, []))
    return total

def handle_webhook_logic(payload: dict):
    """Função que faz o trabalho pesado, executada em segundo plano."""
    info = extrair_informacoes_planejamento(payload)
    total_itens_habilitados = get_total_itens_habilitados(info)
    form_id = payload.get('_id', {}).get('$oid')
    exec_id = _extract_exec_id(payload)
    user_id = info.get('user_id')

    print("\n--- INICIANDO PROCESSAMENTO EM BACKGROUND ---")
    print(f"Formulário ID: {form_id} | Empresa ID: {exec_id}")
    print(f"Flag 'Gerar Itens': {info['gerar_itens_auto']} | Flag 'Gerar Checklist': {info['gerar_checklist_manual']} | Itens Habilitados: {total_itens_habilitados}")

    if info['gerar_itens_auto'] and total_itens_habilitados == 0:
        print("\n▶️ CENÁRIO 1: Populando subformulário 'Seleção de Itens'...")
        if not exec_id or not form_id: return print(f"Falha no Cenário 1: IDs não encontrados (Form: {form_id}, Empresa: {exec_id}).")
        clausulas = GET._buscar_clausulas(exec_id)
        if not clausulas: return print("Falha no Cenário 1: Nenhuma cláusula de cadastro encontrada.")
        creator = ChecklistCreator()
        creator.popular_formulario_planejamento(form_id, clausulas)
        print("✅ Processamento em background do Cenário 1 concluído.")
        return

    elif info['gerar_checklist_manual'] and total_itens_habilitados > 0:
        print("\n▶️ CENÁRIO 2: Gerando checklist de fiscalização final...")
        if not exec_id: return print("Falha no Cenário 2: ID da empresa não encontrado.")
        
        buscador = GET.FormulariosBuscador(execution_company_id=exec_id)
        buscador.carregar_e_salvar_formularios()
        
        itens_para_api = {}
        for tipo_key in ['itens_ft', 'itens_fa', 'itens_fo', 'itens_gc', 'itens_vc']:
            tipo_abbr = tipo_key.replace('itens_', '').upper()
            clausulas_habilitadas_do_tipo = [item['item'] for item in info[tipo_key] if item.get('habilitado')]
            if not clausulas_habilitadas_do_tipo: continue
            
            print(f"Processando {len(clausulas_habilitadas_do_tipo)} item(ns) para a categoria: {tipo_abbr}")
            formularios_encontrados = buscador.buscar_por_clausulas_no_cache(clausulas_habilitadas_do_tipo)
            if formularios_encontrados:
                itens_para_api[tipo_abbr] = [buscador.extrair_informacoes_formulario(form) for form in formularios_encontrados]

        if not itens_para_api: return print("Falha no Cenário 2: Nenhum detalhe encontrado para os itens selecionados.")
        
        identificacao = {k: info.get(k) for k in ["data_prevista", "contrato_concessao", "identificador", "concessionaria"]}
        creator = ChecklistCreator()
        checklist_id = creator.criar_checklist_completo(
            identificacao=identificacao, execution_company_id=exec_id,
            itens_por_tipo=itens_para_api, assignee_id=user_id, creator_id=user_id
        )
        if checklist_id: print(f"✅ Processamento em background do Cenário 2 concluído. Checklist ID: {checklist_id}")
        else: print("❌ Falha no Cenário 2: Erro na criação do checklist via API.")
        return

    else:
        print("\n⏹️ Nenhuma condição atendida no processamento em background.")
        return

def criar_app_fastapi():
    """Cria e configura a aplicação FastAPI com Background Tasks e cache de IDs."""
    app = FastAPI()
    
    WEBHOOK_ID_CACHE_FILE = 'webhook_cache.json'
    MAX_CACHE_SIZE = 200

    def ler_cache_de_ids() -> List[str]:
        """Lê a lista de IDs de webhooks processados do arquivo de cache."""
        try:
            with open(WEBHOOK_ID_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def salvar_cache_de_ids(ids: List[str]):
        """Salva a lista atualizada de IDs no arquivo de cache."""
        # A estrutura try/except aqui está corrigida.
        try:
            with open(WEBHOOK_ID_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(ids, f)
        except IOError as e:
            print(f"❌ Erro ao salvar o cache de webhooks: {e}")

    @app.post("/webhook")
    async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
        try:
            body = await request.json()
            print("\n=== WEBHOOK PAYLOAD COMPLETO ===")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            print("=== FIM DO PAYLOAD ===\n")
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"status": "erro", "motivo": "Payload inválido."})

        try:
            form_id = body.get('_id', {}).get('$oid')
            updated_at = body.get('updated_at')
            if not form_id or not updated_at: raise KeyError("IDs não encontrados no formato esperado")
            current_id = hashlib.md5(f"{form_id}-{updated_at}".encode()).hexdigest()
        except (KeyError, AttributeError):
            current_id = hashlib.md5(json.dumps(body, sort_keys=True).encode()).hexdigest()
            
        cached_ids = ler_cache_de_ids()
        if current_id in cached_ids:
            print(f"🔄 Webhook duplicado detectado (ID: {current_id[:8]}). Ignorando.")
            return JSONResponse(status_code=200, content={"status": "ignorado", "reason": "duplicate"})
        
        cached_ids.append(current_id)
        salvar_cache_de_ids(cached_ids[-MAX_CACHE_SIZE:])
        
        background_tasks.add_task(handle_webhook_logic, body)
        
        print(f"✅ Webhook (ID: {current_id[:8]}) aceito. Agendado para processamento.")
        return JSONResponse(status_code=202, content={"status": "aceito", "detail": "Webhook recebido."})
        
    return app
