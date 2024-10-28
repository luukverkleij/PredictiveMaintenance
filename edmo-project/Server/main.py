# Nuitka compile options
# nuitka-project: --standalone
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/**/*.json=main.dist/

import asyncio
from EDMOBackend import EDMOBackend
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

async def main():
    server = EDMOBackend()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())