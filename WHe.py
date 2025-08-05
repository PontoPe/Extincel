import json
import hashlib
import os
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

import GETe  # Importa com o novo nome
from POSTe import SeparacaoMaterialCreator  # Importa com o novo nome


def _extract_exec_id(payload: dict) -> Optional[str]:
    """Extrai o ID da empresa de execução do payload do webhook"""
    try:
        return payload.get("execution_company_id", {}).get("$oid")
    except (AttributeError, TypeError):
        return None


def extrair_informacoes_planejamento_material(data: dict) -> dict:
    """
    Extrai e formata as informações do payload do webhook para o novo fluxo de materiais
    """
    info = {
        # Identificação da empresa/cliente
        "razao_social": None,
        "nome_fantasia": None,
        "cnpj": None,
        "contato_cliente": None,
        "cargo_funcao": None,
        "telefone": None,
        "email_cliente": None,
        "responsavel_separacao": None,
        "necessita_compra": False,
        
        # Flags de controle
        "gerar_lista_materiais": False,  # Equivalente ao antigo "gerar_itens_auto"
        "gerar_separacao": False,  # Equivalente ao antigo "gerar_checklist_manual"
        
        # Filtros e materiais
        "subcategoria_servico": None,
        "materiais_selecionados": [],
        
        # Metadados
        "user_id": None,
        "form_id": None
    }
    
    # Extrai user_id
    info['user_id'] = data.get('user_id', {}).get('$oid')
    info['form_id'] = data.get('_id', {}).get('$oid')
    
    # Processa as questões do template
    for question in data.get("template_questions", []):
        q_text = question.get("question")
        q_value = question.get("value")
        
        # Mapeamento dos campos de identificação
        if "razão social" in q_text.lower():
            info["razao_social"] = q_value
        elif "nome fantasia" in q_text.lower():
            info["nome_fantasia"] = q_value
        elif "cnpj" in q_text.lower():
            info["cnpj"] = q_value
        elif "contato" in q_text.lower() and "cliente" in q_text.lower():
            info["contato_cliente"] = q_value
        elif "cargo" in q_text.lower() or "função" in q_text.lower():
            info["cargo_funcao"] = q_value
        elif "telefone" in q_text.lower():
            info["telefone"] = q_value
        elif "e-mail" in q_text.lower() or "email" in q_text.lower():
            info["email_cliente"] = q_value
        elif "responsável" in q_text.lower() and "separação" in q_text.lower():
            info["responsavel_separacao"] = q_value
        elif "necessita compra" in q_text.lower():
            info["necessita_compra"] = q_value == "true"
        
        # Flags de controle
        elif "gerar lista" in q_text.lower() or "buscar materiais" in q_text.lower():
            info["gerar_lista_materiais"] = q_value == "true"
        elif "gerar separação" in q_text.lower() or "criar formulário" in q_text.lower():
            info["gerar_separacao"] = q_value == "true"
        
        # Subcategoria para filtro
        elif "subcategoria" in q_text.lower() and "serviço" in q_text.lower():
            info["subcategoria_servico"] = q_value
        
        # Processamento do subformulário de materiais
        elif "materiais" in q_text.lower() and "sub_checklists" in question:
            for sub_entry in question.get("sub_checklists", []):
                material_info = {}
                
                for sub_col in sub_entry.get('sub_checklist_questions', []):
                    col_question = sub_col.get('question', '').lower()
                    col_value = sub_col.get('value')
                    
                    if 'código' in col_question:
                        material_info['codigo'] = col_value
                    elif 'descrição' in col_question or 'descricao' in col_question:
                        material_info['descricao'] = col_value
                    elif 'quantidade' in col_question:
                        material_info['quantidade'] = col_value
                    elif 'unidade' in col_question:
                        material_info['unidade'] = col_value
                    elif 'selecionado' in col_question or 'selecionar' in col_question:
                        material_info['selecionado'] = col_value == 'true'
                
                # Adiciona apenas materiais selecionados
                if material_info.get('selecionado', False) and material_info.get('codigo'):
                    info['materiais_selecionados'].append(material_info)
    
    return info


