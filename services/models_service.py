"""
Scientific Models Service Module
Provides simplified engineering correlations for gas purification screening.

These functions are intentionally lightweight. They are suitable for
educational comparisons and stable dashboard simulations, not detailed
industrial equipment design.
"""

import math


DEFAULT_GAS_PROPERTIES = {
    "henry_constant": 450.0,
    "langmuir_qmax": 1.5,
    "langmuir_b": 0.08,
    "permeability": 15.0,
}


GAS_PROPERTIES = {
    # Lower Henry constants indicate stronger liquid-phase solubility.
    # Langmuir parameters are simplified adsorption placeholders.
    # Permeability values are relative screening values for membranes.
    "CO2": {
        "henry_constant": 29.0,
        "langmuir_qmax": 4.8,
        "langmuir_b": 0.80,
        "permeability": 100.0,
    },
    "H2S": {
        "henry_constant": 10.0,
        "langmuir_qmax": 5.6,
        "langmuir_b": 1.60,
        "permeability": 150.0,
    },
    "NH3": {
        "henry_constant": 6.0,
        "langmuir_qmax": 5.2,
        "langmuir_b": 1.10,
        "permeability": 65.0,
    },
    "H2": {
        "henry_constant": 1280.0,
        "langmuir_qmax": 0.40,
        "langmuir_b": 0.02,
        "permeability": 300.0,
    },
    "CO": {
        "henry_constant": 950.0,
        "langmuir_qmax": 1.10,
        "langmuir_b": 0.07,
        "permeability": 12.0,
    },
    "N2": {
        "henry_constant": 1600.0,
        "langmuir_qmax": 0.70,
        "langmuir_b": 0.04,
        "permeability": 6.0,
    },
    "CH4": {
        "henry_constant": 700.0,
        "langmuir_qmax": 1.90,
        "langmuir_b": 0.12,
        "permeability": 15.0,
    },
    "O2": {
        "henry_constant": 760.0,
        "langmuir_qmax": 0.80,
        "langmuir_b": 0.05,
        "permeability": 20.0,
    },
}


def clamp(value, min_value, max_value):
    """Clamp a numeric value to a physically meaningful range."""
    return max(min_value, min(max_value, value))


