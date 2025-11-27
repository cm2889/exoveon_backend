import asyncio 
import math 
import time
from pathlib import Path 
from typing import List, Tuple 
from browser_use import Browser
from agent.ai_agent import analyze_page_and_report
from django.conf import settings


MINIMUM_SCREENSHOTS = 1
MAXIMUM_SCREENSHOTS = 2

# Save into Django MEDIA_ROOT/agent when Django is configured; else fallback to ./media/agent
try:
    media_root_path = Path(settings.MEDIA_ROOT)
except Exception:
    # Fallback for scripts/tests run outside Django context
    media_root_path = (Path.cwd() / 'media').resolve()

OUTPUT_DIR = media_root_path / 'agent'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def url_normalize(url: str):
    if not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url

    if not url.startswith("https://www."):
        url = "https://www." + url[len("https://"):]
    return url

async def screenshot_agent(prompt: str, url: str, n: int = 2) -> Tuple[List[Path], str]:
    """
    Capture screenshots of a webpage with scrolling and analyze using LLM.
    
    Args:
        prompt: User's analysis prompt
        url: Website URL to analyze
        n: Number of screenshots (1-2)
    
    Returns:
        Tuple of (list of screenshot paths, analysis report)
    """
    # Ensure n is within bounds
    n = max(MINIMUM_SCREENSHOTS, min(n, MAXIMUM_SCREENSHOTS))
    url = url_normalize(url) 
    image_paths = []
    
    browser = None
    try:
        # Initialize browser session
        browser = Browser()
        await browser.start()
        
        # Navigate to the URL
        await browser.navigate_to(url)
        
        # Wait for page to fully load
        await asyncio.sleep(4)
        
        # Get the Playwright page object from browser session
        page = await browser.must_get_current_page()
        
        # Extra wait for network to settle (best-effort; ignore if not supported)
        try:
            await page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass
        
        # Get page dimensions using Playwright API
        viewport_height = await page.evaluate('() => window.innerHeight')
        total_height = await page.evaluate('() => document.body.scrollHeight')
        # Coerce to ints to avoid type issues from unexpected returns
        try:
            viewport_height = int(viewport_height)
        except Exception:
            viewport_height = 0
        try:
            total_height = int(total_height)
        except Exception:
            total_height = 0
        if viewport_height <= 0:
            # Fallback to a reasonable default viewport height
            viewport_height = 900
        if total_height <= 0:
            # If unknown, assume one viewport height
            total_height = viewport_height
        
        # Calculate how many screenshots we need
        # Ensure we don't divide strings and we take at least 1 screenshot
        num_screenshots = max(1, min(n, math.ceil(total_height / viewport_height)))
        
        if num_screenshots == 1:
            # Ensure we are at the top and take a full-page screenshot
            try:
                await page.evaluate('() => window.scrollTo(0, 0)')
            except Exception:
                pass
            timestamp = int(time.time() * 1000)
            screenshot_path = OUTPUT_DIR / f'screenshot_{timestamp}_full.png'
            
            # Use BrowserSession API to take screenshot; write bytes explicitly to ensure file exists
            try:
                data = await browser.take_screenshot(path=None, full_page=True)
            except Exception:
                data = await browser.take_screenshot(path=None, full_page=False)
            screenshot_path.write_bytes(data)
            image_paths.append(screenshot_path)
        
        else:
            # Take multiple screenshots with scrolling (no gap)
            for i in range(num_screenshots):
                # Calculate scroll position
                scroll_position = i * viewport_height
                
                # Scroll to position using Playwright API
                await page.evaluate(f'() => window.scrollTo(0, {scroll_position})')
                
                # Wait for content to load after scroll
                await asyncio.sleep(2)
                
                # Take screenshot
                timestamp = int(time.time() * 1000)
                screenshot_path = OUTPUT_DIR / f'screenshot_{timestamp}_{i+1}.png'
                # Capture current viewport and write bytes to file
                data = await browser.take_screenshot(path=None, full_page=False)
                screenshot_path.write_bytes(data)
                image_paths.append(screenshot_path)
        
        # Close browser
        await browser.stop()
        
        # Analyze screenshots with LLM (do not block saving screenshots on failure)
        persona_note = prompt if prompt else "Analyze this website for UX/UI issues and improvements"
        analysis_report = ""
        try:
            analysis_report = analyze_page_and_report(
                image_paths=image_paths,
                page_url=url,
                persona_note=persona_note,
                do_polish=True
            )
        except Exception as analysis_err:
            # Keep screenshots; return a fallback message instead of raising
            analysis_report = f"Analysis unavailable: {analysis_err}"
        
        # Return absolute paths so downstream open() works regardless of cwd
        return [p.resolve() for p in image_paths], analysis_report
    
    except Exception as e:
        # Ensure browser is closed even on error
        if browser:
            try:
                await browser.stop()
            except Exception:
                pass
        # Do NOT delete screenshots if any were taken; surface error to caller
        raise Exception(f"Screenshot agent error: {str(e)}")

  
  
   
    
