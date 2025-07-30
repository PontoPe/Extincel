import time
import requests
import json
from typing import Dict, List, Any, Optional


class SeparacaoMaterialCreator:
    def __init__(self):
        self.base_url = "https://app.way-v.com/api/integration"
        self.token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb21wYW55X2lkIjoiNjYzZDMxYTFlOWRhYzNmNWY0ZDNjZjJlIiwiY3VycmVudF90aW1lIjoxNzQ4OTUzODcyNjgzLCJleHAiOjIwNjQ0ODY2NzJ9.j6zOrJMDKNcCcMMcO99SudriP7KqEDLMJDE2FBlQ6ok'
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # IDs do template de separação de materiais
        self.template_id_separacao = "6877fc37e833bf57706a2edf"
        self.execution_company_id = "685d7c22ebc532b38cc602ce"

        # Mapeamento de IDs de questões (baseado na estrutura real do template)
        self.identification_questions = {
            'razao_social': 'e9997ac0cf2a470883bf838b2c5381ac',
            'nome_fantasia': '56d556a4bb354355a8a65994bee361fe',
            'cnpj': 'd00366e3b9d64fcba8866854615de85d',
            'contato_cliente': '68200775db174fa9b78d7596f84bf952',
            'cargo_funcao': 'd902b4d597a14d18b7cb79573b0b4016',
            'telefone': '129497cacaec4d3aaba284c72ca72534',
            'email_cliente': '3ef550c6232940509338ebe1c8207148',
            'responsavel_separacao': '38f14658c34641288c64f9335e572fba',
            'assinatura_responsavel': 'ff8547ea42b34836973f7056a8e98c04',
            'necessita_compra': 'c6c21ebeaf8a490daf61fe92532e0152'
        }

        # IDs para o subformulário de materiais
        self.question_id_subform_materiais = None  # Adicionar ID real do subform de materiais
        self.sub_question_mapping_materiais = {
            'codigo_material': None,  # ID para o código/descrição do material (ex: ADAPTADOR PVC 1/2)
            'unidade': None,  # ID para unidade (ex: Unid.)
            'quantidade': None,  # ID para quantidade solicitada
            'valor_unitario': None,  # ID para valor unitário (pode usar o valor_compra como referência)
            'valor_total': None,  # ID para valor total (quantidade * valor_unitario)
            'observacoes': None,  # ID para observações
            # Adicionar outros campos conforme necessário no formulário de separação
        }

    def _send_request(self, payload: Dict, batch_num: int) -> bool:
        """Envia requisição para a API"""
        try:
            response = requests.post(
                f"{self.base_url}/subchecklists",
                headers=self.headers,
                json=payload,
                timeout=90
            )

            if response.status_code not in [200, 201]:
                print(f"❌ ERRO no lote {batch_num}: Status {response.status_code}")
                print(f"Resposta: {response.text}")
                return False
            else:
                print(f"✅ Lote {batch_num} enviado com sucesso.")
                return True

        except requests.exceptions.RequestException as e:
            print(f"❌ ERRO DE CONEXÃO no lote {batch_num}: {e}")
            return False

    def criar_formulario_separacao(self, identificacao: Dict[str, str],
                                   assignee_id: str = None,
                                   creator_id: str = None) -> Optional[str]:
        """Cria o formulário principal de separação de materiais"""
        checklist_data = {
            "checklist": {
                "template_id": self.template_id_separacao,
                "execution_company_id": self.execution_company_id,
                "assignee_id": assignee_id,
                "creator_id": creator_id,
                "status_info": {
                    "new_execution_status": "pending"
                },
                "questions": []
            }
        }

        # Adiciona campos de identificação
        for campo, question_id in self.identification_questions.items():
            valor = identificacao.get(campo)
            if valor and question_id:
                checklist_data["checklist"]["questions"].append({
                    "id": question_id,
                    "sub_questions": [{"id": "1", "value": valor}]
                })

        print(f"📝 Criando formulário de separação de materiais...")

        try:
            response = requests.post(
                f"{self.base_url}/checklists",
                headers=self.headers,
                json=checklist_data
            )

            if response.status_code not in [200, 201]:
                print(f"❌ Erro ao criar formulário: {response.status_code}")
                print(f"Resposta: {response.text}")
                return None
            else:
                checklist_id = response.json()["_id"]["$oid"]
                print(f"✅ Formulário criado com ID: {checklist_id}")
                return checklist_id

        except Exception as e:
            print(f"❌ Erro ao criar formulário: {e}")
            return None

    def popular_materiais_no_formulario(self, form_id: str, materiais: List[Dict]):
        """Popula o formulário com os materiais em lotes"""
        if not materiais:
            print("ℹ️ Nenhum material para adicionar ao formulário.")
            return

        if not self.question_id_subform_materiais:
            print("❌ ID do subformulário de materiais não configurado.")
            return

        print(f"📦 Preparando para popular formulário ID: {form_id} com {len(materiais)} materiais...")

        # Prepara os subchecklists
        sub_checklists_para_adicionar = []

        for material in materiais:
            sub_checklist_questions = []

            # Mapeia os campos do material para as questões do subformulário
            # Usa o código_material como descrição principal
            if 'codigo_material' in material and self.sub_question_mapping_materiais.get('codigo_material'):
                sub_checklist_questions.append({
                    "question_id": self.sub_question_mapping_materiais['codigo_material'],
                    "value": str(material.get('codigo_material', ""))
                })

            # Adiciona unidade
            if 'unidade' in material and self.sub_question_mapping_materiais.get('unidade'):
                sub_checklist_questions.append({
                    "question_id": self.sub_question_mapping_materiais['unidade'],
                    "value": str(material.get('unidade', ""))
                })

            # Adiciona quantidade (se existir no formulário de separação)
            if self.sub_question_mapping_materiais.get('quantidade'):
                quantidade = material.get('quantidade', '1')  # Default 1 se não especificado
                sub_checklist_questions.append({
                    "question_id": self.sub_question_mapping_materiais['quantidade'],
                    "value": str(quantidade)
                })

            # Adiciona valor unitário (usando valor_compra do cadastro)
            if 'valor_compra' in material and self.sub_question_mapping_materiais.get('valor_unitario'):
                sub_checklist_questions.append({
                    "question_id": self.sub_question_mapping_materiais['valor_unitario'],
                    "value": str(material.get('valor_compra', ""))
                })

            # Calcula e adiciona valor total se necessário
            if self.sub_question_mapping_materiais.get('valor_total'):
                try:
                    quantidade = float(material.get('quantidade', 1))
                    valor_unit = float(material.get('valor_compra', 0))
                    valor_total = quantidade * valor_unit
                    sub_checklist_questions.append({
                        "question_id": self.sub_question_mapping_materiais['valor_total'],
                        "value": f"{valor_total:.2f}"
                    })
                except (ValueError, TypeError):
                    pass

            if sub_checklist_questions:
                sub_checklists_para_adicionar.append({
                    "id": self.question_id_subform_materiais,
                    "sub_checklist_questions": sub_checklist_questions
                })

        if not sub_checklists_para_adicionar:
            print("⚠️ Nenhum subchecklist foi preparado.")
            return

        # Envia em lotes
        batch_size = 50  # Tamanho menor para materiais que podem ter mais campos
        payloads = [
            {
                "checklist_id": form_id,
                "sub_checklists": sub_checklists_para_adicionar[i:i + batch_size]
            }
            for i in range(0, len(sub_checklists_para_adicionar), batch_size)
        ]

        total_lotes = len(payloads)
        print(f"📤 Total de {len(sub_checklists_para_adicionar)} materiais a serem enviados em {total_lotes} lotes.")

        success_count = 0
        for i, payload in enumerate(payloads):
            batch_num = i + 1
            print(f"➡️ Enviando lote {batch_num}/{total_lotes}...")

            success = self._send_request(payload, batch_num)

            if success:
                success_count += 1
            else:
                print(f"🛑 Envio interrompido devido a erro no lote {batch_num}.")
                break

            # Pequena pausa entre lotes para não sobrecarregar a API
            if batch_num < total_lotes:
                time.sleep(0.5)

        if success_count == total_lotes:
            print("🎉 Formulário populado com sucesso! Todos os lotes foram enviados.")
        else:
            print(f"⚠️ Processo concluído com falhas. {success_count} de {total_lotes} lotes enviados.")

    def criar_separacao_completa(self, identificacao: Dict[str, str],
                                 materiais: List[Dict],
                                 assignee_id: str = None,
                                 creator_id: str = None) -> Optional[str]:
        """Cria o formulário de separação e popula com materiais"""
        # Cria o formulário principal
        form_id = self.criar_formulario_separacao(
            identificacao=identificacao,
            assignee_id=assignee_id,
            creator_id=creator_id
        )

        if not form_id:
            return None

        if not materiais:
            print("ℹ️ Formulário criado sem materiais.")
            return form_id

        # Aguarda um momento antes de adicionar os materiais
        print("⏳ Aguardando 2 segundos antes de adicionar materiais...")
        time.sleep(2)

        # Popula com os materiais
        self.popular_materiais_no_formulario(form_id, materiais)

        return form_id

    def atualizar_mapeamento_campos(self, template_data: dict):
        """
        Método auxiliar para atualizar o mapeamento de campos baseado
        na estrutura real do template. Deve ser chamado após análise
        do template real.
        """
        print("🔍 Analisando estrutura do template para mapeamento de campos...")

        # Aqui você pode implementar a lógica para extrair automaticamente
        # os IDs das questões do template
        # Por enquanto, deixamos como placeholder para ser preenchido manualmente

        print("ℹ️ Mapeamento de campos deve ser atualizado manualmente com os IDs reais.")


if __name__ == "__main__":
    # Teste do módulo
    creator = SeparacaoMaterialCreator()

    # Dados de teste
    identificacao_teste = {
        'solicitante': 'João Silva',
        'data_solicitacao': '2025-01-29',
        'obra': 'Obra ABC',
        'responsavel': 'Maria Santos'
    }

    materiais_teste = [
        {
            'codigo': 'MAT001',
            'descricao': 'Cabo elétrico 2.5mm',
            'quantidade': '100',
            'unidade': 'metros',
            'observacoes': 'Para instalação elétrica'
        },
        {
            'codigo': 'MAT002',
            'descricao': 'Tomada 20A',
            'quantidade': '50',
            'unidade': 'unidades',
            'observacoes': 'Padrão brasileiro'
        }
    ]

    print("⚠️ ATENÇÃO: Este é apenas um teste de estrutura.")
    print("Os IDs de mapeamento precisam ser configurados com os valores reais do template.")