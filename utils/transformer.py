from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from typing import Any, Callable, Optional


class ToAsync:
    """Converts a blocking function to an async function"""

    def __init__(self, *, executor: Optional[ThreadPoolExecutor] = None) -> None:
        self.executor = executor or ThreadPoolExecutor()

    def __call__(self, blocking) -> Callable[..., Any]:
        @wraps(blocking)
        async def wrapper(*args, **kwargs) -> Any:

            return await asyncio.get_event_loop().run_in_executor(
                self.executor, partial(blocking, *args, **kwargs)
            )

        return wrapper
