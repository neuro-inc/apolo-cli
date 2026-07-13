from mcp.server.fastmcp import FastMCP

from .tools import apps, disks, jobs, storage

mcp = FastMCP(
    "apolo",
    instructions=(
        "You are connected to the Apolo ML/AI platform. "
        "You can run training jobs, deploy long-lived applications, "
        "and manage persistent storage and disks. "
        "The user must be logged in via `apolo login` before using these tools."
    ),
)

jobs.register(mcp)
apps.register(mcp)
storage.register(mcp)
disks.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
