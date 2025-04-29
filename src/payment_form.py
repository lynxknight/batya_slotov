import dataclasses
import logging

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Card:
    number: str
    expiry: str
    cvc: str

    @classmethod
    def from_string(cls, s: str) -> "Card":
        parts = s.split("@")
        logger.info(f"Creating card with nuber: {parts[0][:4]}")
        return cls(number=parts[0], expiry=parts[1], cvc=parts[2])


async def fill_stripe_element(page, element_id, value):
    """
    Fill in a Stripe Element iframe with the given value.
    """
    try:
        # Wait for the element to be present
        logger.info(f"Fill stripe element {element_id}")
        await page.wait_for_timeout(100)
        await page.type(f"#{element_id} input", " " + value, delay=100)
    except Exception:
        logger.exception(f"Error filling {element_id}")
        raise


async def process_payment(page, card: Card, dry_run: bool = False) -> bool:
    """
    Process a payment through the Stripe form.

    Args:
        page: Playwright page object
        card: Card to use
    """
    try:
        await page.wait_for_selector("#cs-stripe-elements-card-number")
        await fill_stripe_element(page, "cs-stripe-elements-card-number", card.number)
        await fill_stripe_element(page, "cs-stripe-elements-card-expiry", card.expiry)
        await fill_stripe_element(page, "cs-stripe-elements-card-cvc", card.cvc)
        logger.info("Filled in card details")
        if dry_run:
            logger.info("Dry run, skipping submit")
            return
        await page.click("#cs-stripe-elements-submit-button")
        logger.info("Submit button clicked")
        return True
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        raise
