"""
Comparison Service Module
Handles gas purification method comparison using simplified engineering models.
"""

from services.models_service import (
    build_process_context,
    calculate_adsorption_capacity,
    clamp,
    evaluate_absorption_favorability,
    evaluate_membrane_favorability,
    get_gas_properties,
    normalize_gas_mixture,
    normalize_gas_name,
)


class ComparisonService:
    """Service for comparing gas purification methods."""

    def __init__(self):
        """Initialize the comparison service."""
        pass

    def recommend_method(self, data):
        """
        Recommend the best purification method based on input data.

        Returns a frontend-compatible dictionary containing:
            - scores
            - best_method
            - best_score
            - explanation
            - recommendations
        """
        context = self.build_analysis_context(data)

        evaluations = {
            "Absorption": self._evaluate_absorption(context),
            "Adsorption": self._evaluate_adsorption(context),
            "Membrane": self._evaluate_membrane(context),
        }

        scores = {
            method: round(details["score"], 2)
            for method, details in evaluations.items()
        }

        best_method = max(scores, key=scores.get)
        best_score = scores[best_method]

        explanation = self._generate_explanation(best_method, evaluations, context)
        recommendations = self._generate_recommendations(evaluations, context)

        return {
            "scores": scores,
            "best_method": best_method,
            "best_score": round(best_score, 2),
            "explanation": explanation,
            "recommendations": recommendations,
        }

    def build_analysis_context(self, data):
        """
        Build a service-level process context with consistent gas-role logic.

        Rules:
            - The dominant feed gas is the component with the largest percentage.
            - impurityToRemove is always treated as the removal target.
            - Initial purity refers to the retained main product gas. If the
              impurity is also the dominant feed gas, the product gas becomes
              the largest remaining component instead of the impurity.
        """
        context = build_process_context(data)
        gas_mixture = context.get("gas_mixture") or normalize_gas_mixture(
            data.get("gas_mixture", [])
        )

        impurity_name = normalize_gas_name(data.get("impurityToRemove")) or context["impurity_name"]
        dominant_gas = self._get_largest_component(gas_mixture)
        product_gas = self._get_main_product_gas(gas_mixture, impurity_name, dominant_gas)

        context["impurity_name"] = impurity_name or context["impurity_name"]
        context["dominant_gas_name"] = dominant_gas["name"]
        context["dominant_gas_fraction"] = dominant_gas["fraction"]
        context["main_gas_name"] = product_gas["name"]
        context["main_gas_fraction"] = clamp(product_gas["fraction"], 0.0, 1.0)
        context["initial_purity"] = clamp(product_gas["fraction"] * 100.0, 0.0, 99.99)
        context["main_gas_properties"] = get_gas_properties(product_gas["name"])

        return context

    def _get_largest_component(self, gas_mixture):
        """
        Return the gas with the largest feed percentage.

        This is the dominant component in the incoming mixture and replaces any
        ordering assumption from the original gas list.
        """
        if not gas_mixture:
            return {"name": "N2", "fraction": 0.95}

        return max(gas_mixture, key=lambda gas: gas.get("fraction", 0.0))

    def _get_main_product_gas(self, gas_mixture, impurity_name, dominant_gas):
        """
        Determine the retained product gas used for purity calculations.

        The dominant feed gas is used unless it is also the impurity targeted
        for removal, in which case the largest remaining component becomes the
        product gas for the purity basis.
        """
        if not gas_mixture:
            return dominant_gas

        impurity_key = normalize_gas_name(impurity_name)
        if dominant_gas["name"] != impurity_key:
            return dominant_gas

        non_impurity_components = [
            gas for gas in gas_mixture if gas["name"] != impurity_key
        ]
        if not non_impurity_components:
            return dominant_gas

        return max(non_impurity_components, key=lambda gas: gas.get("fraction", 0.0))

    def _evaluate_absorption(self, context):
        """
        Score absorption from Henry-law behavior.

        Key drivers:
            - Henry constant
            - operating pressure
            - impurity fraction
            - desired purity target
        """
        properties = context["impurity_properties"]
        absorption = evaluate_absorption_favorability(
            properties["henry_constant"],
            context["pressure"],
            context["impurity_fraction"],
        )

        # Use the Henry-law favorability directly as the primary scoring driver.
        # The remaining factors only shape how well absorption fits the target
        # purity and bulk-throughput use case.
        purity_alignment = clamp(
            1.0 - max(context["desired_purity"] - 97.5, 0.0) / 2.5,
            0.20,
            1.0,
        )
        throughput_factor = clamp(context["flowrate"] / 250.0, 0.25, 1.0)
        temperature_factor = clamp(
            1.0 - max(context["temperature"] - 40.0, 0.0) / 140.0,
            0.65,
            1.0,
        )

        score_factor = clamp(
            0.65 * absorption["favorability"]
            + 0.20 * absorption["loading_factor"]
            + 0.10 * throughput_factor
            + 0.05 * purity_alignment * temperature_factor,
            0.0,
            1.0,
        )
        score = 100.0 * score_factor

        return {
            "score": clamp(score, 0.0, 100.0),
            "henry_constant": properties["henry_constant"],
            "equilibrium_loading": absorption["equilibrium_loading"],
            "equilibrium_slope": absorption["equilibrium_slope"],
            "loading_factor": absorption["loading_factor"],
            "favorability": absorption["favorability"],
        }

    def _evaluate_adsorption(self, context):
        """
        Score adsorption from Langmuir loading and bed saturation behavior.

        Key drivers:
            - adsorption capacity q
            - impurity partial pressure
            - saturation ratio
            - desired purity target
        """
        properties = context["impurity_properties"]
        adsorption = calculate_adsorption_capacity(
            properties["langmuir_qmax"],
            properties["langmuir_b"],
            context["pressure"],
            context["impurity_fraction"],
        )

        # Convert Langmuir outputs into bounded engineering factors for
        # screening. Pi drives loading, q measures usable capacity, and the
        # saturation ratio penalizes cases that would exhaust the bed quickly.
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
        stability_factor = clamp(1.0 - adsorption["saturation_ratio"], 0.0, 1.0)
        purity_factor = clamp((context["desired_purity"] - 90.0) / 10.0, 0.0, 1.0)
        temperature_factor = clamp(
            1.0 - max(context["temperature"] - 90.0, 0.0) / 150.0,
            0.70,
            1.0,
        )
        flow_factor = clamp(
            1.0 - max(context["flowrate"] - 140.0, 0.0) / 260.0,
            0.25,
            1.0,
        )

        score_factor = clamp(
            0.40 * working_capacity_factor
            + 0.20 * partial_pressure_factor
            + 0.15 * stability_factor
            + 0.15 * purity_factor
            + 0.05 * temperature_factor
            + 0.05 * flow_factor,
            0.0,
            1.0,
        )
        score = 100.0 * score_factor

        return {
            "score": clamp(score, 0.0, 100.0),
            "langmuir_qmax": properties["langmuir_qmax"],
            "langmuir_b": properties["langmuir_b"],
            "capacity": adsorption["capacity"],
            "partial_pressure": adsorption["partial_pressure"],
            "working_capacity_factor": working_capacity_factor,
            "saturation_ratio": adsorption["saturation_ratio"],
        }

    def _evaluate_membrane(self, context):
        """
        Score membrane separation from flux and selectivity.

        Key drivers:
            - permeation flux
            - pressure difference
            - selectivity
            - desired purity target
        """
        impurity_properties = context["impurity_properties"]
        main_gas_properties = context["main_gas_properties"]
        membrane = evaluate_membrane_favorability(
            impurity_properties["permeability"],
            main_gas_properties["permeability"],
            context["pressure"],
            context["impurity_fraction"],
        )

        purity_window = clamp(
            1.0 - max(context["desired_purity"] - 98.5, 0.0) / 2.5,
            0.15,
            1.0,
        )
        flow_window = clamp(
            1.0 - abs(context["flowrate"] - 120.0) / 240.0,
            0.25,
            1.0,
        )
        temperature_factor = clamp(
            1.0
            - max(context["temperature"] - 100.0, 0.0) / 180.0
            - max(0.0 - context["temperature"], 0.0) / 120.0,
            0.65,
            1.0,
        )

        score_factor = clamp(
            0.40 * membrane["flux_factor"]
            + 0.30 * membrane["selectivity_factor"]
            + 0.15 * membrane["driving_force_factor"]
            + 0.10 * purity_window
            + 0.05 * flow_window * temperature_factor,
            0.0,
            1.0,
        )
        score = 100.0 * score_factor

        return {
            "score": clamp(score, 0.0, 100.0),
            "permeability": impurity_properties["permeability"],
            "feed_partial_pressure": membrane["feed_partial_pressure"],
            "permeate_partial_pressure": membrane["permeate_partial_pressure"],
            "flux": membrane["flux"],
            "pressure_difference": membrane["pressure_difference"],
            "driving_force_factor": membrane["driving_force_factor"],
            "selectivity": membrane["selectivity"],
            "selectivity_factor": membrane["selectivity_factor"],
        }

    def _generate_explanation(self, best_method, evaluations, context):
        """Generate a concise engineering explanation for the recommendation."""
        impurity = context["impurity_name"]
        main_gas = context["main_gas_name"]
        desired_purity = context["desired_purity"]

        if best_method == "Absorption":
            details = evaluations["Absorption"]
            return (
                f"Absorption is recommended for removing {impurity} from a {main_gas}-rich "
                f"stream. Henry-law screening gives H={details['henry_constant']:.2f} bar and "
                f"an equilibrium slope m={details['equilibrium_slope']:.2f} at "
                f"{context['pressure']:.2f} bar, which translates to an absorption "
                f"favorability of {details['favorability'] * 100.0:.1f}%. That makes solvent "
                f"contact the strongest of the screened options for approaching "
                f"{desired_purity:.1f}% purity."
            )

        if best_method == "Adsorption":
            details = evaluations["Adsorption"]
            return (
                f"Adsorption is recommended for removing {impurity} from a {main_gas}-rich "
                f"stream. The Langmuir model predicts q={details['capacity']:.2f} mol/kg at "
                f"Pi={details['partial_pressure']:.2f} bar, with a saturation ratio of "
                f"{details['saturation_ratio']:.2f}. That combination supports selective "
                f"polishing toward the requested {desired_purity:.1f}% purity target."
            )

        details = evaluations["Membrane"]
        return (
            f"Membrane separation is recommended for removing {impurity} from a {main_gas}-rich "
            f"stream. The screening model predicts an impurity flux of {details['flux']:.2f} "
            f"(normalized units) with a selectivity alpha={details['selectivity']:.2f} against "
            f"{main_gas}, supported by a partial-pressure driving force of "
            f"{details['pressure_difference']:.2f} bar. That gives the membrane route the best "
            f"continuous-separation fit for the current target of {desired_purity:.1f}% purity."
        )

    def _generate_recommendations(self, evaluations, context):
        """Generate per-method recommendation cards while keeping the UI schema intact."""
        return {
            "Absorption": self._build_absorption_recommendation(
                evaluations["Absorption"], context
            ),
            "Adsorption": self._build_adsorption_recommendation(
                evaluations["Adsorption"], context
            ),
            "Membrane": self._build_membrane_recommendation(
                evaluations["Membrane"], context
            ),
        }

    def _build_absorption_recommendation(self, evaluation, context):
        """Build absorption recommendation details."""
        impurity = context["impurity_name"]
        suitability = self._score_to_suitability(evaluation["score"])

        if evaluation["favorability"] >= 0.60:
            solubility_note = (
                f"Henry-law behavior is favorable for {impurity} at the current pressure."
            )
        else:
            solubility_note = (
                f"Absorption remains feasible, but {impurity} is only moderately soluble in this screening model."
            )

        advantages = [
            solubility_note,
            f"Operating at {context['pressure']:.2f} bar improves the liquid-phase driving force.",
            "Handles continuous bulk gas processing well, especially at higher throughputs.",
        ]

        limitations = [
            "Solvent circulation and regeneration add operating complexity.",
            "Absorption alone becomes less attractive when purity requirements move into ultra-high polishing service.",
            "Performance usually weakens as temperature rises because gas solubility falls.",
        ]

        return {
            "suitability": suitability,
            "advantages": advantages,
            "limitations": limitations,
        }

    def _build_adsorption_recommendation(self, evaluation, context):
        """Build adsorption recommendation details."""
        suitability = self._score_to_suitability(evaluation["score"])

        advantages = [
            (
                f"Langmuir loading predicts q={evaluation['capacity']:.2f} mol/kg at "
                f"Pi={evaluation['partial_pressure']:.2f} bar."
            ),
            (
                f"The requested purity target of {context['desired_purity']:.1f}% aligns well "
                "with adsorption as a polishing step."
            ),
            "Selective solid media can remove impurities without introducing solvent handling.",
        ]

        limitations = [
            (
                f"Estimated saturation ratio is {evaluation['saturation_ratio']:.2f}, so cycle "
                "management and regeneration remain important."
            ),
            "Higher flowrates shorten bed life and can reduce practical contact time.",
            "Competitive adsorption from other trace species is not included in this simplified model.",
        ]

        return {
            "suitability": suitability,
            "advantages": advantages,
            "limitations": limitations,
        }

    def _build_membrane_recommendation(self, evaluation, context):
        """Build membrane recommendation details."""
        main_gas = context["main_gas_name"]
        suitability = self._score_to_suitability(evaluation["score"])

        advantages = [
            (
                f"Predicted impurity flux is {evaluation['flux']:.2f} with a partial-pressure "
                f"driving force of {evaluation['pressure_difference']:.2f} bar."
            ),
            (
                f"Selectivity alpha={evaluation['selectivity']:.2f} against {main_gas} supports "
                "continuous separation in this screening model."
            ),
            "Membranes offer compact, steady-state operation with no solvent regeneration loop.",
        ]

        limitations = [
            "Single-stage membranes may need polishing support for the highest purity targets.",
            (
                f"If {context['impurity_name']} is not much more permeable than {main_gas}, "
                "separation performance can drop quickly."
            ),
            "Pretreatment and fouling risks are not captured in this simplified scoring model.",
        ]

        return {
            "suitability": suitability,
            "advantages": advantages,
            "limitations": limitations,
        }

    def _score_to_suitability(self, score):
        """Map numeric score to the UI's suitability labels."""
        if score >= 70.0:
            return "High"
        if score >= 45.0:
            return "Moderate"
        return "Low"

    def compare(self, data):
        """Compare gas purification methods."""
        return self.recommend_method(data)

    def get_comparison_results(self, comparison_id):
        """
        Retrieve comparison results.

        Placeholder maintained for compatibility with the existing app shape.
        """
        return {}
