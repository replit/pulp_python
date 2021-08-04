import json
import os
import sys
from logging import getLogger

from google.cloud import pubsub_v1

from aiohttp.web import json_response
from dynaconf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models

from pulpcore.plugin.models import (
    Content,
    Publication,
    Distribution,
    Remote,
    Repository
)

from pathlib import PurePath
from .utils import python_content_to_json, PYPI_LAST_SERIAL, PYPI_SERIAL_CONSTANT
from pulpcore.plugin.repo_version_utils import remove_duplicates, validate_repo_version

log = getLogger(__name__)


PACKAGE_TYPES = (
    ("bdist_dmg", "bdist_dmg"),
    ("bdist_dumb", "bdist_dumb"),
    ("bdist_egg", "bdist_egg"),
    ("bdist_msi", "bdist_msi"),
    ("bdist_rpm", "bdist_rpm"),
    ("bdist_wheel", "bdist_wheel"),
    ("bdist_wininst", "bdist_wininst"),
    ("sdist", "sdist"),
)

PLATFORMS = (("windows", "windows"),
             ("macos", "macos"),
             ("freebsd", "freebsd"),
             ("linux", "linux"))


class PythonDistribution(Distribution):
    """
    Distribution for 'Python' Content.
    """

    TYPE = 'python'

    allow_uploads = models.BooleanField(default=True)

    def content_handler(self, path):
        """
        Handler to serve extra, non-Artifact content for this Distribution

        Args:
            path (str): The path being requested
        Returns:
            None if there is no content to be served at path. Otherwise a
            aiohttp.web_response.Response with the content.
        """
        path = PurePath(path)
        name = None
        version = None
        if path.match("pypi/*/*/json"):
            version = path.parts[2]
            name = path.parts[1]
        elif path.match("pypi/*/json"):
            name = path.parts[1]
        # Ignore the google pub/sub link when running the test scripts (it breaks the docs scripts)
        if (path.match("*.tar.gz") or path.match("*.whl")) and os.getenv("ENV") != "test":
            try:
                project_id = settings.GOOGLE_PUBSUB_PROJECT_ID
                topic_id = settings.GOOGLE_PUBSUB_TOPIC_ID

                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(project_id, topic_id)

                message = json.dumps({
                    "action": "package_requested",
                    "package": str(path),
                    "source": self.base_path,
                })

                response = publisher.publish(topic_path, message.encode("utf-8"))
                log.info(
                    "package_requested message send to %s pub/sub, %s",
                    topic_id,
                    response.result()
                )
            except Exception as e:
                log.error(
                    "Could not call package_requested message to pub/sub server, %s",
                    e.__str__()
                )
        if name:
            package_content = PythonPackageContent.objects.filter(
                pk__in=self.publication.repository_version.content,
                name__iexact=name
            )
            # TODO Change this value to the Repo's serial value when implemented
            headers = {PYPI_LAST_SERIAL: str(PYPI_SERIAL_CONSTANT)}
            json_body = python_content_to_json(self.base_path, package_content, version=version)
            if json_body:
                return json_response(json_body, headers=headers)

        return None

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class PythonPackageContent(Content):
    """
    A Content Type representing Python's Distribution Package.

    As defined in pep-0426 and pep-0345.

    https://www.python.org/dev/peps/pep-0491/
    https://www.python.org/dev/peps/pep-0345/
    """

    TYPE = 'python'
    repo_key_fields = ("filename",)
    # Required metadata
    filename = models.TextField(db_index=True)
    packagetype = models.TextField(choices=PACKAGE_TYPES)
    name = models.TextField()
    version = models.TextField()
    sha256 = models.CharField(unique=True, db_index=True, max_length=64)
    # Optional metadata
    python_version = models.TextField()
    metadata_version = models.TextField()
    summary = models.TextField()
    description = models.TextField()
    keywords = models.TextField()
    home_page = models.TextField()
    download_url = models.TextField()
    author = models.TextField()
    author_email = models.TextField()
    maintainer = models.TextField()
    maintainer_email = models.TextField()
    license = models.TextField()
    requires_python = models.TextField()
    project_url = models.TextField()
    platform = models.TextField()
    supported_platform = models.TextField()
    requires_dist = JSONField(default=list)
    provides_dist = JSONField(default=list)
    obsoletes_dist = JSONField(default=list)
    requires_external = JSONField(default=list)
    classifiers = JSONField(default=list)
    project_urls = JSONField(default=dict)
    description_content_type = models.TextField()

    def __str__(self):
        """
        Provide more useful repr information.

        Overrides Content.str to provide the distribution version and type at
        the end.

        e.g. <PythonPackageContent: shelf-reader [version] (whl)>

        """
        return '<{obj_name}: {name} [{version}] ({type})>'.format(
            obj_name=self._meta.object_name,
            name=self.name,
            version=self.version,
            type=self.packagetype
        )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("sha256",)


class PythonPublication(Publication):
    """
    A Publication for PythonContent.
    """

    TYPE = 'python'

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class PythonRemote(Remote):
    """
    A Remote for Python Content.

    Fields:

        prereleases (models.BooleanField): Whether to sync pre-release versions of packages.
    """

    TYPE = 'python'
    DEFAULT_DOWNLOAD_CONCURRENCY = 10
    prereleases = models.BooleanField(default=False)
    includes = JSONField(default=list)
    excludes = JSONField(default=list)
    package_types = ArrayField(models.CharField(max_length=15, blank=True),
                               choices=PACKAGE_TYPES, default=list)
    keep_latest_packages = models.IntegerField(default=0)
    exclude_platforms = ArrayField(models.CharField(max_length=10, blank=True),
                                   choices=PLATFORMS, default=list)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class PythonRepository(Repository):
    """
    Repository for "python" content.
    """

    TYPE = "python"
    CONTENT_TYPES = [PythonPackageContent]
    REMOTE_TYPES = [PythonRemote]

    autopublish = models.BooleanField(default=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"

    def on_new_version(self, version):
        """
        Called when new repository versions are created.

        Args:
            version: The new repository version
        """
        super().on_new_version(version)

        # avoid circular import issues
        from pulp_python.app import tasks

        if self.autopublish:
            tasks.publish(repository_version_pk=version.pk)

    def finalize_new_version(self, new_version):
        """
        Remove duplicate packages that have the same filename.
        """
        remove_duplicates(new_version)
        validate_repo_version(new_version)
