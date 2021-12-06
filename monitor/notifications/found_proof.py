from monitor.database import session
from monitor.database.queries import get_proofs_found
from monitor.format import *
from monitor.notifications.notification import Notification


class FoundProofNotification(Notification):
    last_proofs_found: int = None

    def condition(self) -> bool:
        with session() as db_session:
            proofs_found = get_proofs_found(db_session)
        if proofs_found is not None and self.last_proofs_found is not None and proofs_found > self.last_proofs_found:
            self.last_proofs_found = proofs_found
            return True
        else:
            self.last_proofs_found = proofs_found
            return False

    def trigger(self) -> None:
        return self.apobj.notify(title='** 🤑 Proof found! 🤑 **',
                                 body="Your farm found a new partial or full proof")
