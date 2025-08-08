import json
import hashlib
from typing import List, Dict
from datetime import datetime

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


def extrair_informacoes_materiais(data: dict) -> dict:
    """
    Extrai informações do webhook para o sistema de materiais.
    Detecta automaticamente se é Abertura de Projetos ou Separação de Materiais.
    """
    template_name = data.get("template_name", "")

    # Se for Separação de Materiais
    if template_name == "Separação de Materiais":
        return extrair_informacoes_separacao_materiais(data)
    # Se for Abertura de Projetos
    else:
        return extrair_informacoes_abertura_projetos(data)


def extrair_informacoes_abertura_projetos(data: dict) -> dict:
    """
    Extrai informações do webhook de Abertura de Projetos.
    """
    info = {
        # Dados do cliente
        "nome_fantasia": None,
        "cnpj": None,
        "razao_social": None,
        "contato_cliente": None,
        "email_cliente": None,
        "telefone": None,
        "cargo_funcao": None,

        # Controle
        "gerar_materiais": False,

        # Listas de materiais por serviço
        "materiais_servico_1": [],
        "materiais_servico_2": [],
        "materiais_servico_3": [],

        # IDs
        "user_id": None,
        "execution_company_id": None,
        "template_name": "Abertura de Projetos"
    }

    # Extrai IDs
    info['user_id'] = data.get('user_id', {}).get('$oid')
    info['execution_company_id'] = data.get('execution_company_id', {}).get('$oid')

    # Mapeia os IDs das perguntas de materiais
    MATERIAL_QUESTIONS_IDS = {
        "7801b46e101e48f49c94d869c1867c14": "materiais_servico_1",  # Materiais Serviço 1
        "1ddbf377795b45b9b7460b8e4a722679": "materiais_servico_2",  # Materiais Serviço 2
        "44643698731841429bf167389d08dbe7": "materiais_servico_3"  # Materiais Serviço 3
    }

    for question in data.get("template_questions", []):
        q_text = question.get("question")
        q_value = question.get("value")
        q_id = question.get("_id")

        # Dados de identificação
        if q_text == "Nome Fantasia":
            info["nome_fantasia"] = q_value
        elif q_text == "CNPJ":
            info["cnpj"] = q_value
        elif q_text == "Razão Social":
            info["razao_social"] = q_value
        elif q_text == "Contato no Cliente":
            info["contato_cliente"] = q_value
        elif q_text == "E-mail do Cliente":
            info["email_cliente"] = q_value
        elif q_text == "Telefone":
            info["telefone"] = q_value
        elif q_text == "Cargo/Função":
            info["cargo_funcao"] = q_value
        elif q_text == "Gerar Materiais":
            info["gerar_materiais"] = q_value == "true"

        # Processa sub_checklists de materiais
        elif q_id in MATERIAL_QUESTIONS_IDS and "sub_checklists" in question:
            servico_key = MATERIAL_QUESTIONS_IDS[q_id]

            for sub_checklist in question.get("sub_checklists", []):
                material_info = {}

                for sub_q in sub_checklist.get("sub_checklist_questions", []):
                    sub_q_text = sub_q.get("question")
                    sub_q_value = sub_q.get("value")

                    # Normaliza os nomes dos campos
                    if "Material" in sub_q_text:
                        material_info["material"] = sub_q_value
                    elif "Qtde" in sub_q_text:
                        material_info["quantidade"] = sub_q_value
                    elif "Valor Unit" in sub_q_text:
                        material_info["valor_unitario"] = sub_q_value
                    elif "Valor de Venda" in sub_q_text:
                        material_info["valor_venda"] = sub_q_value
                    elif "Total de Venda" in sub_q_text:
                        material_info["total_venda"] = sub_q_value

                if material_info:
                    info[servico_key].append(material_info)

    return info


