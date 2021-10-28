from monitor.database.queries import get_current_balance, get_last_payment
from monitor.database import async_session
from monitor.format import *
from monitor.notifications.notification import Notification


class PaymentNotification(Notification):
    last_mojos: int = None

    async def condition(self) -> bool:
        async with async_session() as db_session:
            current_mojos = await get_current_balance(db_session)
        if current_mojos is not None and self.last_mojos is not None and current_mojos > self.last_mojos:
            self.last_mojos = current_mojos
            return True
        else:
            self.last_mojos = current_mojos
            return False

    async def trigger(self) -> None:
        async with async_session() as db_session:
            last_payment_mojos = await get_last_payment(db_session)
        return self.apobj.notify(title='** 🤑 Payment received! 🤑 **',
                                 body="Your wallet received a new payment\n" + \
                                     f"🌱 +{last_payment_mojos/1e12:.5f} XCH")
