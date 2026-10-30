from pathlib import Path
import watchfiles
import time
import logging
import asyncio
from aiohttp import web
from ..builder import build_site

_log = logging.getLogger(__name__)

async def serve_live(
	root_path: Path,
	public_origin: str,
	listen_host: str,
	listen_port: int,
	*,
	vite_output: bool = False
) -> None:
	source_path = root_path / "src"
	dist_path = root_path / "dist"

	is_ready_event = asyncio.Event()
	update_start_event = asyncio.Event()
	asyncio.create_task(_serve_built_files(is_ready_event, update_start_event, listen_host, listen_port, dist_path))

	watch_filter = lambda change, path: change in [watchfiles.Change.added, watchfiles.Change.deleted, watchfiles.Change.modified]

	# Release the *current* waiters but not any future ones
	# This is done as the clients is in a loop of wait for update -> reload -> wait again, and we don't want to spam reloads
	update_start_event.set()
	update_start_event.clear()
	try:
		start_time = time.time()
		await build_site(root_path, public_origin, live_reload=True, vite_output=vite_output)
		end_time = time.time()
		_log.info("built site in %.2f seconds", end_time - start_time)
		is_ready_event.set()
	except:
		_log.error("failed to build site. Waiting for file changes", exc_info=True)

	async for change in watchfiles.awatch(source_path, watch_filter=watch_filter):
		_log.info("files changed, rebuilding!")
		update_start_event.set()
		update_start_event.clear()
		is_ready_event.clear()
		try:
			start_time = time.time()
			await build_site(root_path, public_origin, live_reload=True, vite_output=vite_output)
			end_time = time.time()
			_log.info("built site in %.2f seconds", end_time - start_time)
			is_ready_event.set()
		except:
			_log.error("failed to build site. Waiting for file changes", exc_info=True)

async def _serve_built_files(
	is_ready_event: asyncio.Event,
	update_start_event: asyncio.Event,
	host: str,
	port: int,
	dist_path: Path
) -> None:
	app = web.Application()
	routes = web.RouteTableDef()

	@routes.get("/ws")
	async def handle_websocket(request: web.Request) -> web.WebSocketResponse:
		ws = web.WebSocketResponse()
		await ws.prepare(request)

		await update_start_event.wait()

		return ws
	@routes.get("/")
	@routes.get("/{path:.+}")
	async def get_from_build_path(request: web.Request) -> web.FileResponse:
		await is_ready_event.wait()
		
		path = Path(request.match_info.get("path", ""))
		path = dist_path / (dist_path / path).relative_to(dist_path)
		
		if path.is_dir():
			return web.FileResponse(path / "index.html")
		else:
			return web.FileResponse(path)

	app.add_routes(routes)
	
	_log.info("started serving on port: %s", port)
	# While yes this is undocumented and unstable
	# it has been there for years and worked fine
	# There is also no alternative (afaik) to run the app *asynchronously* so the alternative
	# would be to create a full new thread to run the app
	await web._run_app(app, host=host, port=port)
