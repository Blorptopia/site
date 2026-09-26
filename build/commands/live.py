from pathlib import Path
from asyncinotify import Mask, RecursiveInotify
import time
import logging
import asyncio
from aiohttp import web
from ..builder import build_site

_log = logging.getLogger(__name__)

async def serve_live(
	root_path: Path,
	listen_host: str,
	listen_port: int
) -> None:
	source_path = root_path / "src"
	dist_path = root_path / "dist"

	is_ready_event = asyncio.Event()
	update_start_event = asyncio.Event()
	asyncio.create_task(_serve_built_files(is_ready_event, update_start_event, listen_host, listen_port, dist_path))

	source_watcher = RecursiveInotify()
	source_watcher.add_recursive_watch(source_path, Mask.CLOSE_WRITE | Mask.CREATE | Mask.MOVE)

	# Release the *current* waiters but not any future ones
	# This is done as the clients is in a loop of wait for update -> reload -> wait again, and we don't want to spam reloads
	update_start_event.set()
	update_start_event.clear()
	try:
		start_time = time.time()
		await build_site(root_path, live_reload=True)
		end_time = time.time()
		_log.info("built site in %.2f seconds", end_time - start_time)
		is_ready_event.set()
	except:
		_log.error("failed to build site. Waiting for file changes", exc_info=True)


	while True:
		paths_changed: set[Path] = set()
		while True:
			try:
				if len(paths_changed) == 0:
					event = await source_watcher.get()
				else:
					event = await asyncio.wait_for(source_watcher.get(), timeout=.1)
			except asyncio.TimeoutError:
				break
			_log.debug("event: %s", event)
			if event.path is None:
				continue
			_log.debug("change event: %s", event.path)
			paths_changed.add(event.path)
		_log.info("changes to %s detected, re-building", ", ".join([str(path.relative_to(root_path)) for path in paths_changed]))
		paths_changed.clear()

		update_start_event.set()
		update_start_event.clear()
		is_ready_event.clear()
		try:
			start_time = time.time()
			await build_site(root_path, live_reload=True)
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
