import asyncio
import argparse
import logging
import typing
from pathlib import Path
import time

from .builder import build_site
from .commands.live import serve_live
from .commands.gen import gen_post, gen_project

_log = logging.getLogger(__name__)

async def main() -> None:
	logging.basicConfig(level=logging.DEBUG)
	

	root_parser = argparse.ArgumentParser()
	root_parser.add_argument(
		"--root-path",
		default=Path("."),
		help="The root path to use for resolving directories"
	)
	subcommand_parser = root_parser.add_subparsers(dest="subcommand")
	
	live_parser = subcommand_parser.add_parser("live")
	live_parser.add_argument(
		"--host",
		default="127.0.0.1",
		help="Which host to listen on. 0.0.0.0 can be used to listen on all interfaces, while 127.0.0.1 can be used to only listen on loopback"
	)
	live_parser.add_argument("--port", default="8000", help="The port to serve requests on")

	dist_parser = subcommand_parser.add_parser("dist")
	dist_parser.add_argument(
		"--keep-build-root",
		action="store_true",
		help="If enabled, the directory for temporary build artifacts is kept after building. This is meant for debugging"
	)

	gen_parser = subcommand_parser.add_parser("gen")
	gen_subcommand_parser = gen_parser.add_subparsers(dest="gen_subcommand")
	gen_post_parser = gen_subcommand_parser.add_parser("post")
	gen_post_parser.add_argument("title", help="The title of the post")
	gen_post_parser.add_argument("--slug", help="The name of the post in the URL and the filesystem. This should ideally be memorable, short and never changing.")
	gen_project_parser = gen_subcommand_parser.add_parser("project")
	gen_project_parser.add_argument("title", help="The title of the project")
	gen_project_parser.add_argument("--slug", help="The name of the project in the URL and the filesystem. This should ideally be memorable, short and never changing.")

	parsed = root_parser.parse_args()
	_log.debug("parsed: %s", parsed)
	command: typing.Literal["live", "dist", "gen", None] = parsed.subcommand
	
	if command == "dist":
		start_time = time.time()
		await build_site(parsed.root_path, keep_build_root=parsed.keep_build_root)
		end_time = time.time()
		_log.info("build completed in %.2f seconds. Output can be found in dist folder", end_time - start_time)
	elif command == "live":
		await serve_live(parsed.root_path, parsed.host, parsed.port)
	elif command == "gen":
		gen_subcommand: typing.Literal["post", "project"] = parsed.gen_subcommand
		if gen_subcommand == "post":
			await gen_post(parsed.root_path, parsed.title, slug=parsed.slug)
		elif gen_subcommand == "project":
			await gen_project(parsed.root_path, parsed.title, slug=parsed.slug)
		else:
			root_parser.print_help()
	else:
		root_parser.print_help()


asyncio.run(main())
