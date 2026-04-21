"""
Simulation Service Module
Handles gas purification simulation logic
"""

import math


class SimulationService:
    """Service for gas purification simulations"""

    def __init__(self):
        """Initialize the simulation service"""
        pass

    def simulate_process(self, data):
        """
        Simulate purification process over time
        
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
                - time_array: array of time values (hours)
                - purity_evolution: array of purity values (%)
                - efficiency_evolution: array of efficiency values (%)
                - final_purity: final purity achieved
                - time_to_target: time to reach target purity
                - summary: text summary of simulation
        """
        # Get initial parameters
        initial_purity = self._calculate_initial_purity(data.get('gas_mixture', []))
        target_purity = data.get('desiredPurity', 95)
        flowrate = data.get('flowRate', 100)
        pressure = data.get('pressure', 1)
        temperature = data.get('temperature', 25)
        
        # Simulation parameters
        max_time = self._estimate_operation_time(
            initial_purity, target_purity, flowrate, pressure
        )
        time_steps = 100
        dt = max_time / time_steps
        
        # Initialize arrays
        time_array = []
        purity_evolution = []
        efficiency_evolution = []
        
        # Initial values
        current_purity = initial_purity
        current_efficiency = 100.0
        saturation_factor = 0.0
        
        # Simulation loop
        for i in range(time_steps + 1):
            t = i * dt
            time_array.append(t)
            
            # Calculate purity at this time step
            purity = self._calculate_purity(
                current_purity, target_purity, t, max_time, flowrate, pressure
            )
            purity_evolution.append(purity)
            current_purity = purity
            
            # Calculate efficiency (decreases over time due to saturation)
            efficiency = self._calculate_efficiency(
                t, max_time, flowrate, temperature, saturation_factor
            )
            efficiency_evolution.append(efficiency)
            saturation_factor += (efficiency / 100.0) * dt / max_time
        
        # Find time to reach target purity
        time_to_target = self._find_time_to_target(time_array, purity_evolution, target_purity)
        
        # Generate summary
        summary = self._generate_summary(
            initial_purity, current_purity, target_purity, 
            time_to_target, max_time, efficiency_evolution
        )
        
        return {
            'time_array': time_array,
            'purity_evolution': purity_evolution,
            'efficiency_evolution': efficiency_evolution,
            'final_purity': round(current_purity, 2),
            'time_to_target': time_to_target,
            'max_time': round(max_time, 2),
            'summary': summary,
            'initial_purity': round(initial_purity, 2),
            'target_purity': target_purity
        }

    def _calculate_initial_purity(self, gas_mixture):
        """
        Calculate initial purity from gas mixture
        Assumes first gas is main component, others are impurities
        """
        if not gas_mixture:
            return 50.0
        
        # Initial purity is the percentage of the first gas (main component)
        return gas_mixture[0].get('percentage', 50.0)

    def _estimate_operation_time(self, initial_purity, target_purity, flowrate, pressure):
        """
        Estimate operation time to reach target purity
        Simple formula based on flowrate and required purity change
        """
        purity_gap = target_purity - initial_purity
        
        # Base time increases with larger gap
        base_time = abs(purity_gap) * 0.05
        
        # High flowrate reduces time needed
        flowrate_factor = 200 / (flowrate + 50)
        
        # Higher pressure helps purification
        pressure_factor = 1 / (1 + pressure * 0.1)
        
        operation_time = base_time * flowrate_factor * pressure_factor
        
        # Clamp between 0.5 and 24 hours
        return max(0.5, min(24, operation_time))

    def _calculate_purity(self, current_purity, target_purity, time, max_time, flowrate, pressure):
        """
        Calculate purity at a given time
        Uses exponential approach to target purity
        """
        # Normalized time (0 to 1)
        t_norm = min(1.0, time / max_time)
        
        # Exponential curve: purity approaches target
        # Steeper for higher flowrate and pressure
        rate_constant = (2.0 + flowrate / 100.0) * (1.0 + pressure * 0.1)
        exponent = rate_constant * t_norm
        
        # Approach target exponentially
        progress = 1 - math.exp(-exponent)
        
        # Calculate new purity
        new_purity = current_purity + (target_purity - current_purity) * progress
        
        # Can't exceed 99.99%
        return min(99.99, new_purity)

    def _calculate_efficiency(self, time, max_time, flowrate, temperature, saturation):
        """
        Calculate efficiency over time
        Efficiency decreases due to saturation and temperature effects
        """
        # Normalized time
        t_norm = time / max_time if max_time > 0 else 0
        
        # Base efficiency depends on temperature
        temp_factor = 1.0 - abs(temperature - 25) / 200.0
        base_efficiency = 80.0 + 20.0 * temp_factor
        
        # Efficiency decreases with saturation
        saturation_loss = saturation * 60.0
        
        # Efficiency decreases exponentially with time
        time_decay = 30.0 * (1 - math.exp(-2 * t_norm))
        
        # Final efficiency
        efficiency = base_efficiency - saturation_loss - time_decay
        
        # Clamp between 10% and 100%
        return max(10.0, min(100.0, efficiency))

    def _find_time_to_target(self, time_array, purity_array, target_purity):
        """
        Find time when target purity is reached
        """
        for t, p in zip(time_array, purity_array):
            if p >= target_purity:
                return round(t, 2)
        
        # If target not reached, return max time
        return round(time_array[-1], 2) if time_array else 0.0

    def _generate_summary(self, initial_purity, final_purity, target_purity, 
                         time_to_target, max_time, efficiency_evolution):
        """
        Generate a text summary of simulation results
        """
        purity_improvement = final_purity - initial_purity
        target_reached = final_purity >= target_purity
        avg_efficiency = sum(efficiency_evolution) / len(efficiency_evolution) if efficiency_evolution else 0
        
        status = "✓ Target purity achieved" if target_reached else "✗ Target purity not fully reached"
        
        summary = (
            f"{status}. Initial purity: {initial_purity:.1f}% → "
            f"Final purity: {final_purity:.1f}% (Improvement: {purity_improvement:.1f}%). "
            f"Time to target: {time_to_target:.2f}h. "
            f"Average efficiency: {avg_efficiency:.1f}%. "
            f"Maximum operation time: {max_time:.2f}h."
        )
        
        return summary

    def run_simulation(self, parameters):
        """
        Run a gas purification simulation
        
        Args:
            parameters: Dictionary containing simulation parameters
            
        Returns:
            Dictionary with simulation results
        """
        return self.simulate_process(parameters)

    def get_simulation_status(self, simulation_id):
        """
        Get the status of a running simulation
        
        Args:
            simulation_id: ID of the simulation
            
        Returns:
            Dictionary with simulation status
        """
        # Placeholder for status retrieval
        return {'status': 'running'}

    def simulate_tsa_case_study(self):
        """
        Simulate H2/CO purification using Temperature Swing Adsorption (TSA)
        with two adsorption columns operating in a cycle
        
        Returns:
            Dictionary with:
                - cycle_data: Array of cycle states
                - column1_data: Column 1 performance data
                - column2_data: Column 2 performance data
                - temperature_evolution: Temperature profiles
                - summary: Case study summary
        """
        # TSA Cycle parameters
        cycle_time = 24  # hours per complete cycle
        column_count = 2
        adsorption_time = 12  # hours
        regeneration_time = 8  # hours
        cool_down_time = 4    # hours
        
        # Gas mixture: H2/CO/CO2
        input_composition = {
            'H2': 10,      # 10% - desired product
            'CO': 80,      # 80% - main component
            'CO2': 10      # 10% - to be removed by adsorption
        }
        
        # Target output
        target_purity = {
            'H2': 15,      # 15% (enriched)
            'CO': 80,      # 80%
            'CO2': 5       # 5% (reduced)
        }
        
        # Simulation parameters
        num_cycles = 5
        time_resolution = 0.5  # hours per data point
        total_time = num_cycles * cycle_time
        
        # Initialize data arrays
        time_array = []
        cycle_array = []
        col1_state = []
        col2_state = []
        col1_purity = []
        col2_purity = []
        col1_temp = []
        col2_temp = []
        
        # Constants
        adsorption_start = 0
        regeneration_start = adsorption_time
        cool_down_start = regeneration_start + regeneration_time
        next_cycle_start = cool_down_start + cool_down_time
        safe_time_resolution = self._sanitize_time_resolution(time_resolution)
        cycle_points = max(1, int(math.ceil(next_cycle_start / safe_time_resolution)))
        
        # Run simulation
        for cycle_num in range(num_cycles):
            cycle_start_time = cycle_num * cycle_time
            
            # Use a point count instead of a range step so fractional resolutions
            # like 0.5 hours never collapse to a zero range step.
            for step_index in range(cycle_points):
                t_offset = step_index * safe_time_resolution
                if t_offset >= next_cycle_start:
                    break
                
                t = cycle_start_time + t_offset
                time_array.append(t)
                cycle_array.append(cycle_num + 1)
                
                # Column 1 position in cycle (starts at adsorption)
                col1_phase = t_offset % next_cycle_start
                
                # Column 2 position in cycle (offset by half cycle)
                col2_phase = (t_offset + adsorption_time) % next_cycle_start
                
                # Determine states and calculate values
                col1_state_str, col1_purity_val, col1_temp_val = self._calculate_column_state(
                    col1_phase, adsorption_time, regeneration_time, cool_down_time,
                    input_composition, target_purity
                )
                col2_state_str, col2_purity_val, col2_temp_val = self._calculate_column_state(
                    col2_phase, adsorption_time, regeneration_time, cool_down_time,
                    input_composition, target_purity
                )
                
                col1_state.append(col1_state_str)
                col2_state.append(col2_state_str)
                col1_purity.append(col1_purity_val)
                col2_purity.append(col2_purity_val)
                col1_temp.append(col1_temp_val)
                col2_temp.append(col2_temp_val)
        
        # Calculate summary statistics
        avg_col1_purity = sum(col1_purity) / len(col1_purity) if col1_purity else 0
        avg_col2_purity = sum(col2_purity) / len(col2_purity) if col2_purity else 0
        regeneration_count = col1_state.count('Regeneration') + col2_state.count('Regeneration')
        
        summary = (
            f"H2/CO Purification using Temperature Swing Adsorption (TSA). "
            f"Two columns operating in parallel with staggered cycles. "
            f"Average CO2 removal efficiency: Column 1: {avg_col1_purity:.1f}%, "
            f"Column 2: {avg_col2_purity:.1f}%. "
            f"Total regeneration cycles: {regeneration_count}. "
            f"Simulated {num_cycles} complete cycles over {total_time} hours."
        )
        
        return {
            'time_array': time_array,
            'cycle_array': cycle_array,
            'column1_state': col1_state,
            'column2_state': col2_state,
            'column1_purity': col1_purity,
            'column2_purity': col2_purity,
            'column1_temperature': col1_temp,
            'column2_temperature': col2_temp,
            'input_composition': input_composition,
            'target_composition': target_purity,
            'cycle_duration': cycle_time,
            'adsorption_time': adsorption_time,
            'regeneration_time': regeneration_time,
            'cool_down_time': cool_down_time,
            'summary': summary
        }

    def _sanitize_time_resolution(self, time_resolution):
        """
        Ensure time resolution stays positive and usable in iterative loops.
        """
        try:
            safe_resolution = float(time_resolution)
        except (TypeError, ValueError):
            return 1.0

        if safe_resolution <= 0:
            return 1.0

        return safe_resolution

    def _calculate_column_state(self, time_in_cycle, ads_time, regen_time, cooldown_time,
                               input_comp, target_comp):
        """
        Calculate column state, purity, and temperature at a given time in cycle
        """
        cycle_duration = ads_time + regen_time + cooldown_time
        phase_time = time_in_cycle % cycle_duration
        
        # Determine phase
        if phase_time < ads_time:
            state = 'Adsorption'
            # Purity increases during adsorption
            progress = phase_time / ads_time
            base_purity = 100 - input_comp['CO2']  # Remove CO2
            purity = base_purity + (target_comp['CO2'] - input_comp['CO2']) * progress * 0.7
            purity = min(purity, 100)
            # Temperature constant during adsorption (25°C)
            temperature = 25
            
        elif phase_time < ads_time + regen_time:
            state = 'Regeneration'
            # Heating for regeneration (simple linear ramp)
            regen_progress = (phase_time - ads_time) / regen_time
            temperature = 25 + (200 - 25) * regen_progress  # Ramp to 200°C
            # Purity drops during regeneration (bed is being flushed)
            purity = 90 - regen_progress * 40
            
        else:
            state = 'Cool-down'
            # Cooling phase
            cooldown_progress = (phase_time - ads_time - regen_time) / cooldown_time
            temperature = 200 - (200 - 25) * cooldown_progress  # Cool back to 25°C
            # Purity recovers slightly
            purity = 50 + cooldown_progress * 40
        
        return state, purity, temperature

    def simulate_case_study(self):
        """
        Simulate H2/CO purification case study
        Wrapper for TSA case study simulation
        """
        return self.simulate_tsa_case_study()
