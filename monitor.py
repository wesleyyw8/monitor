import math
import os
import requests
import yfinance as yf

def carregar_env_local(caminho=".env"):
    if not os.path.exists(caminho):
        return

    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue

            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))

carregar_env_local()

# PARAMÊTROS DO SEU CANAL
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_ID")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

# BANCO DE DADOS
# Para ações: adicionado o "teto_max" para travar distorções das fórmulas
CARTEIRA_DADOS = {
    # Ações da sua carteira e radar
    "BBAS3.SA": {"tipo": "acao", "lpa": 2.47, "vpa": 33.26, "div12m": 1.75, "teto_max": 19.60},
    "CMIG4.SA": {"tipo": "acao", "lpa": 1.63, "vpa": 10.12, "div12m": 0.98, "teto_max": 10.60},
    "VALE3.SA": {"tipo": "acao", "lpa": 3.51, "vpa": 43.07, "div12m": 5.48, "teto_max": 77.00},
    "PETR4.SA": {"tipo": "acao", "lpa": 5.80, "vpa": 31.20, "div12m": 4.12, "teto_max": 35.50},
    "BBSE3.SA": {"tipo": "acao", "lpa": 4.73, "vpa": 6.51, "div12m": 4.49, "teto_max": 35.00},
    "DIRR3.SA": {"tipo": "acao", "lpa": 1.15, "vpa": 11.29, "div12m": 1.12, "teto_max": 13.70},
    "WIZC3.SA": {"tipo": "acao", "lpa": 0.73, "vpa": 6.52, "div12m": 0.69, "teto_max": 9.00},
    "ITSA4.SA": {"tipo": "acao", "lpa": 1.34, "vpa": 9.20, "div12m": 0.61, "teto_max": 11.10},
    "SAPR4.SA": {"tipo": "acao", "lpa": 0.81, "vpa": 8.40, "div12m": 0.57, "teto_max": 5.10},
    "EGIE3.SA": {"tipo": "acao", "lpa": 2.26, "vpa": 11.98, "div12m": 1.47, "teto_max": 33.55},
    "TAEE11.SA": {"tipo": "acao", "lpa": 2.85, "vpa": 21.10, "div12m": 2.10, "teto_max": 35.00},
    "CPLE3.SA": {"tipo": "acao", "lpa": 0.95, "vpa": 11.40, "div12m": 0.65, "teto_max": 14.00},
    "VIVT3.SA": {"tipo": "acao", "lpa": 3.10, "vpa": 41.50, "div12m": 2.30, "teto_max": 31.50},
    "TRPL4.SA": {"tipo": "acao", "lpa": 2.45, "vpa": 24.10, "div12m": 1.60, "teto_max": 23.50},
    "CURY3.SA": {"tipo": "acao", "lpa": 2.10, "vpa": 12.20, "div12m": 1.85, "teto_max": 32.50},

    # Seus FIIs (Mantidos com teto fixo patrimonial)
    "GARE11.SA": {"tipo": "fii", "teto_fixo": 8.10},
    "MXRF11.SA": {"tipo": "fii", "teto_fixo": 9.70},
    "GGRC11.SA": {"tipo": "fii", "teto_fixo": 9.85},
}

def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Erro: configure TELEGRAM_TOKEN e TELEGRAM_CHAT_ID nas variáveis de ambiente.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Erro ao enviar Telegram: {response.text}")
    except Exception as e:
        print(f"Erro de conexão: {e}")

def monitorar_mercado():
    print("Iniciando varredura inteligente de mercado com travas...")
    alertas_disparados = []
    
    tickers_symbols = list(CARTEIRA_DADOS.keys())
    dados_mercado = yf.download(tickers_symbols, period="1d", interval="1m", progress=False)
    
    for ticker, info in CARTEIRA_DADOS.items():
        try:
            preco_atual = dados_mercado['Close'][ticker].iloc[-1]
            preco_atual = round(float(preco_atual), 2)
            
            # Lógica de cálculo do Preço-Teto
            if info["tipo"] == "acao":
                # 1. Fórmula de Graham
                if info["lpa"] > 0 and info["vpa"] > 0:
                    graham = math.sqrt(22.5 * info["lpa"] * info["vpa"])
                else:
                    graham = 0
                
                # 2. Método de Bazin
                bazin = info["div12m"] / 0.06
                
                # Pega o menor valor calculado pelas fórmulas
                teto_calculado = min(graham, bazin)
                
                # TRAVA DE SEGURANÇA: Limita o preço final ao "teto_max" definido por você
                preco_teto = round(min(teto_calculado, info["teto_max"]), 2)
                
                # Define a string de exibição do método correspondente
                if preco_teto == info["teto_max"]:
                    metodo_usado = "Trava Manual"
                else:
                    metodo_usado = "Graham" if graham < bazin else "Bazin"
            else:
                # Se for FII, usa direto o teto patrimonial fixo
                preco_teto = info["teto_fixo"]
                metodo_usado = "P/VP FII"

            print(f"{ticker}: Atual R$ {preco_atual} | Teto Final R$ {preco_teto} ({metodo_usado})")
            
            if preco_atual <= preco_teto:
                ticker_limpo = ticker.replace(".SA", "")
                alertas_disparados.append(
                    f"🚨 *{ticker_limpo}* entrou em ponto de compra!\n"
                    f"Preço Atual: R$ {preco_atual}\n"
                    f"Seu Preço Teto: R$ {preco_teto} ({metodo_usado})\n"
                    f"Link: [C6 Bank](https://www.c6bank.com.br/)"
                )
        except Exception as e:
            print(f"Erro ao processar {ticker}: {e}")
            
    if alertas_disparados:
        mensagem_final = "🔥 *RADAR DE INVESTIMENTOS AUTOMÁTICO* 🔥\n\n" + "\n---\n".join(alertas_disparados)
        enviar_mensagem_telegram(mensagem_final)
        print("Alertas enviados para o Telegram.")
    else:
        print("Varredura concluída. Nenhum ativo abaixo do teto das fórmulas.")

if __name__ == "__main__":
    monitorar_mercado()