import time
import requests
import json
from typing import Dict, List, Any
import math


class ChecklistCreator:
    def __init__(self):
        self.base_url = "https://app.way-v.com/api/integration"
        self.token = os.getenv("WAYV_TOKEN_API")
        if not token:
            raise ValueError("O token TOKEN_API não foi encontrado nas variáveis de ambiente.") 
        
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        self.template_id_materiais = "6877fc37e833bf57706a2edf"

        # ID da pergunta do subformulário de materiais no template de Separação
        self.question_id_materiais_separacao = "7801b46e101e48f49c94d869c1867c14"

        self.sub_question_mapping_abertura = {
            'material': '7559766a25f94622b2f3df928c3ee660',
            'quantidade': '85d5271fdfce4aef86273533eea24804'
        }

        # Mapeamento para os subcampos de materiais na Separação
        self.sub_question_mapping_separacao = {
            'material': '2fcf125b16c8483c97e4bc8c57ee453b',
            'quantidade': 'fda6238d6c1d4bc79586bd7604d76ccf',
            'status_produto': 'ec608e7eac574de788e8a6f3794b3bb7',
            'separado': 'c6930a0e081242a6a3366f4aa102b106',
            'imagem': 'cf08bcae0f9d443f994b9558e73825bd',
            'valor_unitario': '33e189ac9bee4b5b9a8f443ecc62ac3a'
        }

        self.sub_question_mapping_materiais = {
            'item': '1d5015491a8b404db59b95891cf00b22',
            'unidade': '54f2e2ef14a14113a2dfd33cd87eb397',
            'subcategoria': 'f1e2e64f6eac4752b88435db97c81571',
            'valor': '783f2490e5104e3f9b291bd851980281'
        }

        self.identification_question_mapping_materiais = {
            'nome_fantasia': '56d556a4bb354355a8a65994bee361fe',
            'cnpj': 'd00366e3b9d64fcba8866854615de85d',
            'contato_cliente': '68200775db174fa9b78d7596f84bf952',
            'email_cliente': '3ef550c6232940509338ebe1c8207148',
            'razao_social': 'e9997ac0cf2a470883bf838b2c5381ac',
            'cargo_funcao': 'd902b4d597a14d18b7cb79573b0b4016',
            'telefone': '129497cacaec4d3aaba284c72ca72534'
        }

        self.identification_question_mapping_cadastro = {
            'nome_fantasia': '56d556a4bb354355a8a65994bee361fe',
            'cnpj': 'd00366e3b9d64fcba8866854615de85d',
            'contato_cliente': '68200775db174fa9b78d7596f84bf952',
            'email_cliente': '3ef550c6232940509338ebe1c8207148',
            'razao_social': 'e9997ac0cf2a470883bf838b2c5381ac',
            'cargo_funcao': 'd902b4d597a14d18b7cb79573b0b4016',
            'telefone': '129497cacaec4d3aaba284c72ca72534'
        }

        self.template_id_ordem_compra = "6876adf1919af1f97652c2d2"  # Você precisa confirmar este ID

        # Mapeamento das perguntas de identificação para Ordem de Compra (mesmas da separação)
        self.identification_question_mapping_ordem_compra = {
            'nome_fantasia': '56d556a4bb354355a8a65994bee361fe',
            'cnpj': 'd00366e3b9d64fcba8866854615de85d',
            'contato_cliente': '68200775db174fa9b78d7596f84bf952',
            'email_cliente': '3ef550c6232940509338ebe1c8207148',
            'razao_social': 'e9997ac0cf2a470883bf838b2c5381ac',
            'cargo_funcao': 'd902b4d597a14d18b7cb79573b0b4016',
            'telefone': '129497cacaec4d3aaba284c72ca72534'
        }

        # Mapeamento das perguntas da seção Recebimento
        self.recebimento_question_mapping = {
            'data_recebimento': '7dd07c8495144180a629c1e225812c8e',
            'nota_fiscal': 'ccf775368f654635977f2ff5927ccd49'
        }

        # Mapeamento das perguntas de controle
        self.controle_question_mapping = {
            'bloqueia_questoes': 'ea27f7753abf46938b14bf1313bf6175',
            'aprovacao_compra': 'e2d803b9e8b24ba3a1f5e132cfb91f40'
        }

        # ID da pergunta do subformulário de materiais para compra
        self.question_id_materiais_compra = "7801b46e101e48f49c94d869c1867c14"

        # Mapeamento dos subcampos de materiais na Ordem de Compra
        self.sub_question_mapping_ordem_compra = {
            'material': '10b58ea788f64e069ca1266af4848f36',
            'quantidade': 'e857556a367645f0ab0e19f22012b870',
            'valor_compra': 'a5aa0c14931e4944a7dfa297d5b7b543'
        }

    def _send_request(self, payload: Dict, batch_num: int) -> bool:
        try:
            response = requests.post(f"{self.base_url}/subchecklists", headers=self.headers, json=payload, timeout=90)
            if response.status_code not in [200, 201]:
                print(f"❌ ERRO no lote {batch_num}: Status {response.status_code}\n{response.text}")
                return False
            else:
                print(f"✅ Lote {batch_num} enviado com sucesso.")
                return True
        except requests.exceptions.RequestException as e:
            print(f"❌ ERRO DE CONEXÃO no lote {batch_num}: {e}")
            return False

    def criar_checklist_principal(self, identificacao: Dict[str, str], execution_company_id: str,
                                  assignee_id: str = None, creator_id: str = None):
        checklist_data = {
            "checklist": {
                "template_id": self.template_id_materiais,
                "execution_company_id": execution_company_id,
                "assignee_id": assignee_id,
                "creator_id": creator_id,
                "status_info": {
                    "new_execution_status": "pending"
                },
                "questions": []
            }
        }
        for campo, question_id in self.identification_question_mapping_materiais.items():
            valor = identificacao.get(campo)
            if valor:
                checklist_data["checklist"]["questions"].append(
                    {"id": question_id, "sub_questions": [{"id": "1", "value": valor}]})

        print(f"📝 Criando checklist principal para a empresa {execution_company_id} com status 'pending'...")
        response = requests.post(f"{self.base_url}/checklists", headers=self.headers, json=checklist_data)
        if response.status_code not in [200, 201]:
            print(f"❌ Erro ao criar checklist: {response.status_code}\n{response.text}")
            return None
        else:
            checklist_id = response.json()["_id"]["$oid"]
            print(f"✅ Checklist criado com id: {checklist_id}")
            return checklist_id

    def adicionar_subchecklists_materiais(self, checklist_id: str, materiais: List[Dict[str, Any]]):
        """
        Adiciona materiais ao checklist de Separação de Materiais.
        """
        if not materiais:
            print("⚠️ Nenhum material para adicionar.")
            return

        print(f"📋 Adicionando {len(materiais)} materiais ao checklist de separação...")

        # Prepara os subchecklists
        sub_checklists = []

        for material in materiais:
            # Pula materiais sem nome
            if not material.get('material'):
                continue

            sub_checklist_questions = []

            # Material
            sub_checklist_questions.append({
                "question_id": self.sub_question_mapping_separacao['material'],
                "value": str(material['material'])
            })

            # Quantidade - usa '1' como padrão se não houver
            quantidade = material.get('quantidade') or '1'
            sub_checklist_questions.append({
                "question_id": self.sub_question_mapping_separacao['quantidade'],
                "value": str(quantidade)
            })

            valor = material.get('valor_unitario')
            if valor:
                sub_checklist_questions.append({
                    "question_id": self.sub_question_mapping_separacao['valor_unitario'],
                    "value": str(valor)
                })

            if sub_checklist_questions:
                sub_checklists.append({
                    "id": self.question_id_materiais_separacao,
                    "sub_checklist_questions": sub_checklist_questions
                })

        # Se não houver subchecklists válidos, retorna
        if not sub_checklists:
            print("⚠️ Nenhum material válido para adicionar.")
            return

        # Envia em lotes
        batch_size = 50
        total_enviados = 0

        for i in range(0, len(sub_checklists), batch_size):
            batch = sub_checklists[i:i + batch_size]
            payload = {
                "checklist_id": checklist_id,
                "sub_checklists": batch
            }

            batch_num = (i // batch_size) + 1
            total_batches = math.ceil(len(sub_checklists) / batch_size)

            print(f"📦 Enviando lote {batch_num}/{total_batches} com {len(batch)} materiais...")

            # DEBUG: Imprimir o payload para ver o que está sendo enviado
            print(f"DEBUG - Payload sendo enviado:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            try:
                response = requests.post(
                    f"{self.base_url}/subchecklists",
                    headers=self.headers,
                    json=payload,
                    timeout=90
                )

                if response.status_code in [200, 201]:
                    total_enviados += len(batch)
                    print(f"✅ Lote {batch_num} enviado com sucesso.")
                else:
                    print(f"❌ Erro ao adicionar materiais (lote {batch_num}): {response.status_code}")
                    print(f"Resposta: {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"❌ Erro de conexão ao enviar lote {batch_num}: {e}")

        print(f"\n📊 Total de materiais enviados: {total_enviados}/{len(sub_checklists)}")

    def criar_checklist_completo(self, identificacao: Dict[str, str], execution_company_id: str,
                                 itens: List[Dict] = None,
                                 assignee_id: str = None, creator_id: str = None):
        checklist_id = self.criar_checklist_principal(identificacao=identificacao,
                                                      execution_company_id=execution_company_id,
                                                      assignee_id=assignee_id, creator_id=creator_id)
        if not checklist_id:
            return None

        if itens:
            print("⏳ Aguardando 2 segundos antes de adicionar subchecklists...")
            time.sleep(2)
            self.adicionar_subchecklists_materiais(checklist_id, itens)

        return checklist_id

    def criar_checklist_separacao_materiais(self, identificacao: Dict[str, str], execution_company_id: str,
                                            materiais: List[Dict[str, Any]], assignee_id: str = None,
                                            creator_id: str = None):
        """
        Cria um checklist de Separação de Materiais com os materiais fornecidos.
        Usa o método criar_checklist_completo para garantir a criação correta.
        """
        return self.criar_checklist_completo(
            identificacao=identificacao,
            execution_company_id=execution_company_id,
            itens=materiais,
            assignee_id=assignee_id,
            creator_id=creator_id
        )

    def criar_checklist_ordem_compra(self, identificacao: Dict[str, str], execution_company_id: str,
                                     assignee_id: str = None, creator_id: str = None,
                                     data_recebimento: str = None):
        """
        Cria o checklist principal de Ordem de Compra.
        """
        checklist_data = {
            "checklist": {
                "template_id": self.template_id_ordem_compra,
                "execution_company_id": execution_company_id,
                "assignee_id": assignee_id,
                "creator_id": creator_id,
                "status_info": {
                    "new_execution_status": "pending"
                },
                "questions": []
            }
        }

        # Adiciona campos de identificação
        for campo, question_id in self.identification_question_mapping_ordem_compra.items():
            valor = identificacao.get(campo)
            if valor:
                checklist_data["checklist"]["questions"].append(
                    {"id": question_id, "sub_questions": [{"id": "1", "value": valor}]}
                )

        # Adiciona campos de recebimento (inicialmente vazios ou com valores padrão)
        if data_recebimento:
            checklist_data["checklist"]["questions"].append(
                {"id": self.recebimento_question_mapping['data_recebimento'],
                 "sub_questions": [{"id": "1", "value": data_recebimento}]}
            )

        print(f"📝 Criando Ordem de Compra para a empresa {execution_company_id}...")
        response = requests.post(f"{self.base_url}/checklists", headers=self.headers, json=checklist_data)

        if response.status_code not in [200, 201]:
            print(f"❌ Erro ao criar ordem de compra: {response.status_code}\n{response.text}")
            return None
        else:
            checklist_id = response.json()["_id"]["$oid"]
            print(f"✅ Ordem de Compra criada com id: {checklist_id}")
            return checklist_id

    def adicionar_materiais_ordem_compra(self, checklist_id: str, materiais: List[Dict[str, Any]]):
        """
        Adiciona materiais à Ordem de Compra.

        Args:
            checklist_id: ID do checklist de ordem de compra
            materiais: Lista de dicionários com 'material', 'quantidade' e opcionalmente 'valor_compra'
        """
        if not materiais:
            print("⚠️ Nenhum material para adicionar à ordem de compra.")
            return

        print(f"📋 Adicionando {len(materiais)} materiais à ordem de compra...")

        sub_checklists = []

        for material in materiais:
            # Pula materiais sem nome
            if not material.get('material'):
                continue

            sub_checklist_questions = []

            # Material (obrigatório)
            sub_checklist_questions.append({
                "question_id": self.sub_question_mapping_ordem_compra['material'],
                "value": str(material['material'])
            })

            # Quantidade (usa '1' como padrão se não houver)
            quantidade = material.get('quantidade', '1')
            sub_checklist_questions.append({
                "question_id": self.sub_question_mapping_ordem_compra['quantidade'],
                "value": str(quantidade)
            })

            # Valor de compra (opcional)
            valor_unit = material.get('valor_unitario')
            valor = int(material.get('quantidade')) * float(valor_unit) if valor_unit else material.get('valor_compra')
            sub_checklist_questions.append({
                    "question_id": self.sub_question_mapping_ordem_compra['valor_compra'],
                    "value": valor
                })

            if sub_checklist_questions:
                sub_checklists.append({
                    "id": self.question_id_materiais_compra,
                    "sub_checklist_questions": sub_checklist_questions
                })

        # Se não houver subchecklists válidos, retorna
        if not sub_checklists:
            print("⚠️ Nenhum material válido para adicionar.")
            return

        # Envia em lotes
        batch_size = 50
        total_enviados = 0

        for i in range(0, len(sub_checklists), batch_size):
            batch = sub_checklists[i:i + batch_size]
            payload = {
                "checklist_id": checklist_id,
                "sub_checklists": batch
            }

            batch_num = (i // batch_size) + 1
            total_batches = math.ceil(len(sub_checklists) / batch_size)

            print(f"📦 Enviando lote {batch_num}/{total_batches} com {len(batch)} materiais...")

            try:
                response = requests.post(
                    f"{self.base_url}/subchecklists",
                    headers=self.headers,
                    json=payload,
                    timeout=90
                )

                if response.status_code in [200, 201]:
                    total_enviados += len(batch)
                    print(f"✅ Lote {batch_num} enviado com sucesso.")
                else:
                    print(f"❌ Erro ao adicionar materiais (lote {batch_num}): {response.status_code}")
                    print(f"Resposta: {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"❌ Erro de conexão ao enviar lote {batch_num}: {e}")

        print(f"\n📊 Total de materiais enviados: {total_enviados}/{len(sub_checklists)}")

    def criar_ordem_compra_completa(self, identificacao: Dict[str, str],
                                    execution_company_id: str,
                                    materiais_compra: List[Dict],
                                    assignee_id: str = None,
                                    creator_id: str = None):
        """
        Cria uma Ordem de Compra completa com todos os materiais.

        Args:
            identificacao: Dados do cliente
            execution_company_id: ID da empresa
            materiais_compra: Lista de materiais para comprar
            assignee_id: ID do responsável
            creator_id: ID do criador
            valor_total: Valor total da compra (opcional)

        Returns:
            ID do checklist criado ou None em caso de erro
        """
        # Cria o checklist principal
        checklist_id = self.criar_checklist_ordem_compra(
            identificacao=identificacao,
            execution_company_id=execution_company_id,
            assignee_id=assignee_id,
            creator_id=creator_id
        )

        if not checklist_id:
            return None

        # Aguarda antes de adicionar subchecklists
        if materiais_compra:
            print("⏳ Aguardando 2 segundos antes de adicionar materiais...")
            time.sleep(2)
            self.adicionar_materiais_ordem_compra(checklist_id, materiais_compra)

        return checklist_id
