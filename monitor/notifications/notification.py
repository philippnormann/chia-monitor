import logging

from apprise import Apprise


class Notification:
    apobj: Apprise
    firing: bool = False

    def __init__(self, apobj: Apprise) -> None:
        self.apobj = apobj
        self.log = logging.getLogger(__name__)

    def condition(self) -> bool:
        raise NotImplementedError

    def trigger(self) -> bool:
        raise NotImplementedError

    def recover(self) -> bool:
        return True

    def run(self) -> None:
        if self.condition():
            if not self.firing:
                sent = self.trigger()
                if sent:
                    self.firing = True
        elif self.firing:
            sent = self.recover()
            if sent:
                self.firing = False
