# backend/tools/external_api.py
import requests

def get_crypto_price(crypto_id: str, vs_currency: str = "usd") -> dict:
    """
    Consulta el precio en tiempo real de una criptomoneda usando la API pública de CoinGecko.
    """
    try:
        # Asegurar formato limpio en minúsculas requerido por la API
        coin = crypto_id.strip().lower()
        fiat = vs_currency.strip().lower()
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={fiat}"
        headers = {"accept": "application/json"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if coin in data and fiat in data[coin]:
                price = data[coin][fiat]
                return {
                    "status": "success",
                    "crypto_id": coin,
                    "currency": fiat,
                    "current_price": price
                }
            else:
                return {
                    "status": "error", 
                    "message": f"No se encontraron datos para la moneda '{coin}' en la divisa '{fiat}'."
                }
        else:
            return {
                "status": "error", 
                "message": f"Error de API CoinGecko. Código de estado: {response.status_code}"
            }
            
    except Exception as e:
        return {"status": "error", "message": f"Fallo de conexión externa: {str(e)}"}