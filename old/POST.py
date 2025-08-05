import time
import requests
import json
from typing import Dict, List, Any
import math


# A linha "from concurrent.futures import ThreadPoolExecutor, as_completed" deve ser removida

class ChecklistCreator:
    def __init__(self):
        self.base_url = "https://app.way-v.com/api/integration"
        self.token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb21wYW55X2lkIjoiNjg1ZDdjMjJlYmM1MzJiMzhjYzYwMmNlIiwiY3VycmVudF90aW1lIjoxNzUzODExOTEwMTI2LCJleHAiOjIwNjkzNDQ3MTB9.aTCOVKgjvNRVBPcwIFiWzTTJlu28jfzUuvI26zYfZkA'
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        self.template_id_materiais = "6877fc37e833bf57706a2edf"

        self.sub_question_mapping_abertura = {'material': '7559766a25f94622b2f3df928c3ee660', 'quantidade': '85d5271fdfce4aef86273533eea24804'}

        self.sub_question_mapping_materiais = {
            'item': '1d5015491a8b404db59b95891cf00b22', 'unidade': '54f2e2ef14a14113a2dfd33cd87eb397', 'subcategoria': 'f1e2e64f6eac4752b88435db97c81571', 'valor': '783f2490e5104e3f9b291bd851980281'
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

    # --- MÉTDO MODIFICADO ---
    def popular_formulario_planejamento(self, form_id: str, clausulas: List[str]):
        if not clausulas:
            print("ℹ️ Nenhuma cláusula de cadastro encontrada para popular.")
            return

        print(f"📋 Preparando para popular o formulário ID: {form_id} com {len(clausulas)} cláusulas...")

        sub_checklists_para_adicionar = [
            {"id": self.question_id_subform_itens,
             "sub_checklist_questions": [{"question_id": self.sub_question_id_item_col, "value": str(clausula)}]}
            for clausula in clausulas
        ]

        if not sub_checklists_para_adicionar:
            print("⚠️ Nenhum subchecklist foi preparado.")
            return

        batch_size = 150
        payloads = [
            {"checklist_id": form_id, "sub_checklists": sub_checklists_para_adicionar[i:i + batch_size]}
            for i in range(0, len(sub_checklists_para_adicionar), batch_size)
        ]

        total_lotes = len(payloads)
        print(
            f"📦 Total de {len(sub_checklists_para_adicionar)} itens a serem enviados em {total_lotes} lotes sequenciais.")

        success_count = 0
        for i, payload in enumerate(payloads):
            batch_num = i + 1
            print(f"➡️ Enviando lote {batch_num}/{total_lotes}...")

            # Chama o envio para o lote atual e aguarda o resultado
            success = self._send_request(payload, batch_num)

            # Se o envio falhar, interrompe o processo
            if success:
                success_count += 1
            else:
                print(f"🛑 Envio interrompido devido a erro no lote {batch_num}.")
                break

        if success_count == total_lotes:
            print("🎉 Formulário populado com sucesso! Todos os lotes foram enviados.")
        else:
            print(
                f"⚠️ Processo de população concluído com falhas. {success_count} de {total_lotes} lotes enviados com sucesso.")

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

    def adicionar_subchecklists_materiais(self, checklist_id: str, itens: List[Dict[str, Any]]):
        if not itens: return
        print(f"📋 Adicionando {len(itens)} itens de materiais...")
        sub_checklists = []
        question_mapping = self.sub_question_mapping_materiais
        for item_data in itens:
            sub_checklist_questions = []
            for campo, question_id in question_mapping.items():
                if campo in item_data and item_data[campo] is not None:
                    sub_checklist_questions.append({"question_id": question_id, "value": str(item_data[campo])})
            sub_checklists.append(
                {"id": self.sub_question_mapping_materiais, "sub_checklist_questions": sub_checklist_questions})
        payload = {"checklist_id": checklist_id, "sub_checklists": sub_checklists}
        response = requests.post(f"{self.base_url}/subchecklists", headers=self.headers, json=payload, timeout=90)
        if response.status_code not in [200, 201]:
            print(f"❌ Erro ao adicionar itens: {response.status_code}\n{response.text}")

    def criar_checklist_completo(self, identificacao: Dict[str, str], execution_company_id: str,
                                 itens: Dict[str, List[Dict]] = None,
                                 assignee_id: str = None, creator_id: str = None):
        checklist_id = self.criar_checklist_principal(identificacao=identificacao,
                                                      execution_company_id=execution_company_id,
                                                      assignee_id=assignee_id, creator_id=creator_id)
        if not checklist_id: return None
        print("⏳ Aguardando 2 segundos antes de adicionar subchecklists...")
        time.sleep(2)
        self.adicionar_subchecklists_materiais(checklist_id, itens)
