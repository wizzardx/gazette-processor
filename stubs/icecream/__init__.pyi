from typing import Any, Callable, Optional, overload

class IceCreamDebugger:
    def __init__(
        self,
        prefix: str = ...,
        outputFunction: Optional[Callable[[str], None]] = ...,
        argToStringFunction: Optional[Callable[[Any], str]] = ...,
        includeContext: bool = ...,
        contextAbsPath: bool = ...,
    ) -> None: ...
    @overload
    def __call__(self) -> None: ...
    @overload
    def __call__(self, *args: Any) -> Any: ...
    def enable(self) -> IceCreamDebugger: ...
    def disable(self) -> IceCreamDebugger: ...
    def configureOutput(
        self,
        prefix: Optional[str] = ...,
        outputFunction: Optional[Callable[[str], None]] = ...,
        argToStringFunction: Optional[Callable[[Any], str]] = ...,
        includeContext: Optional[bool] = ...,
        contextAbsPath: Optional[bool] = ...,
    ) -> IceCreamDebugger: ...

ic: IceCreamDebugger

def install() -> None: ...
def uninstall() -> None: ...
def isInstalled() -> bool: ...
def enable() -> None: ...
def disable() -> None: ...
def configureOutput(
    prefix: Optional[str] = ...,
    outputFunction: Optional[Callable[[str], None]] = ...,
    argToStringFunction: Optional[Callable[[Any], str]] = ...,
    includeContext: Optional[bool] = ...,
    contextAbsPath: Optional[bool] = ...,
) -> None: ...
