"""
Simulation Service Module
Handles gas purification simulation logic using simplified engineering models.
"""

import math

from services.comparison_service import ComparisonService
from services.models_service import (
    calculate_adsorption_capacity,
    clamp,
    evaluate_absorption_favorability,
    evaluate_membrane_favorability,
)


class SimulationService:
    """Service for gas purification simulations."""

    VALID_METHODS = ("Absorption", "Adsorption", "Membrane")

    def __init__(self):
        """Initialize the simulation service."""
        self.comparison_service = ComparisonService()

    def simulate_process(self, data):
        """
        Simulate purification performance over time.

        The simulator is intentionally lightweight. It uses simplified
        engineering indicators from Henry's law, the Langmuir isotherm, and
        membrane permeation to produce stable trend curves for the UI.
        """
        context = self.comparison_service.build_analysis_context(data)
        method = self._resolve_method(data)
        method_model = self._build_method_model(method, context)

        initial_purity = context["initial_purity"]
        target_purity = context["desired_purity"]
        effective_target = max(initial_purity, target_purity)

        max_time = self._estimate_operation_time(
            initial_purity,
            effective_target,
            context,
            method_model,
        )

        time_steps = 100
        dt = max_time / time_steps if time_steps > 0 else max_time

        time_array = []
        purity_evolution = []
        efficiency_evolution = []

        current_purity = initial_purity
        dynamic_state = self._initialize_dynamic_state(method, method_model)

        for index in range(time_steps + 1):
            current_time = index * dt
            normalized_time = index / time_steps if time_steps > 0 else 0.0

            if index > 0:
                self._advance_dynamic_state(
                    method,
                    dynamic_state,
                    method_model,
                    context,
                    dt,
                    max_time,
                )

                efficiency = self._calculate_efficiency(
                    method,
                    dynamic_state,
                    method_model,
                    normalized_time,
                )
                step_factor = self._calculate_step_factor(
                    method,
                    dynamic_state,
                    method_model,
                    efficiency,
                    normalized_time,
                    time_steps,
                )

                current_purity += (
                    method_model["attainable_purity"] - current_purity
                ) * step_factor
                current_purity = clamp(
                    current_purity,
                    0.0,
                    method_model["attainable_purity"],
                )
            else:
                efficiency = self._calculate_efficiency(
                    method,
                    dynamic_state,
                    method_model,
                    normalized_time,
                )

            time_array.append(round(current_time, 4))
            purity_evolution.append(round(current_purity, 4))
            efficiency_evolution.append(round(efficiency, 4))

        time_to_target = self._find_time_to_target(
            time_array,
            purity_evolution,
            target_purity,
        )

        summary = self._generate_summary(
            method,
            context,
            method_model,
            current_purity,
            time_to_target,
            max_time,
            efficiency_evolution,
        )

        return {
            "time_array": time_array,
            "purity_evolution": purity_evolution,
            "efficiency_evolution": efficiency_evolution,
            "final_purity": round(current_purity, 2),
            "time_to_target": time_to_target,
            "max_time": round(max_time, 2),
            "summary": summary,
            "initial_purity": round(initial_purity, 2),
            "target_purity": round(target_purity, 2),
            "method": method,
            "main_gas": context["main_gas_name"],
            "model_metrics": method_model["model_metrics"],
        }

    def _resolve_method(self, data):
        """Use the requested method when available, otherwise use the best recommendation."""
        requested_method = self._normalize_method(data.get("method"))
        if requested_method:
            return requested_method

        comparison = self.comparison_service.recommend_method(data)
        recommended_method = self._normalize_method(comparison.get("best_method"))
        return recommended_method or "Adsorption"

    def _normalize_method(self, method_name):
        """Normalize UI or API method names to the internal method labels."""
        normalized = str(method_name or "").strip().lower()
        mapping = {
            "absorption": "Absorption",
            "adsorption": "Adsorption",
            "membrane": "Membrane",
        }
        return mapping.get(normalized)

    def _build_method_model(self, method, context):
        """Build method-specific performance factors from the scientific models."""
        if method == "Absorption":
            return self._build_absorption_model(context)
        if method == "Membrane":
            return self._build_membrane_model(context)
        return self._build_adsorption_model(context)

    def _build_absorption_model(self, context):
        """Build absorption performance factors from Henry's law screening."""
        properties = context["impurity_properties"]
        absorption = evaluate_absorption_favorability(
            properties["henry_constant"],
            context["pressure"],
            context["impurity_fraction"],
        )

        purity_gap = max(0.0, context["desired_purity"] - context["initial_purity"])
        purity_penalty = clamp((context["desired_purity"] - 97.0) / 3.0, 0.0, 1.0)
        temperature_factor = clamp(
            1.0 - max(context["temperature"] - 40.0, 0.0) / 140.0,
            0.70,
            1.05,
        )
        absorption_strength = clamp(
            0.70 * absorption["favorability"] + 0.30 * absorption["loading_factor"],
            0.0,
            1.0,
        )

        attainable_fraction = clamp(
            0.20 + 0.78 * absorption_strength * (1.0 - 0.25 * purity_penalty),
            0.15,
            0.98,
        )

        attainable_purity = clamp(
            context["initial_purity"] + purity_gap * attainable_fraction,
            context["initial_purity"],
            99.99,
        )

        return {
            "attainable_purity": attainable_purity,
            # Higher Henry-law favorability means faster approach to the
            # attainable purity because liquid uptake is more favorable.
            "rate_constant": 0.35 + 2.85 * absorption_strength,
            "base_efficiency": clamp(
                (30.0 + 68.0 * absorption_strength) * temperature_factor,
                15.0,
                99.0,
            ),
            "loading_rate": clamp(
                0.06
                + context["impurity_fraction"] * (0.80 + 0.80 * absorption["favorability"])
                + context["flowrate"] / 600.0,
                0.05,
                0.90,
            ),
            "flow_sensitivity": 0.20,
            "pressure_benefit": 1.20,
            "model_metrics": {
                "henry_constant": round(properties["henry_constant"], 4),
                "equilibrium_loading": round(absorption["equilibrium_loading"], 4),
                "equilibrium_slope": round(absorption["equilibrium_slope"], 4),
                "loading_factor": round(absorption["loading_factor"], 4),
                "absorption_strength": round(absorption_strength, 4),
                "favorability": round(absorption["favorability"], 4),
            },
        }

    def _build_adsorption_model(self, context):
        """Build adsorption performance factors from the Langmuir isotherm."""
        properties = context["impurity_properties"]
        adsorption = calculate_adsorption_capacity(
            properties["langmuir_qmax"],
            properties["langmuir_b"],
            context["pressure"],
            context["impurity_fraction"],
        )

        purity_gap = max(0.0, context["desired_purity"] - context["initial_purity"])
        partial_pressure_factor = clamp(
            adsorption["partial_pressure"] / (1.0 + adsorption["partial_pressure"]),
            0.0,
            1.0,
        )
        loading_factor = adsorption["saturation_ratio"]
        working_capacity_factor = clamp(
            loading_factor * (1.0 - 0.35 * adsorption["saturation_ratio"]),
            0.0,
            1.0,
        )
        purity_factor = clamp((context["desired_purity"] - 90.0) / 10.0, 0.0, 1.0)
        temperature_factor = clamp(
            1.0 - max(context["temperature"] - 90.0, 0.0) / 160.0,
            0.75,
            1.05,
        )

        attainable_fraction = clamp(
            0.18
            + 0.60 * working_capacity_factor
            + 0.14 * partial_pressure_factor
            + 0.08 * purity_factor,
            0.20,
            0.97,
        )

        attainable_purity = clamp(
            context["initial_purity"] + purity_gap * attainable_fraction,
            context["initial_purity"],
            99.99,
        )

        return {
            "attainable_purity": attainable_purity,
            # Pi and Langmuir working capacity control how quickly the bed can
            # move the gas toward its attainable purity.
            "rate_constant": 0.45 + 2.10 * working_capacity_factor + 0.90 * partial_pressure_factor,
            "base_efficiency": clamp(
                (35.0 + 50.0 * working_capacity_factor + 10.0 * purity_factor)
                * temperature_factor,
                15.0,
                99.0,
            ),
            # The adsorption front approaches the Langmuir equilibrium loading
            # over time; this factor governs how quickly q(t) approaches q_eq.
            "loading_rate": clamp(
                0.08
                + 0.45 * partial_pressure_factor
                + 0.30 * loading_factor
                + context["flowrate"] / 700.0,
                0.05,
                0.80,
            ),
            "flow_sensitivity": 0.55,
            "pressure_benefit": 0.60,
            "model_metrics": {
                "langmuir_qmax": round(properties["langmuir_qmax"], 4),
                "langmuir_b": round(properties["langmuir_b"], 4),
                "partial_pressure": round(adsorption["partial_pressure"], 4),
                "capacity": round(adsorption["capacity"], 4),
                "partial_pressure_factor": round(partial_pressure_factor, 4),
                "working_capacity_factor": round(working_capacity_factor, 4),
                "saturation_ratio": round(adsorption["saturation_ratio"], 4),
            },
        }

    def _build_membrane_model(self, context):
        """Build membrane performance factors from flux and selectivity."""
        impurity_properties = context["impurity_properties"]
        main_gas_properties = context["main_gas_properties"]
        membrane = evaluate_membrane_favorability(
            impurity_properties["permeability"],
            main_gas_properties["permeability"],
            context["pressure"],
            context["impurity_fraction"],
        )

        purity_gap = max(0.0, context["desired_purity"] - context["initial_purity"])
        purity_penalty = clamp((context["desired_purity"] - 98.0) / 2.0, 0.0, 1.0)
        temperature_factor = clamp(
            1.0
            - max(context["temperature"] - 100.0, 0.0) / 180.0
            - max(0.0 - context["temperature"], 0.0) / 100.0,
            0.75,
            1.05,
        )
        separation_strength = clamp(
            0.45 * membrane["flux_factor"]
            + 0.35 * membrane["selectivity_factor"]
            + 0.20 * membrane["driving_force_factor"],
            0.0,
            1.0,
        )

        attainable_fraction = clamp(
            0.18 + 0.72 * separation_strength * (1.0 - 0.25 * purity_penalty),
            0.18,
            0.93,
        )

        attainable_purity = clamp(
            context["initial_purity"] + purity_gap * attainable_fraction,
            context["initial_purity"],
            99.99,
        )

        return {
            "attainable_purity": attainable_purity,
            # Membrane separation accelerates with higher permeation flux,
            # better selectivity, and a stronger partial-pressure driving force.
            "rate_constant": (
                0.35
                + 1.90 * membrane["flux_factor"]
                + 1.10 * membrane["selectivity_factor"]
                + 0.75 * membrane["driving_force_factor"]
            ),
            "base_efficiency": clamp(
                (32.0 + 62.0 * separation_strength) * temperature_factor,
                15.0,
                98.0,
            ),
            # Use a slow fouling/throughput penalty so the membrane retains most
            # of its performance unless the operating load is aggressive.
            "loading_rate": clamp(
                0.02
                + context["flowrate"] / 1200.0
                + context["impurity_fraction"] * 0.18
                + 0.08 * (1.0 - membrane["driving_force_factor"]),
                0.02,
                0.30,
            ),
            "flow_sensitivity": 0.40,
            "pressure_benefit": 1.00,
            "model_metrics": {
                "permeability": round(impurity_properties["permeability"], 4),
                "feed_partial_pressure": round(membrane["feed_partial_pressure"], 4),
                "permeate_partial_pressure": round(membrane["permeate_partial_pressure"], 4),
                "flux": round(membrane["flux"], 4),
                "flux_factor": round(membrane["flux_factor"], 4),
                "pressure_difference": round(membrane["pressure_difference"], 4),
                "driving_force_factor": round(membrane["driving_force_factor"], 4),
                "selectivity": round(membrane["selectivity"], 4),
                "selectivity_factor": round(membrane["selectivity_factor"], 4),
                "separation_strength": round(separation_strength, 4),
                "favorability": round(membrane["favorability"], 4),
            },
        }

    def _estimate_operation_time(self, initial_purity, target_purity, context, method_model):
        """
        Estimate a stable simulation time horizon.

        Faster methods and higher pressure shorten the required horizon, while
        larger purity gaps and higher flowrates extend it.
        """
        purity_gap = max(0.0, target_purity - initial_purity)
        base_time = 1.0 + purity_gap * 0.12
        flow_factor = 1.0 + (
            max(context["flowrate"] - 100.0, 0.0) / 250.0
        ) * method_model["flow_sensitivity"]
        pressure_factor = 1.0 / (
            1.0 + context["pressure"] * 0.08 * method_model["pressure_benefit"]
        )
        kinetic_factor = 2.20 / max(method_model["rate_constant"], 0.50)

        operation_time = base_time * flow_factor * pressure_factor * kinetic_factor
        return clamp(operation_time, 0.5, 24.0)

    def _initialize_dynamic_state(self, method, method_model):
        """Initialize method-specific dynamic state variables."""
        if method == "Absorption":
            return {
                "solvent_loading": clamp(
                    method_model["model_metrics"]["equilibrium_loading"] * 0.20,
                    0.0,
                    0.30,
                )
            }

        if method == "Membrane":
            return {
                "fouling": 0.0,
                "flux_retention": 1.0,
                "selectivity_retention": 1.0,
            }

        equilibrium_loading = method_model["model_metrics"]["capacity"]
        equilibrium_saturation = method_model["model_metrics"]["saturation_ratio"]
        return {
            "bed_loading": 0.0,
            "bed_saturation": 0.0,
            "bed_utilization": 0.0,
            "equilibrium_loading": equilibrium_loading,
            "equilibrium_saturation": equilibrium_saturation,
        }

    def _advance_dynamic_state(self, method, dynamic_state, method_model, context, dt, max_time):
        """Advance internal state variables while keeping them physically bounded."""
        time_fraction = dt / max(max_time, 1e-9)

        if method == "Absorption":
            dynamic_state["solvent_loading"] = clamp(
                dynamic_state["solvent_loading"]
                + method_model["loading_rate"] * context["impurity_fraction"] * time_fraction * 0.40,
                0.0,
                0.95,
            )
            return

        if method == "Membrane":
            dynamic_state["fouling"] = clamp(
                dynamic_state["fouling"]
                + method_model["loading_rate"] * time_fraction * 0.50,
                0.0,
                0.60,
            )
            dynamic_state["flux_retention"] = clamp(
                1.0 - 0.75 * dynamic_state["fouling"],
                0.45,
                1.0,
            )
            dynamic_state["selectivity_retention"] = clamp(
                1.0 - 0.35 * dynamic_state["fouling"],
                0.65,
                1.0,
            )
            return

        # Move the adsorbent loading toward the Langmuir equilibrium loading.
        loading_step = clamp(method_model["loading_rate"] * time_fraction * 6.0, 0.0, 0.30)
        target_loading = dynamic_state["equilibrium_loading"]
        current_loading = dynamic_state["bed_loading"]
        updated_loading = current_loading + (target_loading - current_loading) * loading_step

        qmax = max(method_model["model_metrics"]["langmuir_qmax"], 1e-9)
        dynamic_state["bed_loading"] = clamp(updated_loading, 0.0, target_loading)
        dynamic_state["bed_saturation"] = clamp(
            dynamic_state["bed_loading"] / qmax,
            0.0,
            1.0,
        )
        dynamic_state["bed_utilization"] = clamp(
            dynamic_state["bed_loading"] / max(target_loading, 1e-9),
            0.0,
            1.0,
        )

    def _calculate_efficiency(self, method, dynamic_state, method_model, normalized_time):
        """Calculate method-specific efficiency evolution over time."""
        if method == "Absorption":
            efficiency = (
                method_model["base_efficiency"]
                * (1.0 - 0.35 * dynamic_state["solvent_loading"])
                * (1.0 - 0.08 * (1.0 - math.exp(-2.0 * normalized_time)))
            )
            return clamp(efficiency, 10.0, 100.0)

        if method == "Membrane":
            current_flux_factor = (
                method_model["model_metrics"]["flux_factor"]
                * dynamic_state["flux_retention"]
            )
            current_selectivity_factor = (
                method_model["model_metrics"]["selectivity_factor"]
                * dynamic_state["selectivity_retention"]
            )
            efficiency = (
                method_model["base_efficiency"]
                * (0.35 + 0.65 * current_flux_factor)
                * (0.60 + 0.40 * current_selectivity_factor)
            )
            return clamp(efficiency, 10.0, 100.0)

        # Efficiency decays as the bed consumes its Langmuir equilibrium
        # loading capacity. When q(t) approaches q_eq, less adsorption
        # headroom remains and the polishing efficiency drops.
        remaining_capacity_factor = clamp(1.0 - dynamic_state["bed_utilization"], 0.0, 1.0)
        efficiency = (
            method_model["base_efficiency"]
            * (0.20 + 0.80 * remaining_capacity_factor)
        )
        return clamp(efficiency, 10.0, 100.0)

    def _calculate_step_factor(
        self,
        method,
        dynamic_state,
        method_model,
        efficiency,
        normalized_time,
        time_steps,
    ):
        """
        Convert model performance into a stable incremental purity gain.

        The step factor is intentionally capped to avoid unstable exponential
        overshoot in the recursive update.
        """
        if method == "Absorption":
            resistance = 1.0 - 0.45 * dynamic_state["solvent_loading"]
            multiplier = 3.0
        elif method == "Membrane":
            resistance = (
                dynamic_state["flux_retention"]
                * (0.60 + 0.40 * dynamic_state["selectivity_retention"])
            )
            multiplier = (
                2.20
                + 0.80 * method_model["model_metrics"]["driving_force_factor"]
                + 0.80 * method_model["model_metrics"]["selectivity_factor"]
            )
        else:
            resistance = 1.0 - dynamic_state["bed_utilization"]
            multiplier = 2.6 + 0.8 * method_model["model_metrics"]["working_capacity_factor"]

        step_factor = (
            method_model["rate_constant"]
            * (efficiency / 100.0)
            * resistance
            * (1.0 - 0.15 * normalized_time)
            * multiplier
            / max(time_steps, 1)
        )
        return clamp(step_factor, 0.0, 0.24)

    def _find_time_to_target(self, time_array, purity_array, target_purity):
        """Find the time when the target purity is first reached."""
        for time_value, purity_value in zip(time_array, purity_array):
            if purity_value >= target_purity:
                return round(time_value, 2)

        return round(time_array[-1], 2) if time_array else 0.0

    def _generate_summary(
        self,
        method,
        context,
        method_model,
        final_purity,
        time_to_target,
        max_time,
        efficiency_evolution,
    ):
        """Generate a text summary of the simulation results."""
        initial_purity = context["initial_purity"]
        target_purity = context["desired_purity"]
        purity_improvement = final_purity - initial_purity
        average_efficiency = (
            sum(efficiency_evolution) / len(efficiency_evolution)
            if efficiency_evolution else 0.0
        )
        target_reached = final_purity >= target_purity

        if method == "Absorption":
            metrics = method_model["model_metrics"]
            model_note = (
                f"Henry-law favorability={metrics['favorability']:.2f} with "
                f"m={metrics['equilibrium_slope']:.2f}"
            )
        elif method == "Membrane":
            metrics = method_model["model_metrics"]
            model_note = (
                f"flux={metrics['flux']:.2f} and selectivity alpha={metrics['selectivity']:.2f}"
            )
        else:
            metrics = method_model["model_metrics"]
            model_note = (
                f"Langmuir loading q={metrics['capacity']:.2f} mol/kg with "
                f"saturation={metrics['saturation_ratio']:.2f}"
            )

        if target_reached:
            status_text = (
                f"Target purity achieved in {time_to_target:.2f} h using {method.lower()}."
            )
        else:
            status_text = (
                f"Target purity not fully reached within {max_time:.2f} h using {method.lower()}."
            )

        return (
            f"{status_text} Main gas: {context['main_gas_name']}. Impurity removed: "
            f"{context['impurity_name']}. Initial purity: {initial_purity:.1f}%. Final purity: "
            f"{final_purity:.1f}% (gain {purity_improvement:.1f} points). Average efficiency: "
            f"{average_efficiency:.1f}%. Model basis: {model_note}."
        )

    def run_simulation(self, parameters):
        """Run a gas purification simulation."""
        return self.simulate_process(parameters)

    def get_simulation_status(self, simulation_id):
        """
        Get the status of a running simulation.

        Placeholder maintained for compatibility with the current app.
        """
        return {"status": "running"}

    def simulate_tsa_case_study(self):
        """
        Simulate H2/CO purification using Temperature Swing Adsorption (TSA).

        This case-study helper is kept lightweight for the existing dashboard.
        """
        cycle_time = 24
        adsorption_time = 12
        regeneration_time = 8
        cool_down_time = 4

        input_composition = {
            "H2": 10,
            "CO": 80,
            "CO2": 10,
        }

        target_purity = {
            "H2": 15,
            "CO": 80,
            "CO2": 5,
        }

        num_cycles = 5
        time_resolution = 0.5
        total_time = num_cycles * cycle_time

        time_array = []
        cycle_array = []
        col1_state = []
        col2_state = []
        col1_purity = []
        col2_purity = []
        col1_temp = []
        col2_temp = []

        cycle_duration = adsorption_time + regeneration_time + cool_down_time
        safe_time_resolution = self._sanitize_time_resolution(time_resolution)
        cycle_points = max(1, int(math.ceil(cycle_duration / safe_time_resolution)))

        for cycle_num in range(num_cycles):
            cycle_start_time = cycle_num * cycle_time

            for step_index in range(cycle_points):
                time_offset = step_index * safe_time_resolution
                if time_offset >= cycle_duration:
                    break

                current_time = cycle_start_time + time_offset
                time_array.append(current_time)
                cycle_array.append(cycle_num + 1)

                col1_phase = time_offset % cycle_duration
                col2_phase = (time_offset + adsorption_time) % cycle_duration

                col1_state_str, col1_purity_val, col1_temp_val = self._calculate_column_state(
                    col1_phase,
                    adsorption_time,
                    regeneration_time,
                    cool_down_time,
                    input_composition,
                    target_purity,
                )
                col2_state_str, col2_purity_val, col2_temp_val = self._calculate_column_state(
                    col2_phase,
                    adsorption_time,
                    regeneration_time,
                    cool_down_time,
                    input_composition,
                    target_purity,
                )

                col1_state.append(col1_state_str)
                col2_state.append(col2_state_str)
                col1_purity.append(col1_purity_val)
                col2_purity.append(col2_purity_val)
                col1_temp.append(col1_temp_val)
                col2_temp.append(col2_temp_val)

        avg_col1_purity = sum(col1_purity) / len(col1_purity) if col1_purity else 0.0
        avg_col2_purity = sum(col2_purity) / len(col2_purity) if col2_purity else 0.0
        regeneration_count = col1_state.count("Regeneration") + col2_state.count("Regeneration")

        summary = (
            "H2/CO purification using temperature swing adsorption (TSA). "
            "Two columns operate in staggered cycles. "
            f"Average CO2 removal efficiency: Column 1 {avg_col1_purity:.1f}%, "
            f"Column 2 {avg_col2_purity:.1f}%. Total regeneration phases: "
            f"{regeneration_count}. Simulated {num_cycles} complete cycles over "
            f"{total_time} hours."
        )

        return {
            "time_array": time_array,
            "cycle_array": cycle_array,
            "column1_state": col1_state,
            "column2_state": col2_state,
            "column1_purity": col1_purity,
            "column2_purity": col2_purity,
            "column1_temperature": col1_temp,
            "column2_temperature": col2_temp,
            "input_composition": input_composition,
            "target_composition": target_purity,
            "cycle_duration": cycle_time,
            "adsorption_time": adsorption_time,
            "regeneration_time": regeneration_time,
            "cool_down_time": cool_down_time,
            "summary": summary,
        }

    def _sanitize_time_resolution(self, time_resolution):
        """Ensure time resolution stays positive and usable in iterative loops."""
        try:
            safe_resolution = float(time_resolution)
        except (TypeError, ValueError):
            return 1.0

        if safe_resolution <= 0:
            return 1.0

        return safe_resolution

    def _calculate_column_state(
        self,
        time_in_cycle,
        ads_time,
        regen_time,
        cooldown_time,
        input_comp,
        target_comp,
    ):
        """Calculate column state, purity, and temperature at a given time in cycle."""
        cycle_duration = ads_time + regen_time + cooldown_time
        phase_time = time_in_cycle % cycle_duration

        if phase_time < ads_time:
            state = "Adsorption"
            progress = phase_time / ads_time if ads_time > 0 else 0.0
            base_purity = 100.0 - input_comp["CO2"]
            purity = base_purity + (target_comp["CO2"] - input_comp["CO2"]) * progress * 0.7
            purity = min(purity, 100.0)
            temperature = 25.0
        elif phase_time < ads_time + regen_time:
            state = "Regeneration"
            regen_progress = (phase_time - ads_time) / regen_time if regen_time > 0 else 0.0
            temperature = 25.0 + (200.0 - 25.0) * regen_progress
            purity = 90.0 - regen_progress * 40.0
        else:
            state = "Cool-down"
            cooldown_progress = (
                (phase_time - ads_time - regen_time) / cooldown_time
                if cooldown_time > 0 else 0.0
            )
            temperature = 200.0 - (200.0 - 25.0) * cooldown_progress
            purity = 50.0 + cooldown_progress * 40.0

        return state, purity, temperature

    def simulate_case_study(self):
        """Wrapper for the TSA case study simulation."""
        return self.simulate_tsa_case_study()
