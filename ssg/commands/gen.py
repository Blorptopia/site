import logging
from pathlib import Path
from uuid import uuid7
from datetime import datetime
from ..models.post import PostMetadata
from ..models.project import ProjectMetadata
from ..models.ids import PostId
import json

_log = logging.getLogger(__name__)

_DEFAULT_POST_CONTENT = """
{% extends "posts/base.html" %}

{% block head -%}
	{{ super() }}
{% endblock %}
{% block post_content -%}
	<h1>{{ post_metadata.title }}</h1>
{% endblock %}
""".strip()
_DEFAULT_PROJECT_CONTENT = """
{% extends "projects/base.html" %}
{% block page_content %}
	{{ super() }}
{% endblock %}
""".strip()

async def gen_post(root_path: Path, title: str, *, slug: str | None = None) -> None:
	slug = slug or title.lower().replace(" ", "-")
	post_path = root_path / "src" / "posts" / slug
	
	if post_path.is_dir():
		raise ValueError("post with that slug already exists")
	
	post_path.mkdir()
	with (post_path / "metadata.json").open("w+") as f:
		today = str(datetime.now().date())
		metadata: PostMetadata = {
			"id": PostId(str(uuid7())),
			"title": title,
			"summary": "",
			"published_at": today
		}
		json.dump(metadata, f, indent="\t")
		_log.debug("wrote metadata file")
	with (post_path / "index.html").open("w+") as f:
		f.write(_DEFAULT_POST_CONTENT)
		_log.debug("wrote sample content")
	_log.info("wrote post scaffold to %s", post_path)


async def gen_project(root_path: Path, title: str, *, slug: str | None = None) -> None:
	slug = slug or title.lower().replace(" ", "-")
	project_path = root_path / "src" / "posts" / slug
	
	if project_path.is_dir():
		raise ValueError("project with that slug already exists")
	
	project_path.mkdir()
	with (project_path / "metadata.json").open("w+") as f:
		today = str(datetime.now().date())
		metadata: ProjectMetadata = {
			"display_name": title,
			"summary": "TODO",
			"developed_with": {
				"employer": None,
				"developers": 1,
			},
			"tags": [],
			"created_at": today,
			"links": {}
		}
		json.dump(metadata, f, indent="\t")
		_log.debug("wrote metadata file")
	with (project_path / "index.html").open("w+") as f:
		f.write(_DEFAULT_PROJECT_CONTENT)
		_log.debug("wrote sample content")
	_log.info("wrote project scaffold to %s", project_path)


