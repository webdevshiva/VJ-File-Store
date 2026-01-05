# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging
from aiohttp import web

# Configure logging
logger = logging.getLogger(__name__)

async def web_server():
    """
    Create and configure the web application for streaming
    """
    try:
        # Import routes with error handling
        try:
            from .stream_routes import routes
            logger.info("✅ Successfully imported stream routes")
        except ImportError as e:
            logger.error(f"❌ Failed to import stream routes: {e}")
            # Create empty routes as fallback
            routes = []
            
        # Create web application with optimized settings
        web_app = web.Application(
            client_max_size=30000000,  # 30MB max file size
            middlewares=[]  # You can add middlewares here if needed
        )
        
        # Add routes
        if routes:
            web_app.add_routes(routes)
            logger.info(f"✅ Added {len(routes)} route(s) to web application")
        else:
            logger.warning("⚠️ No routes added to web application")
            
        # Add basic health check route if no routes were imported
        if not routes:
            async def health_check(request):
                return web.json_response({
                    "status": "running",
                    "message": "Web server is running but no streaming routes available"
                })
            
            web_app.router.add_get("/", health_check)
            web_app.router.add_get("/health", health_check)
            logger.info("✅ Added fallback health check routes")
        
        logger.info("✅ Web server application created successfully")
        return web_app
        
    except Exception as e:
        logger.critical(f"❌ Failed to create web server: {e}")
        # Return minimal web app even on error
        web_app = web.Application()
        async def error_handler(request):
            return web.json_response({
                "error": "Server initialization failed",
                "details": str(e)
            }, status=500)
        web_app.router.add_get("/", error_handler)
        return web_app
