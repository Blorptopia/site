import asyncio
import logging
from pathlib import Path
import shutil
import typing
import jinja2
from uuid import uuid7
import json

from .models.post import PostMetadata
from .models.project import ProjectMetadata, ProjectsMetadata

_log = logging.getLogger(__name__)

async def build_site(root_path: Path, *, keep_build_root: bool = False, live_reload: bool = False) -> None:
	dist_path = root_path / "dist"
	source_path = root_path / "src"
	
	# The temporary path used for each build instance
	# This is where things like the vite root is kept
	build_root = root_path / f".build-root-{uuid7()}"
	build_root.mkdir()
	
	try:
		context = _BuildContext(source_path, build_root, live_reload=live_reload)
		
		# Copy over assets needed to build html pages
		await context.copy_over_assets()

		# Render "static" pages that have no metadata connection
		await context.render_template(source_path / "index.html")

		# Render blogs
		per_post_metadata: dict[str, PostMetadata] = {}
		for post_path in (source_path / "posts").glob("*"):
			if not post_path.is_dir():
				continue
			metadata_path = post_path / "metadata.json"
			slug = post_path.name
			if not metadata_path.is_file():
				_log.warning("metadata.json missing for post %s", slug)
				continue
			with metadata_path.open() as f:
				# TODO: Validate against model
				per_post_metadata[slug] = json.load(f)
		await asyncio.gather(*[context.render_post(slug, metadata) for slug, metadata in per_post_metadata.items()])

		# Render the post index
		await context.render_template(
			source_path / "posts" / "index.html",
			context={
				"per_post_metadata": per_post_metadata,
			}
		)
		
		# Render projects
		with (source_path / "projects" / "metadata.json").open() as f:
			# TODO: Validate against model
			projects_metadata = json.load(f)
		per_project_metadata: dict[str, ProjectMetadata] = {}
		for project_path in (source_path / "projects").glob("*"):
			if not project_path.is_dir():
				continue
			metadata_path = project_path / "metadata.json"
			slug = project_path.name
			if not metadata_path.is_file():
				_log.warning("metadata.json missing for post %s", slug)
				continue
			with metadata_path.open() as f:
				# TODO: Validate against model
				per_project_metadata[slug] = json.load(f)
		await asyncio.gather(*[context.render_project(slug, metadata, projects_metadata, per_post_metadata) for slug, metadata in per_project_metadata.items()])

		# Render the project index
		await context.render_template(
			source_path / "projects" / "index.html",
			context={
				"per_project_metadata": per_project_metadata,
				"projects_metadata": projects_metadata
			}
		)

		# Create "metadata" files like atom feeds and sitemap
		await context.render_sitemap()
		await context.render_template(source_path / "atom.xml", output_path=Path("public/atom.xml"), context={"per_post_metadata": per_post_metadata})
		await context.render_template(source_path / "robots.txt", output_path=Path("public/robots.txt"))

		# Compile it all into one vite distribution bundle.
		await context.build_dist_bundle(dist_path)
	finally:
		if not keep_build_root:
			shutil.rmtree(build_root)


