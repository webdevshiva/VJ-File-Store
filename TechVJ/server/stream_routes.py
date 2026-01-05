# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import time
import math
import logging
import secrets
import mimetypes
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from TechVJ.bot import multi_clients, work_loads, StreamBot
from TechVJ import StartTime, __version__
from ..utils.time_format import get_readable_time
from TechVJ.utils.render_template import render_page
from config import MULTI_CLIENT

# LOCAL EXCEPTIONS - Replace problematic imports
class FIleNotFound(Exception):
    def __init__(self, message="File not found"):
        self.message = message
        super().__init__(self.message)

class InvalidHash(Exception):
    def __init__(self, message="Invalid hash"):
        self.message = message
        super().__init__(self.message)

# SAFE IMPORT FOR ByteStreamer
try:
    from ..utils.custom_dl import ByteStreamer
    BYTESTREAMER_AVAILABLE = True
    logging.info("ByteStreamer imported successfully")
except ImportError as e:
    BYTESTREAMER_AVAILABLE = False
    logging.warning(f"ByteStreamer import failed: {e}")
    
    # Create a minimal ByteStreamer class as fallback
    class ByteStreamer:
        def __init__(self, client):
            self.client = client
            self.cached_file_ids = {}
        
        async def get_file_properties(self, id: int):
            """Fallback method"""
            raise FIleNotFound("ByteStreamer not properly initialized")
        
        async def yield_file(self, *args, **kwargs):
            """Fallback generator"""
            yield b""

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + StreamBot.username,
            "connected_bots": len(multi_clients),
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
            "version": __version__,
        }
    )


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id_match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not id_match:
                raise FIleNotFound("Invalid path format")
            id = int(id_match.group(1))
            secure_hash = request.rel_url.query.get("hash")
        
        # Check if ByteStreamer is available
        if not BYTESTREAMER_AVAILABLE:
            return web.Response(
                text="<h1>Service Temporarily Unavailable</h1><p>Streaming service is initializing...</p>",
                content_type='text/html'
            )
        
        return web.Response(text=await render_page(id, secure_hash), content_type='text/html')
    
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(f"Stream handler error: {str(e)}")
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id_match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not id_match:
                raise FIleNotFound("Invalid path format")
            id = int(id_match.group(1))
            secure_hash = request.rel_url.query.get("hash")
        
        return await media_streamer(request, id, secure_hash)
    
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(f"Stream handler error: {str(e)}")
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    """Stream media files"""
    
    # Check if ByteStreamer is available
    if not BYTESTREAMER_AVAILABLE:
        raise web.HTTPInternalServerError(text="Streaming service not available")
    
    range_header = request.headers.get("Range", 0)
    
    # Get the least loaded client
    if work_loads:
        index = min(work_loads, key=work_loads.get)
    else:
        index = 0
    
    try:
        faster_client = multi_clients[index]
    except (IndexError, KeyError):
        raise web.HTTPInternalServerError(text="No available clients")
    
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    # Get or create ByteStreamer instance
    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        try:
            tg_connect = ByteStreamer(faster_client)
            class_cache[faster_client] = tg_connect
        except Exception as e:
            logging.error(f"Failed to create ByteStreamer: {e}")
            raise web.HTTPInternalServerError(text="Failed to initialize streamer")

    # Get file properties
    try:
        logging.debug(f"Getting file properties for ID: {id}")
        file_id = await tg_connect.get_file_properties(id)
        logging.debug(f"File properties retrieved: {file_id}")
    except Exception as e:
        logging.error(f"Failed to get file properties: {e}")
        raise FIleNotFound(f"File not found: {str(e)}")
    
    # Validate hash
    if not hasattr(file_id, 'unique_id'):
        raise InvalidHash("File has no unique ID")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    # Get file size
    file_size = getattr(file_id, 'file_size', 0)
    if file_size == 0:
        logging.warning(f"File size is 0 for ID {id}")

    # Handle range requests
    if range_header:
        try:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        except ValueError:
            from_bytes = 0
            until_bytes = file_size - 1
    else:
        from_bytes = 0
        until_bytes = file_size - 1

    # Validate range
    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    # Calculate streaming parameters
    chunk_size = 1024 * 1024  # 1MB chunks
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    
    # Get file stream
    try:
        body = tg_connect.yield_file(
            file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        )
    except Exception as e:
        logging.error(f"Failed to yield file: {e}")
        raise web.HTTPInternalServerError(text="Failed to stream file")

    # Determine MIME type and filename
    mime_type = getattr(file_id, 'mime_type', '')
    file_name = getattr(file_id, 'file_name', '')
    disposition = "attachment"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_name)[0]
        if not mime_type:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    # Return response
    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
