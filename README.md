# Platform Coordination Service

A FastAPI-based service for the First Viscount platform.

## Prerequisites

- Python 3.13+
- pip

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/first-viscount/platform-coordination-service.git
   cd platform-coordination-service
   ```

2. **Set up Python environment**
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   make install-dev
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

5. **Run the service**
   ```bash
   make run
   ```

6. **Access the API**
   - API Documentation: http://localhost:8081/docs
   - Health Check: http://localhost:8081/health

## Development

```bash
make help         # Show all available commands
make format       # Format code
make lint         # Run linting checks
make test         # Run tests
make clean        # Clean up generated files
```

## Project Structure

```
src/
├── core/         # Core configuration
├── api/          # API routes
└── main.py       # Application entry point
tests/            # Test files
```

## License

MIT License