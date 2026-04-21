from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import json
from services.comparison_service import ComparisonService
from services.report_service import ReportService
from services.simulation_service import SimulationService

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Initialize services
comparison_service = ComparisonService()
report_service = ReportService()
simulation_service = SimulationService()


@app.route('/')
def home():
    """Home page route"""
    return render_template('home.html')


@app.route('/input', methods=['GET', 'POST'])
def input_page():
    """Input page route - handles gas mixture input"""
    if request.method == 'POST':
        # Collect form data
        form_data = collect_form_data(request.form)
        
        # Run comparison analysis
        comparison_results = comparison_service.recommend_method(form_data)
        
        # Store both form data and results in session
        session['form_data'] = form_data
        session['comparison_results'] = comparison_results
        
        return redirect(url_for('result'))
    
    return render_template('input.html')


@app.route('/result')
def result():
    """Result page route"""
    # Retrieve data from session
    form_data = session.get('form_data', None)
    comparison_results = session.get('comparison_results', None)
    
    # Convert to JSON strings for display in template
    form_data_json = json.dumps(form_data) if form_data else None
    comparison_results_json = json.dumps(comparison_results) if comparison_results else None
    
    return render_template('result.html', 
                         form_data=form_data_json,
                         comparison_results=comparison_results_json)


@app.route('/download_report')
def download_report():
    """Download the current comparison results as a PDF report."""
    form_data = session.get('form_data')
    comparison_results = session.get('comparison_results')

    if not form_data or not comparison_results:
        return redirect(url_for('result'))

    report_buffer = report_service.build_comparison_report(form_data, comparison_results)

    return send_file(
        report_buffer,
        as_attachment=True,
        download_name='gas_purification_report.pdf',
        mimetype='application/pdf'
    )


@app.route('/simulation', methods=['GET', 'POST'])
def simulation():
    """Simulation page route"""
    if request.method == 'POST':
        # Get form data from submission or use previously stored data
        if 'form_data' in session:
            # Use existing form data from input page
            form_data = session['form_data']
            # Update with simulation-specific parameters
            form_data['temperature'] = float(request.form.get('temperature', 25))
            form_data['pressure'] = float(request.form.get('pressure', 1))
            form_data['flowRate'] = float(request.form.get('flowRate', 100))
            form_data['desiredPurity'] = float(request.form.get('desiredPurity', 95))
            form_data['impurityToRemove'] = request.form.get('impurityToRemove', 'Unknown')
        else:
            # Create default form data for standalone simulation
            form_data = {
                'gas_mixture': [
                    {'name': request.form.get('impurityToRemove', 'Unknown'), 'percentage': 5},
                    {'name': 'Air', 'percentage': 95}
                ],
                'temperature': float(request.form.get('temperature', 25)),
                'pressure': float(request.form.get('pressure', 1)),
                'flowRate': float(request.form.get('flowRate', 100)),
                'impurityToRemove': request.form.get('impurityToRemove', 'Unknown'),
                'desiredPurity': float(request.form.get('desiredPurity', 95))
            }
            session['form_data'] = form_data
        
        # Run simulation
        simulation_results = simulation_service.simulate_process(form_data)
        
        # Store results in session
        session['simulation_results'] = simulation_results
        
        return redirect(url_for('simulation_results'))

    case_study_results = session.get('case_study_results')
    case_study_dashboard = (
        build_case_study_dashboard(case_study_results)
        if case_study_results else None
    )

    return render_template(
        'simulation.html',
        case_study_dashboard=case_study_dashboard
    )


@app.route('/case-study')
def case_study_simulation():
    """Case study simulation route - H2/CO purification using TSA"""
    # Run case study simulation
    case_study_results = simulation_service.simulate_case_study()
    
    # Store in session
    session['case_study_results'] = case_study_results

    case_study_dashboard = build_case_study_dashboard(case_study_results)

    return render_template(
        'case_study_results.html',
        case_study_dashboard=case_study_dashboard,
        case_study_chart_data=case_study_dashboard['chart_data']
    )


@app.route('/api/compare', methods=['POST'])
def api_compare():
    """API endpoint for comparison"""
    data = request.get_json()
    # Run comparison analysis
    results = comparison_service.recommend_method(data)
    return jsonify(results)


@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    """API endpoint for simulation"""
    data = request.get_json()
    # Run simulation
    results = simulation_service.simulate_process(data)
    return jsonify(results)


def collect_form_data(form):
    """
    Collect and organize form data from the input form
    
    Args:
        form: Flask request.form object
        
    Returns:
        Dictionary containing organized form data
    """
    # Get gas names and percentages as lists
    gas_names = request.form.getlist('gas_names')
    gas_percentages = request.form.getlist('gas_percentages')
    
    # Create gas mixture list
    gas_mixture = []
    for name, percentage in zip(gas_names, gas_percentages):
        if name and percentage:  # Only add if both name and percentage are provided
            gas_mixture.append({
                'name': name.strip(),
                'percentage': float(percentage)
            })
    
    # Collect all form data
    form_data = {
        'gas_mixture': gas_mixture,
        'temperature': float(request.form.get('temperature', 0)),
        'pressure': float(request.form.get('pressure', 0)),
        'flowRate': float(request.form.get('flowRate', 0)),
        'impurityToRemove': request.form.get('impurityToRemove', ''),
        'desiredPurity': float(request.form.get('desiredPurity', 0)),
    }
    
    return form_data


