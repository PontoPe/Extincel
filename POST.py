import time
import requests
import json
from typing import Dict, List, Any
import math


class ChecklistCreator:
    def __init__(self):
        self.base_url = "https://app.way-v.com/api/integration"
        self.token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb21wYW55X2lkIjoiNjg1ZDdjMjJlYmM1MzJiMzhjYzYwMmNlIiwiY3VycmVudF90aW1lIjoxNzUzODExOTEwMTI2LCJleHAiOjIwNjkzNDQ3MTB9.aTCOVKgjvNRVBPcwIFiWzTTJlu28jfzUuvI26zYfZkA'
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
            'imagem': 'cf08bcae0f9d443f994b9558e73825bd'
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