def extrair_informacoes_separacao_materiais(data: dict) -> dict:
    """
    Extrai informações do webhook de Separação de Materiais.
    """
    info = {
        # Dados do cliente
        "nome_fantasia": None,
        "cnpj": None,
        "razao_social": None,
        "contato_cliente": None,
        "email_cliente": None,
        "telefone": None,
        "cargo_funcao": None,

        # Controle
        "necessita_compra": False,

        # Lista de materiais para separação
        "materiais_separacao": [],

        # Responsável
        "responsavel_separacao": None,
        "assinatura_responsavel": None,

        # IDs
        "user_id": None,
        "execution_company_id": None,
        "template_name": "Separação de Materiais"
    }

    # Extrai IDs
    info['user_id'] = data.get('user_id', {}).get('$oid')
    info['execution_company_id'] = data.get('execution_company_id', {}).get('$oid')

    for question in data.get("template_questions", []):
        q_text = question.get("question")
        q_value = question.get("value")
        q_id = question.get("_id")

        # Dados de identificação
        if q_text == "Nome Fantasia":
            info["nome_fantasia"] = q_value
        elif q_text == "CNPJ":
            info["cnpj"] = q_value
        elif q_text == "Razão Social":
            info["razao_social"] = q_value
        elif q_text == "Contato no Cliente":
            info["contato_cliente"] = q_value
        elif q_text == "E-mail do Cliente":
            info["email_cliente"] = q_value
        elif q_text == "Telefone":
            info["telefone"] = q_value
        elif q_text == "Cargo/Função":
            info["cargo_funcao"] = q_value
        elif q_text == "Necessita Compra":
            info["necessita_compra"] = q_value == "true"
        elif q_text == "Nome do Responsável pela Separação":
            info["responsavel_separacao"] = q_value
        elif q_text == "Assinatura do Responsável pela Separação dos Materiais":
            info["assinatura_responsavel"] = q_value

        # Processa sub_checklists de materiais (ID: 7801b46e101e48f49c94d869c1867c14)
        elif q_id == "7801b46e101e48f49c94d869c1867c14" and "sub_checklists" in question:
            for sub_checklist in question.get("sub_checklists", []):
                material_info = {
                    "material": None,
                    "quantidade": None,
                    "status_produto": None,
                    "separado": False,
                    "imagem": None
                }

                for sub_q in sub_checklist.get("sub_checklist_questions", []):
                    sub_q_text = sub_q.get("question")
                    sub_q_value = sub_q.get("value")

                    if sub_q_text == "Material":
                        material_info["material"] = sub_q_value
                    elif sub_q_text == "Quantidade":
                        material_info["quantidade"] = sub_q_value
                    elif sub_q_text == "Separado":
                        material_info["separado"] = sub_q_value == "true"
                    elif sub_q_text == "Imagem do Material Separado":
                        material_info["imagem"] = sub_q_value
                    elif sub_q_text == "Status do Produto":
                        # Procura qual opção está marcada como true
                        for option in sub_q.get("options", []):
                            if option.get("value") == "true":
                                material_info["status_produto"] = option.get("text")
                                break

                if material_info["material"]:  # Só adiciona se tiver material
                    info["materiais_separacao"].append(material_info)

    return info


def handle_webhook_logic(payload: dict):
    """Handler unificado que detecta o tipo de webhook e direciona para o processamento correto."""
    template_name = payload.get('template_name', '')
    form_id = payload.get('_id', {}).get('$oid')
    exec_id = _extract_exec_id(payload)

    print(f"\n--- WEBHOOK RECEBIDO: {template_name} ---")
    print(f"Formulário ID: {form_id} | Empresa ID: {exec_id}")

    # Webhooks de Materiais
    if template_name in ["Abertura de Projetos", "Separação de Materiais"]:
        print("📦 Tipo detectado: Sistema de Materiais")
        return handle_webhook_materiais_logic(payload)

    # Webhooks de Fiscalização (futuro)
    elif template_name in ["Planejamento de Fiscalização", "Checklist de Fiscalização"]:
        print("⚠️ Tipo detectado: Sistema de Fiscalização (não implementado)")
        print("ℹ️ O sistema de fiscalização será implementado em versão futura.")
        return

    # Webhooks de Cadastro
    elif template_name in ["Cadastro de Itens", "Cadastro de Materiais"]:
        print("📝 Tipo detectado: Sistema de Cadastros")
        print("ℹ️ Processamento de cadastros não implementado ainda.")
        return

    # Outros tipos não mapeados
    else:
        print(f"❓ Template '{template_name}' não reconhecido")
        print("ℹ️ Nenhum processamento específico disponível para este tipo.")

        # Log detalhado para debug
        print("\n📋 Detalhes do webhook:")
        print(f"- Status: {payload.get('execution_status', 'N/A')}")
        print(f"- Usuário: {payload.get('user_id', {}).get('$oid', 'N/A')}")
        print(f"- Seções: {len(payload.get('template_sections', []))}")
        print(f"- Perguntas: {len(payload.get('template_questions', []))}")

        return