def handle_webhook_logic(payload: dict):
    """Função principal que processa o webhook em background"""
    info = extrair_informacoes_planejamento_material(payload)
    total_materiais_selecionados = len(info['materiais_selecionados'])
    form_id = info['form_id']
    exec_id = _extract_exec_id(payload) or "685d7c22ebc532b38cc602ce"
    user_id = info.get('user_id')
    
    print("\n--- INICIANDO PROCESSAMENTO DE MATERIAIS EM BACKGROUND ---")
    print(f"Formulário ID: {form_id} | Empresa ID: {exec_id}")
    print(f"Flag 'Gerar Lista': {info['gerar_lista_materiais']} | Flag 'Gerar Separação': {info['gerar_separacao']}")
    print(f"Materiais Selecionados: {total_materiais_selecionados}")
    print(f"Subcategoria Filtro: {info['subcategoria_servico']}")
    
    # CENÁRIO 1: Popular lista de materiais baseado em subcategoria
    if info['gerar_lista_materiais'] and total_materiais_selecionados == 0:
        print("\n▶️ CENÁRIO 1: Buscando e populando lista de materiais...")
        
        if not info['subcategoria_servico']:
            print("❌ Falha no Cenário 1: Subcategoria de serviço não especificada.")
            return
        
        if not form_id:
            print("❌ Falha no Cenário 1: ID do formulário não encontrado.")
            return
        
        # Busca materiais da subcategoria especificada
        materiais = GETe.buscar_materiais_com_subcategoria(
            subcategoria_servico=info['subcategoria_servico'],
            exec_id=exec_id
        )
        
        if not materiais:
            print(f"⚠️ Nenhum material encontrado para a subcategoria '{info['subcategoria_servico']}'.")
            return
        
        print(f"📦 Encontrados {len(materiais)} materiais para a subcategoria '{info['subcategoria_servico']}'.")
        
        # Aqui você precisaria implementar a lógica para popular o formulário atual
        # com a lista de materiais encontrados (similar ao popular_formulario_planejamento)
        # Por agora, apenas logamos o resultado
        
        print("✅ Processamento do Cenário 1 concluído.")
        print("⚠️ NOTA: Implementar lógica para popular formulário com lista de materiais.")
        return
    
    # CENÁRIO 2: Criar formulário de separação com materiais selecionados
    elif info['gerar_separacao'] and total_materiais_selecionados > 0:
        print("\n▶️ CENÁRIO 2: Gerando formulário de separação de materiais...")
        
        # Prepara dados de identificação
        identificacao = {
            'razao_social': info.get('razao_social'),
            'nome_fantasia': info.get('nome_fantasia'),
            'cnpj': info.get('cnpj'),
            'contato_cliente': info.get('contato_cliente'),
            'cargo_funcao': info.get('cargo_funcao'),
            'telefone': info.get('telefone'),
            'email_cliente': info.get('email_cliente'),
            'responsavel_separacao': info.get('responsavel_separacao'),
            'necessita_compra': info.get('necessita_compra')
        }
        
        # Remove campos None
        identificacao = {k: v for k, v in identificacao.items() if v is not None}
        
        # Se temos códigos de materiais mas não os detalhes completos,
        # podemos buscar os detalhes no cache
        materiais_completos = []
        
        # Para o cenário 2, vamos usar os dados do cache de materiais
        # que já foram carregados no cenário 1
        print("🔍 Preparando materiais selecionados para separação...")
        
        # Busca informações completas dos materiais selecionados
        buscador = GETe.MaterialBuscador(execution_company_id=exec_id)
        
        # Se temos o cache, busca os detalhes
        if os.path.exists(buscador.arquivo_cache):
            try:
                with open(buscador.arquivo_cache, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                materiais_cache = cache_data.get('dados', [])
                
                # Para cada material selecionado, busca seus detalhes completos
                for mat_selecionado in info['materiais_selecionados']:
                    # Busca pelo código ou outro identificador
                    for mat_completo in materiais_cache:
                        mat_info = buscador.extrair_informacoes_material(mat_completo)
                        
                        # Verifica se é o mesmo material (por código ou descrição)
                        if (mat_info.get('codigo_material') == mat_selecionado.get('codigo') or
                            mat_info.get('codigo_material') == mat_selecionado.get('descricao')):
                            
                            # Adiciona a quantidade selecionada
                            mat_info['quantidade'] = mat_selecionado.get('quantidade', '1')
                            materiais_completos.append(mat_info)
                            break
                
            except Exception as e:
                print(f"⚠️ Erro ao buscar detalhes dos materiais: {e}")
                # Usa os dados que já temos
                materiais_completos = info['materiais_selecionados']
        else:
            print("⚠️ Cache de materiais não encontrado. Usando dados parciais.")
            materiais_completos = info['materiais_selecionados']
        
        # Cria o formulário de separação
        creator = POSTe.SeparacaoMaterialCreator()
        
        # IMPORTANTE: Os IDs de mapeamento precisam ser configurados primeiro
        print("⚠️ ATENÇÃO: Os IDs de mapeamento no SeparacaoMaterialCreator precisam ser configurados!")
        
        separacao_id = creator.criar_separacao_completa(
            identificacao=identificacao,
            materiais=materiais_completos,
            assignee_id=user_id,
            creator_id=user_id
        )
        
        if separacao_id:
            print(f"✅ Processamento do Cenário 2 concluído. Separação ID: {separacao_id}")
        else:
            print("❌ Falha no Cenário 2: Erro na criação do formulário de separação.")
        
        return
    
    else:
        print("\n⏹️ Nenhuma condição atendida no processamento em background.")
        return


def criar_app_fastapi():
    """Cria e configura a aplicação FastAPI com Background Tasks e cache de IDs"""
    app = FastAPI(title="Webhook Processor - Materiais", version="1.0.0")
    
    WEBHOOK_ID_CACHE_FILE = 'webhook_cache_materials.json'
    MAX_CACHE_SIZE = 200

    def ler_cache_de_ids() -> List[str]:
        """Lê a lista de IDs de webhooks processados do arquivo de cache"""
        try:
            with open(WEBHOOK_ID_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def salvar_cache_de_ids(ids: List[str]):
        """Salva a lista atualizada de IDs no arquivo de cache"""
        try:
            with open(WEBHOOK_ID_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(ids, f)
        except IOError as e:
            print(f"❌ Erro ao salvar o cache de webhooks: {e}")

    @app.get("/")
    async def root():
        """Endpoint raiz para verificar se o servidor está rodando"""
        return {
            "status": "online",
            "service": "Webhook Processor - Materiais",
            "endpoints": ["/webhook", "/health"]
        }

    @app.get("/health")
    async def health_check():
        """Endpoint de health check"""
        return {"status": "healthy", "timestamp": json.dumps(str(hash(str(time.time()))))}

    @app.post("/webhook")
    async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
        """Endpoint principal que recebe os webhooks"""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400, 
                content={"status": "erro", "motivo": "Payload inválido - JSON mal formado"}
            )

        # Gera ID único para o webhook
        try:
            form_id = body.get('_id', {}).get('$oid')
            updated_at = body.get('updated_at')
            
            if not form_id or not updated_at:
                raise KeyError("IDs não encontrados no formato esperado")
            
            current_id = hashlib.md5(f"{form_id}-{updated_at}".encode()).hexdigest()
        except (KeyError, AttributeError):
            # Fallback: usa hash do payload completo
            current_id = hashlib.md5(json.dumps(body, sort_keys=True).encode()).hexdigest()
        
        # Verifica duplicação
        cached_ids = ler_cache_de_ids()
        if current_id in cached_ids:
            print(f"🔄 Webhook duplicado detectado (ID: {current_id[:8]}). Ignorando.")
            return JSONResponse(
                status_code=200, 
                content={"status": "ignorado", "reason": "duplicate", "id": current_id[:8]}
            )
        
        # Adiciona ao cache
        cached_ids.append(current_id)
        salvar_cache_de_ids(cached_ids[-MAX_CACHE_SIZE:])
        
        # Agenda processamento em background
        background_tasks.add_task(handle_webhook_logic, body)
        
        print(f"✅ Webhook (ID: {current_id[:8]}) aceito. Agendado para processamento.")
        return JSONResponse(
            status_code=202, 
            content={
                "status": "aceito", 
                "detail": "Webhook recebido e agendado para processamento",
                "id": current_id[:8]
            }
        )
    
    return app


# Importação necessária para o health check
import time
