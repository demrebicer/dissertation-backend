import pytest
from server import app  # Assuming the server.py file is in the same directory
from sanic import Sanic, response

@pytest.fixture
def sanic_app():
    return app

@pytest.mark.asyncio
async def test_timing_route(sanic_app):
    request, response = await sanic_app.asgi_client.get('/timing/2021/R')
    assert response.status == 200

@pytest.mark.asyncio
async def test_telemetry_route(sanic_app):
    request, response = await sanic_app.asgi_client.get('/telemetry/2021/R')
    assert response.status == 200
