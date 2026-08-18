import contextlib
import io
import math
import os
import requests
import pandas as pd
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

# PARÂMETROS DO SEU CANAL
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_ID")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

# BANCO DE DADOS DINÂMICO (LPA, VPA e Dividendos foram removidos para automação total)
CARTEIRA_DADOS = {
    # Ações da sua carteira e radar
    "BBAS3.SA": {"tipo": "acao", "teto_max": 19.60},
    "BBDC4.SA": {"tipo": "acao", "teto_max": 14.50},  
    "BBSE3.SA": {"tipo": "acao", "teto_max": 35.00},
    "CMIG4.SA": {"tipo": "acao", "teto_max": 10.60},
    "CPLE3.SA": {"tipo": "acao", "teto_max": 14.00},
    "CURY3.SA": {"tipo": "acao", "teto_max": 32.50},
    "DIRR3.SA": {"tipo": "acao", "teto_max": 13.70},
    "EGIE3.SA": {"tipo": "acao", "teto_max": 33.55},
    "ITSA4.SA": {"tipo": "acao", "teto_max": 11.10},
    "PETR4.SA": {"tipo": "acao", "teto_max": 35.50},
    "PRIO3.SA": {"tipo": "acao", "teto_max": 41.60},
    "SAPR4.SA": {"tipo": "acao", "teto_max": 5.10},
    "TAEE11.SA": {"tipo": "acao", "teto_max": 35.00},
    "TRPL4.SA": {"tipo": "acao", "teto_max": 23.50},
    "VALE3.SA": {"tipo": "acao", "teto_max": 77.00},
    "VIVT3.SA": {"tipo": "acao", "teto_max": 31.50},
    "WIZC3.SA": {"tipo": "acao", "teto_max": 9.00},
    "AXIA3.SA": {"tipo": "acao", "teto_max": 99.00},
    "KLBN11.SA": {"tipo": "acao", "teto_max": 22.50},
    "CSMG3.SA": {"tipo": "acao", "teto_max": 23.50},
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

def buscar_dados_mercado(tickers):
    tentativas = [
        {"period": "1d", "interval": "5m"},
        {"period": "5d", "interval": "1d"},
        {"period": "1mo", "interval": "1d"},
    ]

    for tentativa in tentativas:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            dados = yf.download(tickers, progress=False, **tentativa)
        if not dados.empty:
            return dados
    return None

def obter_ultimo_preco(dados_mercado, ticker):
    if dados_mercado is None or dados_mercado.empty:
        return None

    try:
        fechamento = dados_mercado["Close"][ticker]
    except KeyError:
        try:
            fechamento = dados_mercado["Close"]
        except KeyError:
            return None

    fechamento = fechamento.dropna()
    if fechamento.empty:
        return None

    return round(float(fechamento.iloc[-1]), 2)

def obter_dados_fundamentais(ticker):
    """
    Busca LPA (trailingEps), VPA (bookValue) e a média anual de dividendos de 3 anos
    diretamente da API do Yahoo Finance.
    """
    lpa, vpa, media_div = 0.0, 0.0, 0.0
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ativo = yf.Ticker(ticker)
            info = ativo.info
            
            # Puxa os dados contábeis fundamentais básicos
            lpa = float(info.get("trailingEps", 0.0))
            vpa = float(info.get("bookValue", 0.0))
            
            # Puxa e calcula a média de dividendos dos últimos 3 anos (1095 dias)
            historico_dividendos = ativo.dividends
            if not historico_dividendos.empty:
                limite_data = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=1095)
                dividendos_3anos = historico_dividendos[historico_dividendos.index >= limite_data]
                media_div = float(dividendos_3anos.sum() / 3)
                
    except Exception as e:
        print(f"Erro ao buscar fundamentos de {ticker}: {e}")
        
    return lpa, vpa, round(media_div, 4)

def monitorar_mercado():
    print("Iniciando varredura 100% dinâmica (Preços, LPA, VPA e Dividendos integrados)...")
    alertas_disparados = []
    
    tickers_symbols = list(CARTEIRA_DADOS.keys())
    dados_mercado = buscar_dados_mercado(tickers_symbols)
    
    for ticker, info in CARTEIRA_DADOS.items():
        try:
            preco_atual = obter_ultimo_preco(dados_mercado, ticker)
            
            # Tratamentos e reconexão individual se o preço falhar
            if preco_atual is None:
                dados_individuais = buscar_dados_mercado([ticker])
                preco_atual = obter_ultimo_preco(dados_individuais, ticker)
                
            if preco_atual is None:
                ticker_puro = ticker.replace(".SA", "")
                dados_individuais = buscar_dados_mercado([ticker_puro])
                preco_atual = obter_ultimo_preco(dados_individuais, ticker_puro)
                
            if preco_atual is None:
                print(f"{ticker}: sem preço disponível no Yahoo Finance.")
                continue
            
            # Lógica para Ações
            if info["tipo"] == "acao":
                if info.get("ignorar_formulas", False):
                    preco_teto = info["teto_max"]
                    metodo_usado = "Trava Manual"
                else:
                    # Busca fundamentos dinâmicos em tempo real
                    lpa, vpa, div_medio_anual = obter_dados_fundamentais(ticker)
                    
                    # Calcula Graham Dinâmico
                    graham = math.sqrt(22.5 * lpa * vpa) if lpa > 0 and vpa > 0 else 0
                    
                    # Calcula Bazin Dinâmico
                    bazin = div_medio_anual / 0.06
                    
                    teto_calculado = min(graham, bazin)
                    preco_teto = round(min(teto_calculado, info["teto_max"]), 2)
                    
                    # Identificação dinâmica do método gerador do teto
                    if preco_teto == info["teto_max"] and preco_atual <= info["teto_max"] and preco_atual > teto_calculado:
                        metodo_usado = f"Trava Manual (LPA: {lpa:.2f} | VPA: {vpa:.2f})"
                    else:
                        passou_graham = preco_atual <= graham
                        passou_bazin = preco_atual <= bazin
                        
                        detalhes = f"LPA: {lpa:.2f} | VPA: {vpa:.2f} | DivMédio: R$ {div_medio_anual:.2f}"
                        if passou_graham and passou_bazin:
                            metodo_usado = f"Graham e Bazin ({detalhes})"
                        elif passou_graham:
                            metodo_usado = f"Graham ({detalhes})"
                        elif passou_bazin:
                            metodo_usado = f"Bazin ({detalhes})"
                        else:
                            metodo_usado = f"Nenhum (Preço Esticado | {detalhes})"
            else:
                # Lógica para FIIs
                preco_teto = info["teto_fii"] if "teto_fii" in info else info.get("teto_fixo", 0)
                metodo_usado = "P/VP FII"

            print(f"{ticker}: Atual R$ {preco_atual} | Teto Final R$ {preco_teto} ({metodo_usado})")
            
            # Validação de gatilho
            if preco_atual <= preco_teto:
                ticker_limpo = ticker.replace(".SA", "")
                alertas_disparados.append(
                    f"🚨 *{ticker_limpo}* entrou em ponto de compra!\n"
                    f"Preço Atual: R$ {preco_atual}\n"
                    f"Seu Preço Teto: R$ {preco_teto}\n"
                    f"Método/Métricas: {metodo_usado}\n"
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