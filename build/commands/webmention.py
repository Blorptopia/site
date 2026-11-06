from pathlib import Path
import logging
import aiohttp
import typing
from dataclasses import dataclass
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from collections import defaultdict
import asyncio
import enum
import time

USER_AGENT_NAME = "BlorptopiaSSG"

_log = logging.getLogger(__name__)

async def send_webmentions(root_path: Path, public_origin: str) -> None:
	dist_path = root_path / "dist"
	mentions = _find_webmentions(dist_path, public_origin)
	_log.info("found webmentions %s possible webmentions", len(mentions))

	origin_to_mentions: defaultdict[str, list[_WebMention]] = defaultdict(list)

	for mention in mentions:
		parsed_target_url = urlsplit(mention.target)
		target_origin = f"{parsed_target_url.scheme}://{parsed_target_url.netloc}"
		origin_to_mentions[target_origin].append(mention)

	user_agent = f"{USER_AGENT_NAME} v/0 (webmention sender for {public_origin}. Can be blocked & rate limited via robots.txt as {USER_AGENT_NAME})"
	async with aiohttp.ClientSession(headers={"User-Agent": user_agent}) as client_session:
		robots_fetcher = RobotsFetcher(client_session)
		send_webmention_tasks: dict[_WebMention, asyncio.Task[None]] = {}
		for mention in mentions:
			send_webmention_tasks[mention] = asyncio.create_task(_send_webmention(client_session, robots_fetcher, mention))
		await asyncio.wait((task for task in send_webmention_tasks.values()))
		origin_to_errors: defaultdict[str, list[Exception]] = defaultdict(list)

		for mention, task in send_webmention_tasks.items():
			parsed_target_url = urlsplit(mention.target)
			origin = f"{parsed_target_url.scheme}://{parsed_target_url.netloc}"
			error = task.exception()
			if error is not None:
				if not isinstance(error, Exception):
					raise error 
				origin_to_errors[origin].append(error)

				silenced_error_types: list[typing.Type[Exception]] = [BlockedByRobotsTxtError, NoWebMentionEndpointFoundError]
				if not any((isinstance(error, error_type) for error_type in silenced_error_types)):
					_log.error("failed to send webmention", exc_info=error)

	_log.info("all webmentions sent")

	for origin, mentions in origin_to_mentions.items():
		total_mentions = len(mentions)
		errors = origin_to_errors[origin]
		successful = total_mentions - len(errors)

		error_type_to_count: defaultdict[typing.Type[Exception], int] = defaultdict(lambda: 0)
		for error in errors:
			error_type_to_count[type(error)] += 1
		print(f"{origin} - {successful}/{total_mentions} successful ({", ".join((f"{count}x {error.__name__}" for error, count in error_type_to_count.items()))})")

async def _send_webmention(
	client_session: aiohttp.ClientSession,
	robots_fetcher: RobotsFetcher,
	mention: _WebMention
) -> None:
	parsed_target_url = urlsplit(mention.target)
	origin = f"{parsed_target_url.scheme}://{parsed_target_url.netloc}"
	robots = await robots_fetcher.fetch_robots(origin)
	if not robots.can_fetch(USER_AGENT_NAME, parsed_target_url.path):
		raise BlockedByRobotsTxtError()
	await robots_fetcher.wait_for_next_request_slot(origin)
	response = await client_session.get(mention.target)
	response.raise_for_status()
	text = await response.text()
	parsed = BeautifulSoup(text, "html.parser")
	webmention_element = parsed.select_one("link[rel=\"webmention\"]")
	if webmention_element is None:
		raise NoWebMentionEndpointFoundError()
	webmention_endpoint = webmention_element.attrs["href"]
	_log.debug("webmention endpoint for %s is %s", mention.target, webmention_endpoint)
	webmention_parsed_endpoint = urlsplit(webmention_endpoint)
	webmention_origin = f"{webmention_parsed_endpoint.scheme}://{webmention_parsed_endpoint.netloc}"
	webmention_robots = await robots_fetcher.fetch_robots(webmention_origin)


	if not webmention_robots.can_fetch(USER_AGENT_NAME, webmention_endpoint):
		raise BlockedByRobotsTxtError()
	await robots_fetcher.wait_for_next_request_slot(webmention_origin)
	_log.debug("sending webmention for %s to %s", mention.target, webmention_endpoint)
	response = await client_session.post(webmention_endpoint, data={
		"source": mention.source,
		"target": mention.target
	})
	response.raise_for_status()
	text = await response.text()
	_log.debug("response from webmention endpoint: %s", text)
	

