import uvicorn
from pyngrok import ngrok, conf
import webhook
import os

def iniciar_servidor():
    """Configura o túnel ngrok e inicia o servidor uvicorn."""
    
    # ------------- Configuração do Ngrok ------------
    NGROK_DOMAIN = "surely-excited-oyster.ngrok-free.app"
    # Recomenda-se usar variáveis de ambiente para o token
    NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN")

    if NGROK_AUTH_TOKEN:
        conf.get_default().auth_token = NGROK_AUTH_TOKEN
        try:
            # Tenta conectar com o domínio fixo primeiro
            ngrok.connect(addr=8000, proto="http", domain=NGROK_DOMAIN)
            print(f"✅ Ngrok conectado em: https://{NGROK_DOMAIN}")
        except Exception as e:
            print(f"⚠️ Não foi possível conectar ao domínio ngrok fixo: {e}")
            try:
                # Se falhar, tenta conectar sem domínio como alternativa
                http_tunnel = ngrok.connect(addr=8000, proto="http")
                print(f"✅ Ngrok conectado em: {http_tunnel.public_url}")
            except Exception as tunnel_e:
                print(f"❌ Falha crítica ao conectar o ngrok: {tunnel_e}")
    else:
        print("ℹ️ Token do Ngrok não encontrado. O túnel público não será criado.")

    # ---------- Inicialização do FastAPI app ---------------
    app = webhook.criar_app_fastapi()
    print("🚀 Servidor pronto em http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    iniciar_servidor()
