import typing


class PostMetadata(typing.TypedDict):
	"""
	Metadata for a blog post

	This is stored in posts/<slug>/metadata.json
	"""
	id: str
	title: str
	summary: str
	published_at: str
	updated_at: typing.NotRequired[str]

