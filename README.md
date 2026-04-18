# VERITAS Flask API Analyzer

A Flask-based API endpoint for analyzing Python code through the VERITAS intake gate system.

## Features

- **POST /analyze** - Accepts Python code and returns VERITAS analysis results
- **Structured JSON Response** - Includes verdict, claim_id, violations, and timestamp
- **Error Handling** - Proper validation and error responses
- **Temporary File Management** - Secure handling of code analysis

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

## Usage

### API Endpoint

**POST** `http://localhost:5000/analyze`

**Request Body:**
```json
{
    "code": "your_python_code_here"
}
```

**Response:**
```json
{
    "claim_id": "VERITAS_20231201_143022",
    "verdict": "SOVEREIGN",
    "timestamp": "2023-12-01T14:30:22.123456",
    "violations": [],
    "summary": "Code analysis complete - SOVEREIGN verdict"
}
```

### Testing

Run the test script to verify functionality:
```bash
python test_analyze.py
```

## Response Codes

- **200** - Analysis completed successfully
- **400** - Invalid request (missing code or invalid JSON)
- **500** - Internal server error during analysis

## Integration with VERITAS

The current implementation uses a mock `omega_assess_file` function. To integrate with the actual VERITAS sovereign module:

1. Replace the mock function with a call to `runSovereignModule`
2. Configure proper module parameters and error handling
3. Set up appropriate security contexts for code execution

## Security Notes

- Code is analyzed in isolated temporary files
- No code execution occurs - only static analysis
- All file operations are properly cleaned up
- Input validation prevents malformed requests

## Development

This API is designed for integration with the VERITAS Research Suite and follows the VERITAS UI/UX standards for structured, deterministic responses.