# Gas Purification App

A clean Flask web application for gas purification analysis and simulation.

## Project Structure

```
Gas Purification App/
├── app.py                          # Main Flask application
├── requirements.txt                # Project dependencies
├── services/                       # Business logic services
│   ├── __init__.py
│   ├── comparison_service.py       # Comparison logic
│   └── simulation_service.py       # Simulation logic
├── templates/                      # Jinja2 templates
│   ├── base.html                  # Base template with Bootstrap
│   ├── home.html                  # Home page
│   ├── input.html                 # Input/comparison page
│   ├── result.html                # Results page
│   └── simulation.html            # Simulation page
└── static/                        # Static files
    ├── css/
    │   └── style.css              # Custom styles
    └── js/
        └── main.js                # Main JavaScript
```

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone or download this project

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Features

- **Home Page**: Welcome page with navigation to tools
- **Comparison Tool**: Input parameters and compare purification methods
- **Simulation Tool**: Run simulations with various purification methods
- **Results Page**: View and analyze results

## Routes

- `/` - Home page
- `/input` - Comparison input page
- `/result` - Results page
- `/simulation` - Simulation page
- `/api/compare` - API endpoint for comparisons (POST)
- `/api/simulate` - API endpoint for simulations (POST)

## Technology Stack

- **Backend**: Flask
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Styling**: Custom CSS
- **JavaScript**: Vanilla JavaScript

## Development

The project structure is designed for easy expansion:

1. Add more services in the `services/` folder
2. Create additional templates in the `templates/` folder
3. Add page-specific styles in `static/css/`
4. Add page-specific JavaScript in `static/js/`

## Notes

- Currently, no complex logic has been implemented
- Services are placeholders ready for business logic
- All routes are functional with basic templates
- Bootstrap 5 CDN is used for responsive design

## Future Enhancements

- Add database models
- Implement service logic for comparisons and simulations
- Add user authentication
- Create data visualization charts
- Add API documentation
