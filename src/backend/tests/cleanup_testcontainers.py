import docker
import docker.errors
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
client = docker.from_env()

for container in client.containers.list(all=True, filters={"label": "org.testcontainers"}):
    logger.info(f"Removing container {container.name} ({container.id})")
    try:
        container.remove(force=True)
    except docker.errors.APIError as e:
        logger.error(f"Failed to remove {container.id}", exc_info=True)
