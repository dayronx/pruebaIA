def ohms_law(voltage=None, current=None, resistance=None):
    """
    Solves Ohm's Law for the missing variable.
    V = I * R, I = V / R, R = V / I
    """
    try:
        if voltage is None:
            return {"current": current, "resistance": resistance, "voltage": current * resistance}
        if current is None:
            return {"voltage": voltage, "resistance": resistance, "current": voltage / resistance}
        if resistance is None:
            return {"voltage": voltage, "current": current, "resistance": voltage / current}
        return {"voltage": voltage, "current": current, "resistance": resistance}
    except Exception as e:
        return {"status": "error", "message": f"Ohm's Law calculation error: {str(e)}"}

def watts_law(voltage=None, current=None, power=None):
    """
    Solves Watt's Law for the missing variable.
    P = V * I
    """
    try:
        if power is None:
            return {"voltage": voltage, "current": current, "power": voltage * current}
        if voltage is None:
            return {"power": power, "current": current, "voltage": power / current}
        if current is None:
            return {"power": power, "voltage": voltage, "current": power / voltage}
        return {"voltage": voltage, "current": current, "power": power}
    except Exception as e:
        return {"status": "error", "message": f"Watt's Law calculation error: {str(e)}"}

def unit_convert(value, from_unit, to_unit):
    """
    Converts between milli, micro, kilo, mega units (e.g., mA to A, kV to V).
    """
    units = {
        "micro": 1e-6, "u": 1e-6,
        "milli": 1e-3, "m": 1e-3,
        "kilo": 1e3, "k": 1e3,
        "mega": 1e6, "M": 1e6,
        "": 1.0
    }
    try:
        def parse_unit(unit):
            for key in units:
                if unit.lower().startswith(key):
                    return units[key], unit[len(key):]
            return 1.0, unit
        from_factor, base_from = parse_unit(from_unit)
        to_factor, base_to = parse_unit(to_unit)
        if base_from != base_to:
            return {"status": "error", "message": "Incompatible units."}
        base_value = float(value) * from_factor
        converted = base_value / to_factor
        return {"value": converted, "unit": to_unit}
    except Exception as e:
        return {"status": "error", "message": f"Unit conversion error: {str(e)}"}