class RobotsFetcher:
	def __init__(self, client_session: aiohttp.ClientSession):
		self._client_session: aiohttp.ClientSession = client_session
		self._pending_fetches: dict[str, asyncio.Event] = {}
		self._origin_to_cached: dict[str, RobotFileParser | None] = {}
		self._origin_to_last_fetch: defaultdict[str, float] = defaultdict(lambda: 0)
		self._origin_fetch_locks: defaultdict[str, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())

	async def fetch_robots(self, origin: str) -> RobotFileParser | None:
		if (cached := self._origin_to_cached.get(origin, None)) is not None:
			return cached
		if (fetch_complete_event := self._pending_fetches.get(origin, None)) is not None:
			await fetch_complete_event.wait()
			return await self.fetch_robots(origin)

		fetch_complete_event = asyncio.Event()
		self._pending_fetches[origin] = fetch_complete_event

		_log.debug("fetching robots.txt for %s", origin)
		response = await self._client_session.get(f"{origin}/robots.txt")
		text = await response.text()
		robots = RobotFileParser()
		robots.parse(text.split("\n"))

		self._origin_to_cached[origin] = robots
		fetch_complete_event.set()
		del self._pending_fetches[origin]

		return robots
	async def wait_for_next_request_slot(self, origin: str) -> None:
		robots = await self.fetch_robots(origin)
		if robots is None:
			return

		async with self._origin_fetch_locks[origin]:
			now = time.time()
			crawl_delay = 0
			if robots is not None:
				crawl_delay = robots.crawl_delay(USER_AGENT_NAME) or crawl_delay
			next_fetch_at = self._origin_to_last_fetch[origin] + crawl_delay
			sleep_duration = next_fetch_at - now
			_log.debug("sleeping for %.2f for fetch to %s", sleep_duration, origin)
			await asyncio.sleep(sleep_duration)


class BlockedByRobotsTxtError(Exception):
	def __init__(self):
		super().__init__("blocked by robots.txt")
class NoWebMentionEndpointFoundError(Exception):
	def __init__(self):
		super().__init__("no webmention endpoint found on this page")






@dataclass(frozen=True)
class _WebMention:
	source: str
	target: str

def _find_webmentions(dist_path: Path, public_origin: str) -> list[_WebMention]:
	mentions: set[_WebMention] = set()
	for html_file_path in dist_path.glob("**/*.html"):
		source_url = _get_url_for_file(html_file_path, public_origin, dist_path)
		with html_file_path.open(encoding="utf-8") as f:
			soup = BeautifulSoup(f.read(),"html.parser")
			anchors = soup.select("a")
			for anchor in anchors:
				relationships = anchor.attrs.get("rel", "")
				if "webmention" not in relationships:
					continue

				raw_target_url = anchor.attrs.get("href", None)
				if raw_target_url is None:
					_log.warning("found webmention anchor without any href in %s", html_file_path)
					continue

				parsed_target_url = urlsplit(raw_target_url)
				target_url = f"{parsed_target_url.scheme}://{parsed_target_url.netloc}{parsed_target_url.path}"

				mentions.add(_WebMention(source=source_url, target=target_url))
	return mentions

def _get_url_for_file(html_file_path: Path, public_origin: str, dist_path: Path) -> str:
	html_relative_to_dist = html_file_path.relative_to(dist_path)
	if html_relative_to_dist.name == "index.html":
		pathname = str(html_relative_to_dist.parent).replace("\\", "/")
	else:
		pathname = str(html_relative_to_dist).replace("\\", "/")
	return f"{public_origin}/{pathname}"