def handle_webhook_materiais_logic(payload: dict):
    """Lógica de processamento para webhooks de materiais."""
    info = extrair_informacoes_materiais(payload)
    form_id = payload.get('_id', {}).get('$oid')
    exec_id = info.get('execution_company_id')
    user_id = info.get('user_id')
    template_name = info.get('template_name')

    print(f"\n--- INICIANDO PROCESSAMENTO DE {template_name.upper()} EM BACKGROUND ---")
    print(f"Formulário ID: {form_id} | Empresa ID: {exec_id}")

    if template_name == "Abertura de Projetos":
        # Lógica para Abertura de Projetos
        print(f"Flag 'Gerar Materiais': {info['gerar_materiais']}")
        if info.get("materiais_servico_1") is None:
            print("⚠️ Nenhum material encontrado para o Serviço 1.")
        else:
            print(f"Materiais do Serviço 1: {len(info['materiais_servico_1'])} encontrados.")
            materiais_servico_1 = info['materiais_servico_1']
        if info.get("materiais_servico_2") is None:
            print("⚠️ Nenhum material encontrado para o Serviço 2.")
        else:
            print(f"Materiais do Serviço 2: {len(info['materiais_servico_2'])} encontrados.")
            materiais_servico_2 = info['materiais_servico_2']
        if info.get("materiais_servico_3") is None:
            print("⚠️ Nenhum material encontrado para o Serviço 3.")
        else:
            print(f"Materiais do Serviço 3: {len(info['materiais_servico_3'])} encontrados.")
            materiais_servico_3 = info['materiais_servico_3']

        total_materiais = (len(materiais_servico_1) +
                           len(materiais_servico_2) +
                           len(materiais_servico_3))

        print(f"Total de materiais encontrados: {total_materiais}")

        if not info['gerar_materiais'] and total_materiais > 0:
            print("\n▶️ Processando materiais de Abertura de Projetos...")
            print(f"Cliente: {info['nome_fantasia']} ({info['cnpj']})")

            # Consolida todos os materiais em uma lista única
            todos_materiais = []

            for servico_num in [1, 2, 3]:
                materiais = info[f'materiais_servico_{servico_num}']
                if materiais is not None and len(materiais) > 0:
                    print(f"\nMateriais do Serviço {servico_num}:")
                    for mat in materiais:
                        print(
                            f"  - {mat.get('material')} | Qtd: {mat.get('quantidade')} | Valor: {mat.get('valor_venda')}")
                        # Adiciona à lista consolidada com formato para separação
                        todos_materiais.append({
                            "material": mat.get('material'),
                            "quantidade": mat.get('quantidade')
                        })

            # Cria o checklist de Separação de Materiais
            if todos_materiais and exec_id:
                print(f"\n▶️ Criando checklist de Separação de Materiais com {len(todos_materiais)} itens...")

                # Prepara dados de identificação do cliente
                identificacao = {
                    "nome_fantasia": info.get('nome_fantasia'),
                    "cnpj": info.get('cnpj'),
                    "razao_social": info.get('razao_social'),
                    "contato_cliente": info.get('contato_cliente'),
                    "email_cliente": info.get('email_cliente'),
                    "telefone": info.get('telefone'),
                    "cargo_funcao": info.get('cargo_funcao')
                }

                creator = ChecklistCreator()
                checklist_id = creator.criar_checklist_separacao_materiais(
                    identificacao=identificacao,
                    execution_company_id=exec_id,
                    materiais=todos_materiais,
                    assignee_id=user_id,
                    creator_id=user_id
                )

                if checklist_id:
                    print(f"✅ Checklist de Separação de Materiais criado com sucesso! ID: {checklist_id}")
                else:
                    print("❌ Erro ao criar checklist de Separação de Materiais.")
            else:
                print("⚠️ Não foi possível criar checklist: sem materiais ou sem ID da empresa.")

            print("\n✅ Processamento de materiais concluído.")
        else:
            if not info['gerar_materiais']:
                print("\n⏹️ Flag 'Gerar Materiais' não está ativa.")
            else:
                print("\n⏹️ Nenhum material encontrado para processar.")

    elif template_name == "Separação de Materiais":
        # Lógica para Separação de Materiais
        print(f"Flag 'Necessita Compra': {info['necessita_compra']}")
        print(f"Responsável: {info['responsavel_separacao']}")

        total_materiais = len(info['materiais_separacao'])
        materiais_separados = sum(1 for mat in info['materiais_separacao'] if mat['separado'])
        materiais_comprar = sum(1 for mat in info['materiais_separacao'] if mat['status_produto'] == 'Item a Comprar')

        print(f"\nTotal de materiais: {total_materiais}")
        print(f"Materiais separados: {materiais_separados}")
        print(f"Materiais a comprar: {materiais_comprar}")

        if info['materiais_separacao']:
            print("\n▶️ Lista de materiais:")
            for mat in info['materiais_separacao']:
                status = "✅" if mat['separado'] else "❌"
                print(f"  {status} {mat['material']} | Qtd: {mat['quantidade']} | Status: {mat['status_produto']}")

        if info['necessita_compra'] and materiais_comprar > 0:
            print("\n▶️ Gerando lista de compras...")
            # TODO: Implementar lógica para gerar pedido de compra
            print("✅ Lista de compras gerada.")

        print("\n✅ Processamento de separação de materiais concluído.")


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
        try:
            with open(WEBHOOK_ID_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(ids, f)
        except IOError as e:
            print(f"❌ Erro ao salvar o cache de webhooks: {e}")

    @app.post("/webhook")
    async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
        try:
            body = await request.json()

            # DEBUG: Salvar o dump (remover em produção)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            template_name = body.get('template_name', 'unknown').replace(' ', '_')
            with open(f'webhook_{template_name}_{timestamp}.json', 'w', encoding='utf-8') as f:
                json.dump(body, f, indent=2, ensure_ascii=False)

        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"status": "erro", "motivo": "Payload inválido."})

        try:
            form_id = body.get('_id', {}).get('$oid')
            updated_at = body.get('updated_at')
            if not form_id or not updated_at:
                raise KeyError("IDs não encontrados no formato esperado")
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

        template_name = body.get('template_name', 'Desconhecido')
        print(f"✅ Webhook '{template_name}' (ID: {current_id[:8]}) aceito. Agendado para processamento.")
        return JSONResponse(status_code=202, content={
            "status": "aceito",
            "detail": "Webhook recebido.",
            "template": template_name
        })

    return app