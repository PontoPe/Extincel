import uvicorn
from pyngrok import ngrok, conf
import WHe
import os
import sys


def configurar_ambiente():
    """Configura variáveis de ambiente e validações iniciais"""
    # Configurações padrão
    config = {
        'NGROK_DOMAIN': os.environ.get('NGROK_DOMAIN', 'surely-excited-oyster.ngrok-free.app'),
        'NGROK_AUTH_TOKEN': os.environ.get('NGROK_AUTH_TOKEN', '2lcZIyet7S75iAIYeSHfnxl3Lxx_5RPfmweQ8XFUAuDRHi2ef'),
        'PORT': int(os.environ.get('PORT', 8000)),
        'HOST': os.environ.get('HOST', '0.0.0.0'),
        'RELOAD': os.environ.get('RELOAD', 'false').lower() == 'true'
    }

    print("🔧 Configurações do ambiente:")
    print(f"   - Porta: {config['PORT']}")
    print(f"   - Host: {config['HOST']}")
    print(f"   - Domínio Ngrok: {config['NGROK_DOMAIN']}")
    print(f"   - Modo Reload: {config['RELOAD']}")

    return config


def configurar_ngrok(config: dict) -> bool:
    """Configura o túnel ngrok"""
    if not config['NGROK_AUTH_TOKEN']:
        print("⚠️ Token do Ngrok não configurado. O túnel público não será criado.")
        return False

    conf.get_default().auth_token = config['NGROK_AUTH_TOKEN']

    try:
        # Tenta conectar com o domínio fixo
        ngrok.connect(addr=config['PORT'], proto="http", domain=config['NGROK_DOMAIN'])
        print(f"✅ Ngrok conectado em: https://{config['NGROK_DOMAIN']}")
        print(f"   Webhook URL: https://{config['NGROK_DOMAIN']}/webhook")
        return True

    except Exception as e:
        print(f"⚠️ Não foi possível conectar ao domínio ngrok fixo: {e}")

        try:
            # Fallback: tenta conectar sem domínio
            http_tunnel = ngrok.connect(addr=config['PORT'], proto="http")
            print(f"✅ Ngrok conectado em: {http_tunnel.public_url}")
            print(f"   Webhook URL: {http_tunnel.public_url}/webhook")
            return True

        except Exception as tunnel_e:
            print(f"❌ Falha crítica ao conectar o ngrok: {tunnel_e}")
            return False


def iniciar_servidor():
    """Configura e inicia o servidor completo"""
    print("\n🚀 INICIANDO SERVIDOR DE PROCESSAMENTO DE MATERIAIS 🚀\n")

    # Configura o ambiente
    config = configurar_ambiente()

    # Configura o ngrok
    ngrok_configurado = configurar_ngrok(config)

    if not ngrok_configurado:
        print("\n⚠️ AVISO: Servidor rodando apenas localmente (sem acesso externo)")

    # Cria a aplicação FastAPI
    app = WHe.criar_app_fastapi()

    print(f"\n📡 Servidor pronto em http://localhost:{config['PORT']}")
    print("📌 Endpoints disponíveis:")
    print(f"   - GET  http://localhost:{config['PORT']}/         (Status)")
    print(f"   - GET  http://localhost:{config['PORT']}/health   (Health Check)")
    print(f"   - POST http://localhost:{config['PORT']}/webhook  (Webhook)")

    print("\n👀 Monitorando webhooks... (Ctrl+C para parar)\n")

    try:
        # Inicia o servidor Uvicorn
        uvicorn.run(
            app,
            host=config['HOST'],
            port=config['PORT'],
            reload=config['RELOAD'],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n⏹️ Servidor interrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        sys.exit(1)
    finally:
        # Fecha conexões ngrok ao finalizar
        try:
            ngrok.disconnect()
            print("🔌 Conexões ngrok fechadas.")
        except:
            pass


if __name__ == "__main__":
    iniciar_servidor()