def safe_float(value, default=0.0):
    """Convert values safely to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_divide(numerator, denominator, default=0.0):
    """Divide safely and avoid divide-by-zero errors."""
    if abs(denominator) < 1e-12:
        return default
    return numerator / denominator


def normalize_gas_name(name):
    """Normalize gas names so lookup keys stay consistent."""
    return str(name or "").strip().upper()


def get_gas_properties(gas_name):
    """Return known gas properties, falling back to generic placeholders."""
    properties = DEFAULT_GAS_PROPERTIES.copy()
    properties.update(GAS_PROPERTIES.get(normalize_gas_name(gas_name), {}))
    return properties


def normalize_gas_mixture(gas_mixture):
    """
    Normalize a gas mixture into fractions that sum to 1.0.

    The input UI stores percentages, but users may not always total exactly 100.
    This function rescales the mixture so downstream engineering formulas remain
    numerically stable.
    """
    normalized = []
    total_percentage = 0.0

    for gas in gas_mixture or []:
        name = normalize_gas_name(gas.get("name"))
        percentage = max(0.0, safe_float(gas.get("percentage"), 0.0))
        if not name:
            continue
        normalized.append({"name": name, "percentage": percentage})
        total_percentage += percentage

    if total_percentage <= 0.0:
        return []

    for gas in normalized:
        gas["fraction"] = gas["percentage"] / total_percentage

    return normalized


def get_impurity_fraction(gas_mixture, impurity_name, default_fraction=0.05):
    """Return impurity mole fraction from the gas mixture."""
    impurity_key = normalize_gas_name(impurity_name)
    if not impurity_key:
        return clamp(default_fraction, 0.0, 1.0)

    for gas in gas_mixture:
        if gas["name"] == impurity_key:
            return clamp(gas.get("fraction", 0.0), 0.0, 1.0)

    return clamp(default_fraction, 0.0, 1.0)


def get_main_gas(gas_mixture, impurity_name=""):
    """
    Determine the logical product gas as the largest non-impurity component.

    This avoids assuming the first gas entry is automatically the product.
    """
    impurity_key = normalize_gas_name(impurity_name)
    candidates = [gas for gas in gas_mixture if gas["name"] != impurity_key]

    if not candidates:
        candidates = gas_mixture

    if not candidates:
        return {"name": "N2", "fraction": 0.95}

    return max(candidates, key=lambda gas: gas.get("fraction", 0.0))


def build_process_context(data):
    """
    Build a normalized context dictionary used across services.
    """
    gas_mixture = normalize_gas_mixture(data.get("gas_mixture", []))

    impurity_name = normalize_gas_name(data.get("impurityToRemove"))
    if not impurity_name and gas_mixture:
        impurity_name = min(
            gas_mixture,
            key=lambda gas: gas.get("fraction", 0.0)
        )["name"]

    impurity_fraction = get_impurity_fraction(gas_mixture, impurity_name)
    main_gas = get_main_gas(gas_mixture, impurity_name)

    pressure = max(0.05, safe_float(data.get("pressure"), 1.0))
    temperature = safe_float(data.get("temperature"), 25.0)
    flowrate = max(0.0, safe_float(data.get("flowRate"), 100.0))
    desired_purity = clamp(safe_float(data.get("desiredPurity"), 95.0), 0.0, 99.99)

    return {
        "gas_mixture": gas_mixture,
        "impurity_name": impurity_name or "CO2",
        "impurity_fraction": impurity_fraction,
        "main_gas_name": main_gas["name"],
        "main_gas_fraction": clamp(main_gas.get("fraction", 0.95), 0.0, 1.0),
        "pressure": pressure,
        "temperature": temperature,
        "flowrate": flowrate,
        "desired_purity": desired_purity,
        "initial_purity": clamp(main_gas.get("fraction", 0.95) * 100.0, 0.0, 99.99),
        "impurity_properties": get_gas_properties(impurity_name or "CO2"),
        "main_gas_properties": get_gas_properties(main_gas["name"]),
    }


def calculate_partial_pressure(yi, pressure):
    """
    Partial pressure relation used across all models.

    Pi = yi * P
    """
    fraction = clamp(safe_float(yi), 0.0, 1.0)
    total_pressure = max(0.0, safe_float(pressure))
    return fraction * total_pressure


def calculate_absorption_equilibrium(y, pressure, henry_constant):
    """
    Henry's law equilibrium loading estimate.

    x = (y * P) / H
    """
    impurity_fraction = clamp(safe_float(y), 0.0, 1.0)
    operating_pressure = max(1e-9, safe_float(pressure, 1.0))
    henry = max(1e-9, safe_float(henry_constant, DEFAULT_GAS_PROPERTIES["henry_constant"]))
    return clamp((impurity_fraction * operating_pressure) / henry, 0.0, 1.0)


def calculate_equilibrium_slope(henry_constant, pressure):
    """
    Henry-law equilibrium slope.

    m = H / P
    """
    henry = max(1e-9, safe_float(henry_constant, DEFAULT_GAS_PROPERTIES["henry_constant"]))
    operating_pressure = max(1e-9, safe_float(pressure, 1.0))
    return clamp(henry / operating_pressure, 0.0, 1e9)


def evaluate_absorption_favorability(henry_constant, pressure, impurity_fraction):
    """
    Evaluate whether absorption is favored by the current gas properties.

    Lower Henry constants, lower equilibrium slopes, higher pressure, and
    higher impurity fractions all improve absorption performance.
    """
    equilibrium_loading = calculate_absorption_equilibrium(
        impurity_fraction, pressure, henry_constant
    )
    equilibrium_slope = calculate_equilibrium_slope(henry_constant, pressure)

    # Low slopes indicate a stronger tendency to transfer impurity into the
    # liquid phase at the current operating pressure.
    solubility_factor = clamp(1.0 / (1.0 + equilibrium_slope / 10.0), 0.0, 1.0)
    concentration_factor = clamp(safe_float(impurity_fraction) / 0.20, 0.0, 1.0)
    pressure_factor = clamp(safe_float(pressure) / 10.0, 0.0, 1.0)
    # The loading factor compares Henry-law liquid loading x to the available
    # gas-phase impurity fraction y. This keeps the absorption strength tied to
    # the actual Henry relation rather than a fixed heuristic bonus.
    loading_factor = clamp(
        safe_divide(equilibrium_loading, max(safe_float(impurity_fraction), 1e-9), 0.0),
        0.0,
        1.0,
    )

    favorability = clamp(
        0.50 * solubility_factor
        + 0.30 * pressure_factor
        + 0.20 * concentration_factor,
        0.0,
        1.0,
    )

    return {
        "equilibrium_loading": equilibrium_loading,
        "equilibrium_slope": equilibrium_slope,
        "solubility_factor": solubility_factor,
        "pressure_factor": pressure_factor,
        "concentration_factor": concentration_factor,
        "loading_factor": loading_factor,
        "favorability": favorability,
    }


def calculate_langmuir_capacity(qmax, b_value, partial_pressure):
    """
    Langmuir adsorption isotherm.

    q = (qmax * b * Pi) / (1 + b * Pi)
    """
    max_capacity = max(0.0, safe_float(qmax))
    affinity = max(0.0, safe_float(b_value))
    gas_partial_pressure = max(0.0, safe_float(partial_pressure))
    denominator = 1.0 + affinity * gas_partial_pressure
    if denominator <= 0.0:
        return 0.0
    return clamp(
        (max_capacity * affinity * gas_partial_pressure) / denominator,
        0.0,
        max_capacity,
    )


def calculate_adsorption_capacity(qmax, b_value, pressure, impurity_fraction):
    """
    Compute adsorption capacity and saturation ratio from Langmuir parameters.
    """
    partial_pressure = calculate_partial_pressure(impurity_fraction, pressure)
    capacity = calculate_langmuir_capacity(qmax, b_value, partial_pressure)
    saturation_ratio = clamp(
        safe_divide(capacity, max(safe_float(qmax), 1e-9), 0.0),
        0.0,
        1.0,
    )

    return {
        "partial_pressure": partial_pressure,
        "capacity": capacity,
        "saturation_ratio": saturation_ratio,
    }


def calculate_permeation_flux(permeability, thickness, feed_partial_pressure, permeate_partial_pressure):
    """
    Membrane permeation flux.

    J = (Perm / delta) * (P_feed_i - P_perm_i)
    """
    permeability_value = max(0.0, safe_float(permeability))
    membrane_thickness = max(1e-9, safe_float(thickness, 1.0))
    driving_force = max(
        0.0,
        safe_float(feed_partial_pressure) - safe_float(permeate_partial_pressure)
    )

    return max(0.0, (permeability_value / membrane_thickness) * driving_force)


def calculate_selectivity(permeability_a, permeability_b):
    """
    Ideal membrane selectivity.

    alpha = Perm_A / Perm_B
    """
    numerator = max(0.0, safe_float(permeability_a))
    denominator = max(1e-9, safe_float(permeability_b, 1.0))
    return max(0.0, numerator / denominator)


def evaluate_membrane_favorability(
    impurity_permeability,
    bulk_permeability,
    pressure,
    impurity_fraction,
    membrane_thickness=1.0,
    permeate_pressure=None,
):
    """
    Evaluate membrane separation favorability.

    The feed-side impurity partial pressure uses Pi = yi * P. A simple low-
    pressure permeate side is assumed to keep the driving force positive.
    """
    feed_pressure = max(0.05, safe_float(pressure, 1.0))
    low_pressure_side = permeate_pressure
    if low_pressure_side is None:
        low_pressure_side = max(0.05, min(1.0, 0.2 * feed_pressure))

    feed_partial_pressure = calculate_partial_pressure(impurity_fraction, feed_pressure)
    permeate_partial_pressure = calculate_partial_pressure(
        clamp(safe_float(impurity_fraction) * 0.25, 0.0, 1.0),
        low_pressure_side,
    )

    flux = calculate_permeation_flux(
        impurity_permeability,
        membrane_thickness,
        feed_partial_pressure,
        permeate_partial_pressure,
    )
    selectivity = calculate_selectivity(impurity_permeability, bulk_permeability)
    pressure_difference = max(0.0, feed_partial_pressure - permeate_partial_pressure)

    flux_factor = clamp(flux / 100.0, 0.0, 1.0)
    driving_force_factor = clamp(
        safe_divide(pressure_difference, max(feed_partial_pressure, 1e-9), 0.0),
        0.0,
        1.0,
    )
    if selectivity <= 1.0:
        selectivity_factor = 0.0
    else:
        selectivity_factor = clamp(
            math.log10(selectivity) / math.log10(20.0),
            0.0,
            1.0,
        )

    favorability = clamp(
        0.45 * flux_factor
        + 0.35 * selectivity_factor
        + 0.20 * driving_force_factor,
        0.0,
        1.0,
    )

    return {
        "feed_partial_pressure": feed_partial_pressure,
        "permeate_partial_pressure": permeate_partial_pressure,
        "pressure_difference": pressure_difference,
        "flux": flux,
        "flux_factor": flux_factor,
        "driving_force_factor": driving_force_factor,
        "selectivity": selectivity,
        "selectivity_factor": selectivity_factor,
        "favorability": favorability,
    }
