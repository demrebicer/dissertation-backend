# University of Sussex - Thesis Project - Formula 1 British Grand Prix Simulation Backend

This project is the backend part of the Formula 1 British Grand Prix Simulation, developed for the thesis project at the University of Sussex.

## Overview

The backend serves as the API layer, facilitating communication between the frontend and the telemetry data.

## Technologies

- **Python**: The main programming language used for the backend.
- **Sanic**: An asynchronous Python web framework used to create the RESTful API.
- **Docker**: Used to containerize the application, ensuring consistent deployment across various environments.

## Installation

To set up the backend on your local machine, follow these steps:

### Prerequisites

- Python 3.x
- Docker (optional, but recommended for containerized deployment)

### Setup

1. **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2. **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3. **Run the server**:
    ```bash
    python server.py
    ```

    The server will run on `http://localhost:8000/`.

### Docker Setup (Optional)

If you want to run the application in a containerized environment:

1. **Build the Docker image**:
    ```bash
    docker compose up --build -d
    ```

    This will start the server at `http://localhost:8000/`.

## API Endpoints

The backend exposes the following API endpoints for communication with the frontend:

- **`GET /api/telemetry`**: Returns real-time telemetry data for the race simulation.
- **`GET /api/timing`**: Returns real-time timing data for the race simulation.