"""
Comparison Service Module
Handles gas purification comparison logic
"""


class ComparisonService:
    """Service for comparing gas purification methods"""

    # Common gases with properties
    COMMON_GASES = {
        'CO2': {'type': 'acid_gas', 'polarity': 'polar'},
        'H2S': {'type': 'acid_gas', 'polarity': 'polar'},
        'NO2': {'type': 'acid_gas', 'polarity': 'polar'},
        'SO2': {'type': 'acid_gas', 'polarity': 'polar'},
        'NH3': {'type': 'basic', 'polarity': 'polar'},
        'N2': {'type': 'inert', 'polarity': 'non-polar'},
        'O2': {'type': 'inert', 'polarity': 'non-polar'},
    }

    def __init__(self):
        """Initialize the comparison service"""
        pass

    def recommend_method(self, data):
        """
        Recommend the best purification method based on input data
        
        Args:
            data: Dictionary containing:
                - gas_mixture: list of dicts with 'name' and 'percentage'
                - temperature: float (°C)
                - pressure: float (bar)
                - flowRate: float (m³/h)
                - impurityToRemove: string
                - desiredPurity: float (%)
        
        Returns:
            Dictionary with:
                - scores: dict with method names and scores
                - best_method: string (best method name)
                - explanation: string (detailed explanation)
                - recommendations: dict with specific notes for each method
        """
        scores = {
            'Absorption': self._score_absorption(data),
            'Adsorption': self._score_adsorption(data),
            'Membrane': self._score_membrane(data)
        }
        
        # Find best method
        best_method = max(scores, key=scores.get)
        best_score = scores[best_method]
        
        # Generate explanation
        explanation = self._generate_explanation(best_method, scores, data)
        recommendations = self._generate_recommendations(scores, data)
        
        return {
            'scores': scores,
            'best_method': best_method,
            'best_score': round(best_score, 2),
            'explanation': explanation,
            'recommendations': recommendations
        }

    def _score_absorption(self, data):
        """
        Calculate score for Absorption method
        Absorption is good for: CO2, H2S, high flowrate, high pressure
        """
        score = 50  # Base score
        
        impurity = data.get('impurityToRemove', '').upper()
        flowrate = data.get('flowRate', 0)
        pressure = data.get('pressure', 1)
        temperature = data.get('temperature', 25)
        desired_purity = data.get('desiredPurity', 95)
        
        # +15 points for CO2 or H2S (good absorption targets)
        if impurity in ['CO2', 'H2S', 'SO2', 'NO2']:
            score += 15
        
        # +10 points for high flowrate (absorption handles bulk flows well)
        if flowrate >= 100:
            score += 10
        elif flowrate >= 50:
            score += 5
        
        # +10 points for moderate to high pressure
        if pressure > 2:
            score += 10
        elif pressure > 1:
            score += 5
        
        # -10 for very high purity requirement (absorption not best for ultra-pure)
        if desired_purity > 99:
            score -= 10
        
        # -5 for very high temperatures (absorption efficiency drops)
        if temperature > 80:
            score -= 5
        
        return max(0, min(100, score))  # Clamp between 0-100

    def _score_adsorption(self, data):
        """
        Calculate score for Adsorption method
        Adsorption is good for: low concentration, high purity, small volumes
        """
        score = 50  # Base score
        
        impurity = data.get('impurityToRemove', '').upper()
        flowrate = data.get('flowRate', 0)
        pressure = data.get('pressure', 1)
        desired_purity = data.get('desiredPurity', 95)
        gas_mixture = data.get('gas_mixture', [])
        
        # +15 points for high purity requirement (adsorption excels at this)
        if desired_purity >= 98:
            score += 15
        elif desired_purity >= 95:
            score += 10
        
        # +10 points for low flowrate (adsorption good for smaller flows)
        if flowrate <= 50:
            score += 10
        elif flowrate <= 100:
            score += 5
        
        # +10 points for good adsorbent compatibility
        if impurity in ['CO2', 'H2S', 'VOC', 'NH3']:
            score += 10
        
        # Find impurity percentage in mixture
        impurity_percentage = self._get_impurity_percentage(gas_mixture, impurity)
        
        # +10 for low impurity concentration (adsorption is concentration-independent)
        if impurity_percentage < 5:
            score += 10
        
        # -10 for very high flowrate (saturates adsorbent quickly)
        if flowrate > 200:
            score -= 10
        
        # -5 for high pressure (may affect adsorption)
        if pressure > 5:
            score -= 5
        
        return max(0, min(100, score))

    def _score_membrane(self, data):
        """
        Calculate score for Membrane method
        Membrane is good for: compact, continuous separation, moderate requirements
        """
        score = 50  # Base score
        
        impurity = data.get('impurityToRemove', '').upper()
        flowrate = data.get('flowRate', 0)
        pressure = data.get('pressure', 1)
        desired_purity = data.get('desiredPurity', 95)
        temperature = data.get('temperature', 25)
        
        # +10 for continuous operation advantage
        score += 10
        
        # +10 for moderate flowrate (membrane sweet spot is 10-150 m³/h)
        if 10 <= flowrate <= 150:
            score += 10
        elif flowrate > 150:
            score += 5
        
        # +10 for moderate pressure (membranes work well at 1-10 bar)
        if 1 <= pressure <= 10:
            score += 10
        
        # +8 for moderate purity (membranes are good here)
        if 90 <= desired_purity <= 99:
            score += 8
        
        # +5 for many applications
        if impurity in ['CO2', 'N2', 'O2', 'H2']:
            score += 5
        
        # -10 for very high purity (hard to achieve with membrane alone)
        if desired_purity > 99.5:
            score -= 10
        
        # -5 for very low temperature (membrane stiffness)
        if temperature < 0:
            score -= 5
        
        # -10 for very high temperature (membrane degradation)
        if temperature > 100:
            score -= 10
        
        return max(0, min(100, score))

    def _get_impurity_percentage(self, gas_mixture, impurity):
        """
        Get the percentage of a specific impurity in the gas mixture
        """
        for gas in gas_mixture:
            if gas.get('name', '').upper() == impurity.upper():
                return gas.get('percentage', 0)
        return 0

    def _generate_explanation(self, best_method, scores, data):
        """
        Generate a text explanation for the recommendation
        """
        impurity = data.get('impurityToRemove', 'unknown')
        desired_purity = data.get('desiredPurity', 95)
        flowrate = data.get('flowRate', 0)
        
        explanations = {
            'Absorption': (
                f"{best_method} is recommended for removing {impurity} to achieve "
                f"{desired_purity}% purity. This method excels at handling high flowrates "
                f"({flowrate} m³/h) and is particularly effective for acid gases. "
                "It uses chemical or physical solvents to absorb impurities."
            ),
            'Adsorption': (
                f"{best_method} is recommended for removing {impurity} to achieve "
                f"{desired_purity}% purity. This method is excellent for achieving high purity levels "
                "and works well with low to moderate flowrates. It uses solid adsorbents "
                "like activated carbon to capture impurities."
            ),
            'Membrane': (
                f"{best_method} is recommended for removing {impurity} to achieve "
                f"{desired_purity}% purity. This method offers continuous, compact separation "
                f"with a flowrate of {flowrate} m³/h and is ideal for applications requiring "
                "steady-state operation with minimal maintenance."
            )
        }
        
        return explanations.get(best_method, f"{best_method} is the recommended method.")

    def _generate_recommendations(self, scores, data):
        """
        Generate specific recommendations for each method
        """
        impurity_pct = self._get_impurity_percentage(
            data.get('gas_mixture', []),
            data.get('impurityToRemove', '')
        )
        
        return {
            'Absorption': {
                'suitability': 'High' if scores['Absorption'] > 60 else 'Moderate' if scores['Absorption'] > 40 else 'Low',
                'advantages': [
                    'Excellent for bulk gas removal',
                    'Cost-effective for high flowrates',
                    'Good for acid gases (CO2, H2S, SO2)'
                ],
                'limitations': [
                    'Requires solvent regeneration',
                    'May not achieve ultra-high purity',
                    'Operating cost depends on energy'
                ]
            },
            'Adsorption': {
                'suitability': 'High' if scores['Adsorption'] > 60 else 'Moderate' if scores['Adsorption'] > 40 else 'Low',
                'advantages': [
                    'Can achieve very high purity levels',
                    'No liquid waste generation',
                    'Good for selective removal'
                ],
                'limitations': [
                    'Adsorbent bed saturation',
                    'Limited by flowrate',
                    'Periodic regeneration needed'
                ]
            },
            'Membrane': {
                'suitability': 'High' if scores['Membrane'] > 60 else 'Moderate' if scores['Membrane'] > 40 else 'Low',
                'advantages': [
                    'Continuous operation',
                    'Compact footprint',
                    'Low maintenance requirements',
                    'No chemicals needed'
                ],
                'limitations': [
                    'May require pre-treatment',
                    'Membrane fouling risk',
                    'Moderate purity levels'
                ]
            }
        }

    def compare(self, data):
        """
        Compare gas purification methods
        
        Args:
            data: Dictionary containing comparison parameters
            
        Returns:
            Dictionary with comparison results
        """
        return self.recommend_method(data)

    def get_comparison_results(self, comparison_id):
        """
        Retrieve comparison results
        
        Args:
            comparison_id: ID of the comparison
            
        Returns:
            Dictionary with comparison results
        """
        # Placeholder for retrieving results
        return {}
