from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import init_db


# Create app instance
def create_app() -> FastAPI:
    app = FastAPI(
        title='Shift Manager API',
        description='API for shift planning and management',
        version='0.1.0',
        docs_url='/docs',
        redoc_url='/redoc'
    )
    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            o.strip() for o in settings.cors_origins.split(',') if o.strip()
        ],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*']
    )
    # Include API routers
    app.include_router(v1_router)

    # Add event to init DB
    @app.on_event('startup')
    async def startup_event():
        init_db()
        logger.info('Database initialized')
    
    return app


# Create fastapi app
app = create_app()


# Root endpoint
@app.get('/')
async def root():
    return {
        'message': 'Here is the Shift Manager API!',
        'docs': '/docs',
        'redoc': '/redoc'
    }
