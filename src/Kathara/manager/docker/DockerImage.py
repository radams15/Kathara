import logging
from typing import Union, List, Set

import docker.models.images
from docker import DockerClient
from docker.errors import APIError

from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import InvalidImageArchitectureError, DockerImageNotFoundError


class DockerImage(object):
    """Class responsible for interacting with Docker Images."""
    __slots__ = ['client']

    def __init__(self, client: DockerClient) -> None:
        self.client: DockerClient = client

    def get_local(self, image_name: str) -> docker.models.images.Image:
        """Return the specified Docker Image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            docker.models.images.Image: A Docker Image
        """
        return self.client.images.get(image_name)

    def get_remote(self, image_name: str) -> docker.models.images.RegistryData:
        """Gets the registry data for an image.

        Args:
            image_name (str): The name of the image.

        Returns:
            docker.models.images.RegistryData: The data object.

        Raises:
            `docker.errors.APIError`: If the server returns an error.
        """
        return self.client.images.get_registry_data(image_name)

    def pull(self, image_name: str) -> docker.models.images.Image:
        """Pull and return the specified Docker Image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            docker.models.images.Image: A Docker Image
        """
        # If no tag or sha key is specified, we add "latest"
        if (':' or '@') not in image_name:
            image_name = "%s:latest" % image_name

        logging.info("Pulling image `%s`... This may take a while." % image_name)
        return self.client.images.pull(image_name)

    def check_for_updates(self, image_name: str) -> None:
        """Update the specified image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            None
        """
        logging.debug("Checking updates for %s..." % image_name)

        if '@' in image_name:
            logging.debug('No need to check image digest of %s' % image_name)
            return

        local_image_info = self.get_local(image_name)
        # Image has been built locally, so there's nothing to compare.
        local_repo_digests = local_image_info.attrs["RepoDigests"]
        if not local_repo_digests:
            logging.debug("Image %s is build locally" % image_name)
            return

        remote_image_info = self.get_remote(image_name).attrs['Descriptor']
        local_repo_digest = local_repo_digests[0]
        remote_image_digest = remote_image_info["digest"]

        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")
        # We only need to update tagged images, not the ones with digests.
        if remote_image_digest != local_image_digest:
            EventDispatcher.get_instance().dispatch("docker_image_update_found",
                                                    docker_image=self,
                                                    image_name=image_name)

    def check(self, image_name: str) -> None:
        """Check the existence of the specified image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            None

        Raises:
            ConnectionError: If there is a connection error while pulling the Docker image from Docker Hub.
            DockerImageNotFoundError: If the Docker image is not available neither on Docker Hub nor in local repository.
        """
        self._check_and_pull(image_name, pull=False)

    def check_from_list(self, images: Union[List[str], Set[str]]) -> None:
        """Check a list of specified images.

        Args:
            images (Union[List[str], Set[str]]): A list of Docker images name to pull.

        Returns:
            None
        """
        for image in images:
            self._check_and_pull(image)

    def _check_and_pull(self, image_name: str, pull: bool = True) -> None:
        """Check and pull of the specified image.

        Args:
            image_name (str): The name of a Docker Image.
            pull (bool): If True, pull the image from Docker Hub.

        Returns:
            None

        Raises:
            ConnectionError: If there is a connection error while pulling the Docker image from Docker Hub.
            DockerImageNotFoundError: If the Docker image is not available neither on Docker Hub
                nor in local repository.
            InvalidImageArchitectureError: If the Docker image is not compatible with the host architecture.
        """
        try:
            # Tries to get the image from the local Docker repository.
            image = self.get_local(image_name)
            self._check_image_architecture(image)
            try:
                if pull:
                    self.check_for_updates(image_name)
            except APIError:
                logging.debug("Cannot check updates, skipping...")
        except InvalidImageArchitectureError as e:
            raise e
        except APIError:
            # If not found, tries on Docker Hub.
            try:
                # If the image exists on Docker Hub, pulls it.
                registry_data = self.get_remote(image_name)
                self._check_image_architecture(registry_data)
                if pull:
                    self.pull(image_name)
            except APIError as e:
                if e.response.status_code == 500 and 'dial tcp' in e.explanation:
                    raise ConnectionError(
                        "Docker Image `%s` is not available in local repository and "
                        "no Internet connection is available to pull it from Docker Hub." % image_name
                    )
                else:
                    raise DockerImageNotFoundError(image_name)
            except InvalidImageArchitectureError as e:
                raise e

    @staticmethod
    def _check_image_architecture(image: Union[docker.models.images.Image, docker.models.images.RegistryData]) -> None:
        """Check if the specified image is compatible with the host architecture.

        Args:
            image (Union[docker.models.images.Image, docker.models.images.RegistryData]): Docker Image object.

        Returns:
            None
            
        Raises: 
            InvalidImageArchitectureError: If the Docker image is not compatible with the architecture.
        """
        host_arch = utils.get_architecture()

        is_compatible = False
        if isinstance(image, docker.models.images.Image):
            is_compatible = (image.attrs['Architecture'] == host_arch)
        elif isinstance(image, docker.models.images.RegistryData):
            is_compatible = len(list(filter(lambda x: x['architecture'] == host_arch, image.attrs['Platforms']))) > 0

        if not is_compatible:
            raise InvalidImageArchitectureError(image, host_arch)
