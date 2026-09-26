import typing
from .ids import TagId, PostId, EmployerId

class ProjectMetadata(typing.TypedDict):
	"""
	Metadata for a project

	This is stored in projects/<slug>/metadata.json
	"""
	display_name: str
	summary: str
	created_at: str
	tags: list[TagId]
	developed_with: ProjectDevelopedWith
	links: ProjectLinks

class ProjectTag(typing.TypedDict):
	display_name: str

class ProjectLinks(typing.TypedDict):
	demo: typing.NotRequired[str]
	blog_slugs: typing.NotRequired[list[PostId]]



class ProjectDevelopedWith(typing.TypedDict):
	employer: EmployerId

class Employer(typing.TypedDict):
	display_name: str

class ProjectsMetadata(typing.TypedDict):
	employers: dict[EmployerId, Employer]
	tags: dict[TagId, ProjectTag]
