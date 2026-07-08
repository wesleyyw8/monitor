import requests
import yfinance as yf

TELEGRAM_TOKEN = "8746372216:AAEWxeJnWj6sHrbMyS6OoYoJMT8PXQjGgXo"
CHAT_ID = "6368924019"

CARTEIRA = {
    "BBAS3.SA": 19.60,
    "CMIG4.SA": 10.60,
    "SAPR4.SA": 9.50,
    "BBSE3.SA": 45.00,
    "DIRR3.SA": 14.50,
    "WIZC3.SA": 9.00,
    "ITSA4.SA": 11.10,
    "GARE11.SA": 8.10, 
    "MXRF11.SA": 9.70,
    "GGRC11.SA": 9.85, 
    "VALE3.SA": 76.00,
    "EGIE3.SA": 24.67,
    "PETR4.SA": 35.50,   
    "TAEE11.SA": 35.00,
    "CPLE3.SA": 14.00, 
    "VIVT3.SA": 31.50, 
    "TRPL4.SA": 23.50, 
    "CURY3.SA": 32.50
}

def enviar_mensagem_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Erro ao enviar Telegram: {response.text}")
    except Exception as e:
        print(f"Erro de conexão: {e}")

def monitorar_mercado():
    print("Iniciando varredura de mercado...")
    alertas_disparados = []
    
    tickers_symbols = list(CARTEIRA.keys())
    dados_mercado = yf.download(tickers_symbols, period="1d", interval="1m", progress=False)
    
    for ticker, preco_teto in CARTEIRA.items():
        try:
            preco_atual = dados_mercado['Close'][ticker].iloc[-1]
            preco_atual = round(float(preco_atual), 2)
            
            print(f"{ticker}: Atual R$ {preco_atual} | Alerta se for <= R$ {preco_teto}")
            
            if preco_atual <= preco_teto:
                ticker_limpo = ticker.replace(".SA", "")
                alertas_disparados.append(
                    f"🚨 *{ticker_limpo}* entrou em ponto de compra!\n"
                    f"Preço Atual: R$ {preco_atual}\n"
                    f"Seu Preço Teto: R$ {preco_teto}\n"
                    f"Link: [C6 Bank](https://www.c6bank.com.br/)"
                )
        except Exception as e:
            print(f"Erro ao processar {ticker}: {e}")
            
    if alertas_disparados:
        mensagem_final = "🔥 *RADAR DE INVESTIMENTOS* 🔥\n\n" + "\n---\n".join(alertas_disparados)
        enviar_mensagem_telegram(mensagem_final)
        print("Alertas enviados para o Telegram.")
    else:
        print("Varredura concluída. Nenhum ativo no preço.")

if __name__ == "__main__":
    monitorar_mercado()