class _BuildContext:
	"""
	The context for one instance of a build

	This cannot be reused across builds

	Arguments:
		source_path:
			The source of templates and content to build
		build_root:
			The per-instance path used for temporary files

			This needs to be inside the scope of the package.json
			It is the callers responsibility to clean this up after building
		live_reload:
			If live reload is enabled
	"""
	def __init__(
			self,
			source_path: Path,
			build_root: Path,
			*,
			live_reload: bool = False
		) -> None:
		self._source_path = source_path
		self._vite_root: Path = build_root / "vite"
		self._live_reload = live_reload
		self._jinja_environment = jinja2.Environment(
			loader=jinja2.FileSystemLoader(source_path),
			# While we don't currently use async in any of our templates, we want to in the future
			# for things like open_relative to reduce build times
			# However for now, this is currently unused
			enable_async=True
		)
	@staticmethod
	def _create_temporary_folder() -> Path:
		"""
		Creates a temporary branded folder

		Cleanup is the job of the caller
		"""
		# While we don't *need* to use a UUIDv7 and could do fine with a UUIDv4, there is also no negative to using them
		path_id = uuid7()
		path = Path(f"/tmp/blorptopia-site-{path_id}")
		path.mkdir()
		return path

	async def copy_over_assets(self) -> None:
		"""
		Copies over assets needed for building static files

		This will overwrite files if there is a conflict, so you should call this early in the process
		"""
		for path in self._source_path.glob("**/*"):
			if not path.is_file():
				continue
			allowed_suffixes = ["ts", "css", "png", "jpg", "jpeg", "svg"]
			if path.suffix[1:] not in allowed_suffixes:
				continue
			_log.debug("copying over %s to vite root", path)
			destination_path = self._vite_root / path.relative_to(self._source_path)
			destination_path.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy(path, destination_path)

	async def render_template(self, template_path: Path, context: dict[str, typing.Any] | None = None, output_path: Path | None = None) -> None:
		"""
		Renders a template from the template path to the vite directory
		
		Additional context:
			template_name:
				The name of the template
			template_path:
				The template path passed into this function
			open_relative:
				A function that allows you to open a file relative to the template's parent directory
			ssg_live_reload:
				If live reload is enabled

		Arguments:
			template_path:
				The path of the template to render

				This needs to be inside the :attr:`_source_path` or this will raise a :exc:`ValueError`
			context:
				Additional context to pass to the template

				This function will mutate this!
			output_path:
				A path relative to the :attr:`_vite_root` where the rendered file will be written

				If this is :data:`None`, the file will be rendered at where it is relative to the :attr:`_root_path`
		Raises:
			ValueError:
				The template path was not inside the :attr:`_source_path`
		"""
		template_path_relative_to_source = template_path.relative_to(self._source_path)
		_log.debug("rendering template %s", template_path_relative_to_source)
		template_name = str(template_path_relative_to_source)

		template = self._jinja_environment.get_template(template_name)
		
		context = context or {}
		context.update({
			"template_name": template_name,
			"template_path": template_path,
			"open_relative": lambda sub_path: open(template_path.parent / sub_path),
			"ssg_live_reload": self._live_reload
		})

		output = await template.render_async(**context)
		
		if output_path is None:
			output_path = self._vite_root / template_path_relative_to_source
		else:
			output_path = self._vite_root / output_path
		output_path.parent.mkdir(parents=True, exist_ok=True)
		with output_path.open("w+") as f:
			f.write(output)
		_log.debug("rendered template %s", template_path_relative_to_source)

	async def render_sitemap(self) -> None:
		"""
		Renders a sitemap into the vite build root
		
		This will discover pages through the files in the vite build root, so make sure to render those *before* calling this.
		"""
		html_paths = self._vite_root.glob("**/*.html")
		page_urls = [self._get_page_url_for(html_path) for html_path in html_paths]
		await self.render_template(
			Path("src/sitemap.xml"),
			context={
				"page_urls": page_urls
			},
			# Vite doesn't put pages in the dist folder unless it is in the entrypoints (which requires it to be a HTML file)
			# or if it's in the public folder, in which case it will be copied without the public part of the path to the dist folder
			output_path=Path("public/sitemap.xml")
		)

	async def render_post(self, slug: str, metadata: PostMetadata) -> None:
		await self.render_template(self._source_path / "posts" / slug / "index.html", context={"post_metadata": metadata})
	async def render_project(self, slug: str, metadata: ProjectMetadata, projects_metadata: ProjectsMetadata, per_post_metadata: dict[str, PostMetadata]) -> None:
		await self.render_template(
			self._source_path / "projects" / slug / "index.html",
			context={
				"project_metadata": metadata,
				"projects_metadata": projects_metadata,
				"per_post_metadata": per_post_metadata
			}
		)

	def _get_page_url_for(self, path: Path) -> str:
		relative_to_vite_root = path.relative_to(self._vite_root)
		if relative_to_vite_root.name == "index.html":
			url = str(relative_to_vite_root.parent)
			if url == ".":
				return "/"
			return "/" + url
		else:
			return "/" + str(relative_to_vite_root)

	async def build_dist_bundle(self, dist_path: Path) -> None:
		"""
		Builds the vite root into a folder that can be distributed on static file hosts

		Arguments:
			dist_path:
				The path to put the files into
		"""
		entrypoints = [str(path.relative_to(self._vite_root)) for path in self._vite_root.glob("**/*.html")]
		_log.debug("entrypoints: %s", entrypoints)

		with (self._vite_root / "vite.config.js").open("w+") as f:
			vite_config = {
				"mode": "mpa",
				"build": {
					"rollupOptions": {
						"input": entrypoints
					},
					"outDir": str(dist_path.absolute()),
					"emptyOutDir": True,
					"sourcemap": True
				}
			}
			f.write(f"export default {json.dumps(vite_config)}")
		_log.debug("spawning vite with VITE_ROOT: %s", str(self._vite_root.absolute()))
		process = await asyncio.create_subprocess_exec(
			"npm",
			"run",
			"--",
			"vite",
			"build", 
			cwd=self._vite_root,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE,
		)
		exit_code = await process.wait()
		if exit_code != 0:
			assert process.stdout is not None, "we captured the stdout"
			assert process.stderr is not None, "we captured the stderr"
			print(process.stdout.read())
			print(process.stderr.read())
			raise RuntimeError(f"vite exited with {exit_code} exit code")

