import requests
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
import POST
import unicodedata

class FormulariosBuscador:
    def __init__(self, execution_company_id: str, arquivo_cache='cache_formularios.json'):
        self.url = "https://app.way-v.com/api/integration/checklists"
        self.token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb21wYW55X2lkIjoiNjYzZDMxYTFlOWRhYzNmNWY0ZDNjZjJlIiwiY3VycmVudF90aW1lIjoxNzQ4OTUzODcyNjgzLCJleHAiOjIwNjQ0ODY2NzJ9.j6zOrJMDKNcCcMMcO99SudriP7KqEDLMJDE2FBlQ6ok'
        self.params = {
            "execution_company_id": execution_company_id,
            "template_id": '67f6ae4d6ba4f07ba32a1ea8'
        }
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.arquivo_cache = arquivo_cache

    def carregar_e_salvar_formularios(self, forcar_nova_requisicao=True):
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
            print("🌐 Buscando formulários de cadastro de itens...")
            response = requests.get(self.url, headers=self.headers, params=self.params, timeout=30)
            response.raise_for_status()
            dados_formularios = response.json()
            if not isinstance(dados_formularios, list):
                return False
            with open(self.arquivo_cache, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": datetime.now().isoformat(), "dados": dados_formularios}, f, indent=2, ensure_ascii=False)
            print(f"💾 Dados de cadastro salvos no cache. Total: {len(dados_formularios)}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição: {e}")
            return False
        except Exception as e:
            print(f"❌ Erro inesperado ao carregar/salvar formulários: {e}")
            return False

    def buscar_por_clausulas_no_cache(self, clausulas_desejadas: List[str]) -> List[Dict]:
        if not os.path.exists(self.arquivo_cache):
            print(f"❌ Arquivo de cache '{self.arquivo_cache}' não encontrado.")
            return []
        try:
            with open(self.arquivo_cache, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            dados_formularios = cache_data.get('dados', [])
            clausulas_set = {str(c).strip() for c in clausulas_desejadas}
            formularios_filtrados = []
            
            for formulario in dados_formularios:
                if not clausulas_set: break
                for secao in formulario.get('sections', []):
                    if secao.get('title') == 'Identificação':
                        for questao in secao.get('questions', []):
                            if questao.get('title') == 'item/Cláusula':
                                valor = str(questao.get('sub_questions', [{}])[0].get('value', '')).strip()
                                if valor in clausulas_set:
                                    formularios_filtrados.append(formulario)
                                    clausulas_set.remove(valor)
                                    break
                        break
            
            print(f"📋 Itens encontrados no cache: {len(formularios_filtrados)}")
            return formularios_filtrados
            
        except Exception as e:
            print(f"❌ Erro ao buscar no cache: {e}")
            return []

    def _limpar_titulo(self, titulo_bruto: str) -> str:
        """Normaliza o título para ser usado como chave de dicionário."""
        if not titulo_bruto: return ""
        nfkd_form = unicodedata.normalize('NFKD', titulo_bruto.lower())
        texto_sem_acentos = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        return texto_sem_acentos.replace('/', '_').replace(' ', '_')

    def extrair_informacoes_formulario(self, formulario: dict) -> dict:
        """Extrai os campos da seção Identificação usando títulos normalizados."""
        info = {}
        for secao in formulario.get('sections', []):
            if secao.get('title') == 'Identificação':
                for questao in secao.get('questions', []):
                    titulo_limpo = self._limpar_titulo(questao.get('title'))
                    if titulo_limpo:
                        valor = questao.get('sub_questions', [{}])[0].get('value') if questao.get('sub_questions') else None
                        if titulo_limpo == 'item_clausula':
                           titulo_limpo = 'item'
                        info[titulo_limpo] = valor
        return info

def _buscar_clausulas(exec_id: str) -> List[str]:
    try:
        cc = POST.ChecklistCreator()
        url = f"{cc.base_url.rstrip('/')}/checklists"
        resp = requests.get(url, headers=cc.headers, params={
            "template_id": "67f6ad27bfce31f9c1926b57", # Template de Cadastro de Itens
            "execution_company_id": exec_id
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        claus = []
        for chk in data:
            for sec in chk.get("sections", []):
                for q in sec.get("questions", []):
                    if q.get("title", "").lower() == "item/cláusula":
                        for sub in q.get("sub_questions", []):
                            if sub.get("value"):
                                claus.append(str(sub["value"]).strip())
        claus_unicas = sorted(list(set(claus)))
        print(f"[FetchClauses] Capturadas {len(claus_unicas)} cláusulas de cadastro únicas.")
        return claus_unicas
    except requests.exceptions.RequestException as e:
        print(f"[FetchClauses] ❌ {e}")
        return []

if __name__ == "__main__":
    exec_id = "6800f0468065037501c538d2"  # Substitua pelo ID real
    buscador = FormulariosBuscador(execution_company_id=exec_id)
    if buscador.carregar_e_salvar_formularios():
        clausulas = _buscar_clausulas(exec_id)
        if clausulas:
            formularios = buscador.buscar_por_clausulas_no_cache(clausulas)
            for f in formularios:
                info = buscador.extrair_informacoes_formulario(f)
                print(f"Formulário ID: {f.get('_id', {}).get('$oid')}, Informações: {info}")
        else:
            print("Nenhuma cláusula encontrada.")
    else:
        print("Falha ao carregar/salvar formulários.")