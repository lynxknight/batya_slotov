import dataclasses
import logging
from playwright.async_api import Page, FrameLocator, expect

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Card:
    number: str
    expiry: str  # Expect format like "MM/YY" or "MMYY"
    cvc: str

    @classmethod
    def from_string(cls, s: str) -> "Card":
        parts = s.split("@")
        if len(parts) != 3:
            raise ValueError("Invalid card string format. Expected 'number@expiry@cvc'")
        # Basic validation could be added here
        logger.info(f"Creating card ending with: {parts[0][-4:]}")
        return cls(number=parts[0], expiry=parts[1], cvc=parts[2])


# Removed the old fill_stripe_element function as the logic is integrated below


async def process_payment(page: Page, card: Card, dry_run: bool = False) -> bool:
    """
    Fills Stripe payment details within iframes and submits the form.

    Args:
        page: Playwright Page object.
        card: Card object with payment details.
        dry_run: If True, fills the form but does not click submit and pauses.

    Returns:
        True if submission was attempted (or dry run completed), False otherwise.

    Raises:
        Exception: If any step fails significantly (e.g., element not found).
    """
    logger.info("Starting payment processing...")
    try:
        logger.info("Locating card number frame...")
        card_number_frame: FrameLocator = page.frame_locator(
            'iframe[title="Secure card number input frame"]'
        )
        card_number_input = card_number_frame.locator(
            'input[data-elements-stable-field-name="cardNumber"]'
        )
        await expect(card_number_input).to_be_visible(timeout=1000)
        logger.info("Filling card number...")
        await card_number_input.fill(card.number)
        logger.info(f"Filled card number ending with: {card.number[-4:]}")

        logger.info("Locating expiry date frame...")
        expiry_frame: FrameLocator = page.frame_locator(
            'iframe[title="Secure expiration date input frame"]'
        )
        expiry_input = expiry_frame.locator(
            'input[data-elements-stable-field-name="cardExpiry"]'
        )
        await expect(expiry_input).to_be_visible(timeout=1000)
        logger.info("Filling expiry date...")
        await expiry_input.fill(card.expiry)
        logger.info("Filled expiry date.")

        logger.info("Locating CVC frame...")
        cvc_frame: FrameLocator = page.frame_locator(
            'iframe[title="Secure CVC input frame"]'
        )
        cvc_input = cvc_frame.locator(
            'input[data-elements-stable-field-name="cardCvc"]'
        )
        await expect(cvc_input).to_be_visible(timeout=1000)
        logger.info("Filling CVC...")
        await cvc_input.fill(card.cvc)
        logger.info("Filled CVC.")

        logger.info("Successfully filled all card details.")

        submit_button_selector = "#cs-stripe-elements-submit-button"
        submit_button = page.locator(submit_button_selector)

        if dry_run:
            logger.info("Dry run enabled. Skipping submission.")
            # Ensure the submit button is enabled after filling details (Stripe often enables it)
            try:
                await expect(submit_button).to_be_enabled(timeout=1000)
                logger.info(
                    "Submit button appears enabled (as expected after filling fields)."
                )
            except Exception:
                logger.warning("Submit button did not become enabled within timeout.")
            # pause() is useful for interactive debugging but should generally
            # be removed or conditionalized for automated runs.
            logger.info(
                "Pausing script for inspection (dry run). Close the inspector to continue/end."
            )
            await page.pause()
            logger.info("Resuming after pause (if inspector closed).")
            return True  # Indicate dry run completed section

        # Wait for the button to be enabled before clicking
        logger.info(
            f"Waiting for submit button '{submit_button_selector}' to be enabled..."
        )
        await expect(submit_button).to_be_enabled(timeout=10000)  # Wait up to 10s

        logger.info("Clicking submit button...")
        await submit_button.click()
        logger.info("Submit button clicked.")
        return True
    except Exception as e:
        logger.error(f"Error during payment processing: {e}", exc_info=True)
        # Re-raise the exception to signal failure to the caller
        raise
