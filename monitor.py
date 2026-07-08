import math
import os
import requests
import yfinance as yf

# PARAMÊTROS DO SEU CANAL
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_ID")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

# BANCO DE DADOS
# Para ações: passamos os dados fundamentais [LPA, VPA, Dividendos de 12 meses]
# Para FIIs: passamos apenas o preço-teto fixo direto
CARTEIRA_DADOS = {
    # Ações da sua carteira e radar
    "BBAS3.SA": {"tipo": "acao", "lpa": 2.47, "vpa": 33.26, "div12m": 1.75},
    "BBSE3.SA": {"tipo": "acao", "lpa": 4.73, "vpa": 6.51, "div12m": 4.49},
    "CMIG4.SA": {"tipo": "acao", "lpa": 1.63, "vpa": 10.12, "div12m": 0.98},
    "DIRR3.SA": {"tipo": "acao", "lpa": 1.15, "vpa": 11.29, "div12m": 1.12},
    "WIZC3.SA": {"tipo": "acao", "lpa": 0.73, "vpa": 6.52, "div12m": 0.69},
    "ITSA4.SA": {"tipo": "acao", "lpa": 1.34, "vpa": 9.20, "div12m": 0.61},
    "VALE3.SA": {"tipo": "acao", "lpa": 3.51, "vpa": 43.07, "div12m": 5.48},
    "SAPR4.SA": {"tipo": "acao", "lpa": 0.81, "vpa": 8.40, "div12m": 0.57},
    "EGIE3.SA": {"tipo": "acao", "lpa": 2.26, "vpa": 11.98, "div12m": 1.47},
    "PETR4.SA": {"tipo": "acao", "lpa": 5.80, "vpa": 31.20, "div12m": 4.12},
    "TAEE11.SA": {"tipo": "acao", "lpa": 2.85, "vpa": 21.10, "div12m": 2.10},
    "CPLE3.SA": {"tipo": "acao", "lpa": 0.95, "vpa": 11.40, "div12m": 0.65},
    "VIVT3.SA": {"tipo": "acao", "lpa": 3.10, "vpa": 41.50, "div12m": 2.30},
    "TRPL4.SA": {"tipo": "acao", "lpa": 2.45, "vpa": 24.10, "div12m": 1.60},
    "CURY3.SA": {"tipo": "acao", "lpa": 2.10, "vpa": 12.20, "div12m": 1.85},

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
    print("Iniciando varredura inteligente de mercado...")
    alertas_disparados = []
    
    tickers_symbols = list(CARTEIRA_DADOS.keys())
    dados_mercado = yf.download(tickers_symbols, period="1d", interval="1m", progress=False)
    
    for ticker, info in CARTEIRA_DADOS.items():
        try:
            preco_atual = dados_mercado['Close'][ticker].iloc[-1]
            preco_atual = round(float(preco_atual), 2)
            
            # Lógica de cálculo do Preço-Teto
            if info["tipo"] == "acao":
                # 1. Fórmula de Graham (evita erros caso LPA/VPA sejam negativos em crises)
                if info["lpa"] > 0 and info["vpa"] > 0:
                    graham = math.sqrt(22.5 * info["lpa"] * info["vpa"])
                else:
                    graham = 0
                
                # 2. Método de Bazin (mínimo de 6% de dividendo)
                bazin = info["div12m"] / 0.06
                
                # Define o teto usando o MENOR valor entre as duas fórmulas
                preco_teto = round(min(graham, bazin), 2)
                metodo_usado = "Graham" if graham < bazin else "Bazin"
            else:
                # Se for FII, usa direto o teto patrimonial fixo
                preco_teto = info["teto_fixo"]
                metodo_usado = "P/VP FII"

            print(f"{ticker}: Atual R$ {preco_atual} | Teto Calculado R$ {preco_teto} ({metodo_usado})")
            
            if preco_atual <= preco_teto:
                ticker_limpo = ticker.replace(".SA", "")
                alertas_disparados.append(
                    f"🚨 *{ticker_limpo}* entrou em ponto de compra!\n"
                    f"Preço Atual: R$ {preco_atual}\n"
                    f"Seu Preço Teto: R$ {preco_teto} (Limitado por {metodo_usado})\n"
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