def build_case_study_dashboard(case_study_results):
    """
    Prepare clean, presentation-friendly variables for the case study dashboard.
    """
    time_array = case_study_results.get('time_array', [])
    column_a_temperature = case_study_results.get('column1_temperature', [])
    column_b_temperature = case_study_results.get('column2_temperature', [])
    column_a_purity = case_study_results.get('column1_purity', [])
    column_b_purity = case_study_results.get('column2_purity', [])
    column_a_states = [
        normalize_case_study_state(state)
        for state in case_study_results.get('column1_state', [])
    ]
    column_b_states = [
        normalize_case_study_state(state)
        for state in case_study_results.get('column2_state', [])
    ]

    overall_efficiency = [
        round((purity_a + purity_b) / 2.0, 2)
        for purity_a, purity_b in zip(column_a_purity, column_b_purity)
    ]

    cycle_duration = case_study_results.get('cycle_duration', 0)
    adsorption_time = case_study_results.get('adsorption_time', 0)
    regeneration_time = case_study_results.get('regeneration_time', 0)
    cool_down_time = case_study_results.get('cool_down_time', 0)

    current_time = time_array[-1] if time_array else 0
    current_cycle_time = current_time % cycle_duration if cycle_duration else 0
    column_a_status = build_column_status_panel(
        'Column A',
        current_cycle_time,
        adsorption_time,
        regeneration_time,
        cool_down_time,
        column_a_temperature[-1] if column_a_temperature else None,
        column_a_purity[-1] if column_a_purity else None
    )
    column_b_status = build_column_status_panel(
        'Column B',
        (current_cycle_time + adsorption_time) % cycle_duration if cycle_duration else 0,
        adsorption_time,
        regeneration_time,
        cool_down_time,
        column_b_temperature[-1] if column_b_temperature else None,
        column_b_purity[-1] if column_b_purity else None
    )

    return {
        'summary': case_study_results.get('summary', 'No summary available.'),
        'summary_cards': [
            {'label': 'Cycle Duration', 'value': f'{cycle_duration} h'},
            {'label': 'Adsorption Time', 'value': f'{adsorption_time} h'},
            {'label': 'Regeneration Time', 'value': f'{regeneration_time} h'},
            {'label': 'Cool-down Time', 'value': f'{cool_down_time} h'},
        ],
        'status_panels': [column_a_status, column_b_status],
        'chart_data': {
            'time_array': time_array,
            'temperature': {
                'column_a': column_a_temperature,
                'column_b': column_b_temperature,
            },
            'purity': {
                'column_a': column_a_purity,
                'column_b': column_b_purity,
            },
            'efficiency': {
                'overall': overall_efficiency,
                'column_a': column_a_purity,
                'column_b': column_b_purity,
            },
            'status_history': {
                'column_a': column_a_states,
                'column_b': column_b_states,
            }
        }
    }


def build_column_status_panel(label, phase_time, adsorption_time, regeneration_time,
                              cool_down_time, last_temperature, last_purity):
    """
    Build a status card for a case study column based on the current phase time.
    """
    state, progress = calculate_case_study_phase(phase_time, adsorption_time, regeneration_time, cool_down_time)

    return {
        'label': label,
        'state': state,
        'tone': get_case_study_state_tone(state),
        'note': get_case_study_state_note(state),
        'progress': round(progress, 1),
        'last_temperature': round(last_temperature, 1) if isinstance(last_temperature, (int, float)) else None,
        'last_purity': round(last_purity, 1) if isinstance(last_purity, (int, float)) else None
    }


def calculate_case_study_phase(phase_time, adsorption_time, regeneration_time, cool_down_time):
    """
    Determine the active phase and its progress percentage within the current cycle.
    """
    if adsorption_time > 0 and phase_time < adsorption_time:
        return 'Adsorption', (phase_time / adsorption_time) * 100

    if regeneration_time > 0 and phase_time < adsorption_time + regeneration_time:
        elapsed = phase_time - adsorption_time
        return 'Regeneration', (elapsed / regeneration_time) * 100

    if cool_down_time > 0 and phase_time < adsorption_time + regeneration_time + cool_down_time:
        elapsed = phase_time - adsorption_time - regeneration_time
        return 'Cooling', (elapsed / cool_down_time) * 100

    return 'Standby', 0


def normalize_case_study_state(state):
    """
    Normalize raw service state names into user-friendly dashboard labels.
    """
    state_map = {
        'Cool-down': 'Cooling',
        'Adsorption': 'Adsorption',
        'Regeneration': 'Regeneration',
        'Cooling': 'Cooling',
        'Standby': 'Standby'
    }
    return state_map.get(state, 'Standby')


def get_case_study_state_tone(state):
    """
    Map a state to a Bootstrap color keyword.
    """
    tone_map = {
        'Adsorption': 'primary',
        'Regeneration': 'warning',
        'Cooling': 'info',
        'Standby': 'secondary'
    }
    return tone_map.get(state, 'secondary')


def get_case_study_state_note(state):
    """
    Provide a short human-readable description for the current state.
    """
    note_map = {
        'Adsorption': 'Actively removing impurities from the gas stream.',
        'Regeneration': 'Restoring adsorption capacity for the next cycle.',
        'Cooling': 'Reducing column temperature before reuse.',
        'Standby': 'Waiting for the next active phase.'
    }
    return note_map.get(state, 'Waiting for the next active phase.')


if __name__ == '__main__':
    app.run(debug=True)
