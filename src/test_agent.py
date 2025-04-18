import tempfile
import os
from unittest.mock import AsyncMock, patch

import pytest
import playwright.async_api
from telegram import Bot

from agent import dump_page_debug_info_on_exception
from telegram_bot import TelegramNotifier


@pytest.mark.asyncio
async def test_dump_page_debug_info_on_exception_sends_debug_images():

    # Create a real temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a real browser context with a page
        async with playwright.async_api.async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            # Load some real content
            await page.set_content("<html><body><h1>Test Page</h1></body></html>")

            # Create real TelegramNotifier but mock token loading
            with patch.object(
                TelegramNotifier, "_load_telegram_token", return_value="fake_token"
            ):
                # Mock the Bot.send_photo method
                mock_send_photo = AsyncMock()
                with patch.object(Bot, "send_photo", mock_send_photo):
                    try:
                        # Create the context manager with our temp path
                        async with dump_page_debug_info_on_exception(
                            context, debug_folder=tmp_dir
                        ):
                            raise Exception("Test exception")
                    except Exception:
                        pass

                    # Verify debug files were created
                    assert os.path.exists(f"{tmp_dir}/debug.html")
                    debug_image_path = f"{tmp_dir}/page_0.png"
                    assert os.path.exists(debug_image_path)

                    # Verify send_photo was called with correct args
                    mock_send_photo.assert_called_once()
                    call_args = mock_send_photo.call_args[1]
                    assert call_args["chat_id"] == 1182153  # Owner's ID

                    # Verify photo content matches
                    with open(debug_image_path, "rb") as f:
                        expected_content = f.read()
                    actual_content = call_args["photo"].read()
                    assert actual_content == expected_content

            await browser.close()
