import requests
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import unicodedata


class MaterialBuscador:
    def __init__(self, execution_company_id: str = "685d7c22ebc532b38cc602ce", arquivo_cache='cache_materiais.json'):
        self.url = "https://app.way-v.com/api/integration/checklists"
        self.token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb21wYW55X2lkIjoiNjYzZDMxYTFlOWRhYzNmNWY0ZDNjZjJlIiwiY3VycmVudF90aW1lIjoxNzQ4OTUzODcyNjgzLCJleHAiOjIwNjQ0ODY2NzJ9.j6zOrJMDKNcCcMMcO99SudriP7KqEDLMJDE2FBlQ6ok'
        self.execution_company_id = execution_company_id
        self.template_id_materiais = "68672e90de1e5a11771d2224"  # Template de cadastro de materiais
        self.params = {
            "execution_company_id": self.execution_company_id,
            "template_id": self.template_id_materiais
        }
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.arquivo_cache = arquivo_cache

    def carregar_e_salvar_materiais(self, forcar_nova_requisicao=True):
        """Carrega materiais da API e salva em cache"""
        if not forcar_nova_requisicao and os.path.exists(self.arquivo_cache):
            try:
                tempo_arquivo = datetime.fromtimestamp(os.path.getmtime(self.arquivo_cache))
                if datetime.now() - tempo_arquivo < timedelta(hours=1):
                    print(f"📋 Cache válido encontrado em '{self.arquivo_cache}'.")
                    return True
                else:
                    print(f"⏰ Cache expirado. Fazendo nova requisição...")
            except Exception as e:
                print(f"⚠️ Erro ao verificar cache: {e}. Fazendo nova requisição...")

        try:
            print("🌐 Buscando formulários de cadastro de materiais...")
            response = requests.get(self.url, headers=self.headers, params=self.params, timeout=30)
            response.raise_for_status()
            dados_materiais = response.json()

            if not isinstance(dados_materiais, list):
                return False

            with open(self.arquivo_cache, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "dados": dados_materiais
                }, f, indent=2, ensure_ascii=False)

            print(f"💾 Dados de materiais salvos no cache. Total: {len(dados_materiais)}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição: {e}")
            return False
        except Exception as e:
            print(f"❌ Erro inesperado ao carregar/salvar materiais: {e}")
            return False

    def buscar_materiais_por_subcategoria(self, subcategoria_servico: str) -> List[Dict]:
        """Busca materiais filtrados por subcategoria de serviço no cache"""
        if not os.path.exists(self.arquivo_cache):
            print(f"❌ Arquivo de cache '{self.arquivo_cache}' não encontrado.")
            return []

        try:
            with open(self.arquivo_cache, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            dados_materiais = cache_data.get('dados', [])
            materiais_filtrados = []

            for material in dados_materiais:
                # Busca a subcategoria de serviço no formulário
                subcategoria_encontrada = self._extrair_subcategoria_servico(material)
                if subcategoria_encontrada and subcategoria_encontrada.lower() == subcategoria_servico.lower():
                    materiais_filtrados.append(material)

            print(f"📦 Materiais encontrados com subcategoria '{subcategoria_servico}': {len(materiais_filtrados)}")
            return materiais_filtrados

        except Exception as e:
            print(f"❌ Erro ao buscar materiais no cache: {e}")
            return []

    def _extrair_subcategoria_servico(self, material: dict) -> Optional[str]:
        """Extrai a subcategoria de serviço de um material"""
        for secao in material.get('sections', []):
            for questao in secao.get('questions', []):
                # Busca pelo ID específico da subcategoria
                if questao.get('id') == 'f1e2e64f6eac4752b88435db97c81571':
                    sub_questions = questao.get('sub_questions', [])
                    if sub_questions:
                        return sub_questions[0].get('value')
        return None

    def _limpar_titulo(self, titulo_bruto: str) -> str:
        """Normaliza o título para ser usado como chave de dicionário"""
        if not titulo_bruto:
            return ""
        nfkd_form = unicodedata.normalize('NFKD', titulo_bruto.lower())
        texto_sem_acentos = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        return texto_sem_acentos.replace('/', '_').replace(' ', '_')

    def extrair_informacoes_material(self, material: dict) -> dict:
        """Extrai todas as informações relevantes de um material com os IDs específicos"""
        info = {
            'id': material.get('_id', {}).get('$oid'),
            'created_at': material.get('created_at'),
            'updated_at': material.get('updated_at')
        }

        # Mapeamento dos IDs reais para os campos
        id_mapping = {
            '1d5015491a8b404db59b95891cf00b22': 'codigo_material',  # ADAPTADOR PVC 1/2 - BRANCO
            '54f2e2ef14a14113a2dfd33cd87eb397': 'unidade',  # Unid.
            '783f2490e5104e3f9b291bd851980281': 'valor_compra',  # 0.49
            'f1e2e64f6eac4752b88435db97c81571': 'subcategoria_servico'  # Iluminação De Emergência
        }

        # Extrai informações de todas as seções
        for secao in material.get('sections', []):
            for questao in secao.get('questions', []):
                question_id = questao.get('id')

                # Se o ID está no nosso mapeamento
                if question_id in id_mapping:
                    campo = id_mapping[question_id]
                    sub_questions = questao.get('sub_questions', [])
                    if sub_questions:
                        valor = sub_questions[0].get('value')
                        info[campo] = valor

                # Também mantém o título da pergunta como chave adicional
                titulo_limpo = self._limpar_titulo(questao.get('title', ''))
                if titulo_limpo and questao.get('sub_questions'):
                    valor = questao.get('sub_questions', [{}])[0].get('value')
                    info[titulo_limpo] = valor

        return info


def buscar_materiais_com_subcategoria(subcategoria_servico: str, exec_id: str = "685d7c22ebc532b38cc602ce") -> List[
    Dict]:
    """Função auxiliar para buscar materiais de uma subcategoria específica"""
    try:
        buscador = MaterialBuscador(execution_company_id=exec_id)

        # Carrega e salva materiais em cache
        if not buscador.carregar_e_salvar_materiais():
            print("❌ Falha ao carregar materiais da API")
            return []

        # Busca materiais filtrados por subcategoria
        materiais = buscador.buscar_materiais_por_subcategoria(subcategoria_servico)

        # Extrai informações detalhadas de cada material
        materiais_detalhados = []
        for material in materiais:
            info = buscador.extrair_informacoes_material(material)
            materiais_detalhados.append(info)

        return materiais_detalhados

    except Exception as e:
        print(f"❌ Erro ao buscar materiais: {e}")
        return []


if __name__ == "__main__":
    # Teste do módulo
    exec_id = "685d7c22ebc532b38cc602ce"
    subcategoria_teste = "Elétrica"  # Ajustar conforme as subcategorias reais

    buscador = MaterialBuscador(execution_company_id=exec_id)
    if buscador.carregar_e_salvar_materiais():
        materiais = buscador.buscar_materiais_por_subcategoria(subcategoria_teste)

        for material in materiais[:3]:  # Mostra apenas os 3 primeiros
            info = buscador.extrair_informacoes_material(material)
            print(f"\nMaterial ID: {info.get('id')}")
            print(f"Informações: {json.dumps(info, indent=2, ensure_ascii=False)}")
    else:
        print("Falha ao carregar materiais.")