from PySide6.QtCore import QObject, Signal


class FakeHotkey(QObject):
    triggered = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.registered: list[str] = []
        self.register_result = True
        self.unregistered = 0

    def register(self, text: str) -> bool:
        self.registered.append(text)
        return self.register_result

    def unregister(self) -> None:
        self.unregistered += 1
