# backend/tools/financial_tools.py

def calculate_interest(principal: float, rate: float, years: int) -> dict:
    """
    Calcula el interés compuesto de una inversión.
    """
    try:
        r = float(rate) / 100
        p = float(principal)
        t = int(years)
        
        amount_final = p * ((1 + r) ** t)
        interest_earned = amount_final - p
        
        return {
            "status": "success",
            "principal": p,
            "rate_annual_percentage": rate,
            "years": t,
            "amount_final": round(amount_final, 2),
            "interest_earned": round(interest_earned, 2)
        }
    except Exception as e:
        return {"status": "error", "message": f"Error en el cálculo matemático: {str(e)}"}


def get_usd_rate() -> dict:
    """
    Retorna el tipo de cambio actual de referencia para USD a COP.
    """
    tasa_referencia_cop = 4150.00 
    
    return {
        "status": "success",
        "base_currency": "USD",
        "target_currency": "COP",
        "rate": tasa_referencia_cop,
        "note": "Tasa de cambio de referencia para operaciones de FinBot en Colombia y EE.UU."
    }