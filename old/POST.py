import time
import requests
import json
from typing import Dict, List, Any
import math


# A linha "from concurrent.futures import ThreadPoolExecutor, as_completed" deve ser removida

class ChecklistCreator:
    def __init__(self):
        self.base_url = "https://app.way-v.com/api/integration"
        self.token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb21wYW55X2lkIjoiNjYzZDMxYTFlOWRhYzNmNWY0ZDNjZjJlIiwiY3VycmVudF90aW1lIjoxNzQ4OTUzODcyNjgzLCJleHAiOjIwNjQ0ODY2NzJ9.j6zOrJMDKNcCcMMcO99SudriP7KqEDLMJDE2FBlQ6ok'
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        self.template_id_fiscalizacao = "67f6bfe0aa27d85466bdbb87"
        self.question_ids_fiscalizacao = {
            'FA': '934f80ddd425479b969227c01a5c2eda', 'FT': '9ef230b33c3c435fbe83298d41acc30a',
            'FO': '8c517d351f15462aa62b4c9ac7e6b43e', 'GC': '6e6de895e4604ba78f18e154072be80e',
            'VC': '438dc9b0b7394a72b6ff5008d7574824'
        }
        self.sub_question_mapping_fiscalizacao = {
            'FA': {'item': '3396430e77c74faebb2ebbfefac98b37', 'codigo': '5a507221009d479a87fe3ac2de9b1919',
                   'instrumento': 'b97d97f46fc04c15a2c301949d1b8861', 'dimensao': '3c12a83a05b7482193cbf32d511c864e',
                   'verificacao': 'e758f7b11b2e4d4f99eea9520711a8b1', 'av': '25022d88d8d342c7bb81e77896378032',
                   'peso': 'fd2cc26145c64297b55f002f5552fb8d', 'indicador': '68015fa3daf29bba925f3db7'},
            'FT': {'item': 'b3f6d94b422a426a90f38ce833f1d8e5', 'codigo': '61a996bc1fc34a79a057337493e40b82',
                   'instrumento': 'b2a7a4c6f8e147f4a05ec7078f8fa701', 'dimensao': '340e1d43c30f44c688feb46a2a67804e',
                   'verificacao': 'af52a22123a64a5c90cea2d9879ecc8a', 'indicador': 'a2a45ba1f55f47a5919371ad569afc15',
                   'av': '5b424d95b0564b8e8d7c5794b4339ef5', 'peso': '3f6a015c3b2a4c9fa34b9e243d55f54d'},
            'FO': {'item': '24039db27aa8414cb886c60f379c311e', 'codigo': '683f4b1dc4a5538b711b0f01',
                   'instrumento': '18d14859aacf40f8a1ef25e42444c969', 'dimensao': '83a2870b2f7845aaab120084d5337ac7',
                   'verificacao': '5904a66402a44734b20404dd51d2f95c', 'indicador': '4435bc77d6234f0d85cf73ea2ac3992b',
                   'av': '4dbab1cc69714abba9c7d71a334a7681', 'peso': 'a750de10487c4a0a9483992b9062456f'},
            'GC': {'item': 'a55b817719214888a93b2f388d372263', 'instrumento': '1a40fe0f826841da8b43ffeba3c1eeae',
                   'codigo': '683f4f9f6019b1f3b94bbeff', 'dimensao': '597dcedfa3a9431d997dfca22f19dd1d',
                   'verificacao': 'e4b50d1f4165477fa7902d033700dd88', 'indicador': '57e1268b630149998a83e568372b3453',
                   'av': '16094d6622e547b18655731a5b2d4078', 'peso': 'ca2286fe3f784b568deb19c85e3242b3'},
            'VC': {'item': 'bdb01f91a9774e51ac61cc3cb1d73920', 'instrumento': '5a1e10805d00494eaa8b8f84b321e4d0',
                   'codigo': '683f51034c5aa9678b216f1e', 'dimensao': '954901ca7d034cb7ae6695ba36497cdc',
                   'verificacao': 'c81768535b3f4ded9ca03b6302d1fbe1', 'indicador': '4466ffcbe37b4506b42922a9e6743fc8',
                   'av': '388a99bb2c8d47ce8abd5d1e7f4a2ca1', 'peso': '3396de2bc98447b1b339a937056bfc30'}
        }
        self.identification_questions = {
            'data_prevista': '8113d0edd61c4cf6bf65ec10bdf68cda',
            'contrato_concessao': '11caa9daefcd41bcade0fb221886758b',
            'identificador': '9c51272c7c774224b4dd2783b5fe62d4', 'concessionaria': '8838d1ca06bb4e0ba842b0e1adc5d949'
        }

        self.question_id_subform_itens = "5a3c6db29f4c4968af9cb67001570e7b"
        self.sub_question_id_item_col = "686840cf8bb23d7cf663bbb8"

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

    # --- MÉTODO MODIFICADO ---
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
                "template_id": self.template_id_fiscalizacao,
                "execution_company_id": execution_company_id,
                "assignee_id": assignee_id,
                "creator_id": creator_id,
                "status_info": {
                    "new_execution_status": "pending"
                },
                "questions": []
            }
        }
        for campo, question_id in self.identification_questions.items():
            valor = identificacao.get(campo)
            if valor:
                checklist_data["checklist"]["questions"].append(
                    {"id": question_id, "sub_questions": [{"id": "1", "value": valor}]})
        for tipo in self.question_ids_fiscalizacao.keys():
            checklist_data["checklist"]["questions"].append(
                {"id": self.question_ids_fiscalizacao[tipo], "sub_questions": []})

        print(f"📝 Criando checklist principal para a empresa {execution_company_id} com status 'pending'...")
        response = requests.post(f"{self.base_url}/checklists", headers=self.headers, json=checklist_data)
        if response.status_code not in [200, 201]:
            print(f"❌ Erro ao criar checklist: {response.status_code}\n{response.text}")
            return None
        else:
            checklist_id = response.json()["_id"]["$oid"]
            print(f"✅ Checklist criado com id: {checklist_id}")
            return checklist_id

    def adicionar_subchecklists_fiscalizacao(self, checklist_id: str, tipo: str, itens: List[Dict[str, Any]]):
        if not itens: return
        print(f"📋 Adicionando {len(itens)} itens de fiscalização para a categoria {tipo}...")
        sub_checklists = []
        question_mapping = self.sub_question_mapping_fiscalizacao[tipo]
        for item_data in itens:
            sub_checklist_questions = []
            for campo, question_id in question_mapping.items():
                if campo in item_data and item_data[campo] is not None:
                    sub_checklist_questions.append({"question_id": question_id, "value": str(item_data[campo])})
            sub_checklists.append(
                {"id": self.question_ids_fiscalizacao[tipo], "sub_checklist_questions": sub_checklist_questions})
        payload = {"checklist_id": checklist_id, "sub_checklists": sub_checklists}
        response = requests.post(f"{self.base_url}/subchecklists", headers=self.headers, json=payload, timeout=90)
        if response.status_code not in [200, 201]:
            print(f"❌ Erro ao adicionar itens para {tipo}: {response.status_code}\n{response.text}")

    def criar_checklist_completo(self, identificacao: Dict[str, str], execution_company_id: str,
                                 itens_por_tipo: Dict[str, List[Dict]] = None,
                                 assignee_id: str = None, creator_id: str = None):
        checklist_id = self.criar_checklist_principal(identificacao=identificacao,
                                                      execution_company_id=execution_company_id,
                                                      assignee_id=assignee_id, creator_id=creator_id)
        if not checklist_id: return None
        if not itens_por_tipo: return None
        print("⏳ Aguardando 2 segundos antes de adicionar subchecklists...")
        time.sleep(2)
        for tipo, itens in itens_por_tipo.items():
            if tipo in self.question_ids_fiscalizacao and itens:
                self.adicionar_subchecklists_fiscalizacao(checklist_id, tipo, itens)
        return checklist_id