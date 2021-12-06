from monitor.database import session
from monitor.database.queries import get_current_balance, get_last_payment
from monitor.format import *
from monitor.notifications.notification import Notification


class PaymentNotification(Notification):
    last_mojos: int = None

    def condition(self) -> bool:
        with session() as db_session:
            current_mojos = get_current_balance(db_session)
        if current_mojos is not None and self.last_mojos is not None and current_mojos > self.last_mojos:
            self.last_mojos = current_mojos
            return True
        else:
            self.last_mojos = current_mojos
            return False

    def trigger(self) -> None:
        with session() as db_session:
            last_payment_mojos = get_last_payment(db_session)
        return self.apobj.notify(title='** 🤑 Payment received! 🤑 **',
                                 body="Your wallet received a new payment\n" + \
                                     f"🌱 +{last_payment_mojos/1e12:.5f} XCH")
