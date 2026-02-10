import { test, expect } from "@playwright/test";

/**
 * Annotated demo with text overlays explaining each section.
 *
 * This test injects overlay elements during recording to provide
 * educational context about the HTML report features.
 */

// Helper function to show annotation overlay
async function showAnnotation(page: any, text: string, duration: number = 2000) {
  await page.evaluate((annotationText) => {
    // Remove any existing annotation
    const existing = document.getElementById('demo-annotation');
    if (existing) {
      existing.remove();
    }

    // Create overlay element
    const overlay = document.createElement('div');
    overlay.id = 'demo-annotation';
    overlay.innerHTML = annotationText;

    // Style the overlay
    Object.assign(overlay.style, {
      position: 'fixed',
      top: '20px',
      left: '50%',
      transform: 'translateX(-50%)',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      padding: '20px 40px',
      borderRadius: '12px',
      fontSize: '24px',
      fontWeight: 'bold',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      zIndex: '10000',
      boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
      maxWidth: '80%',
      textAlign: 'center',
      animation: 'slideInDown 0.5s ease-out',
      border: '2px solid rgba(255,255,255,0.3)',
    });

    // Add animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideInDown {
        from {
          opacity: 0;
          transform: translateX(-50%) translateY(-30px);
        }
        to {
          opacity: 1;
          transform: translateX(-50%) translateY(0);
        }
      }
      @keyframes slideOutUp {
        from {
          opacity: 1;
          transform: translateX(-50%) translateY(0);
        }
        to {
          opacity: 0;
          transform: translateX(-50%) translateY(-30px);
        }
      }
    `;
    document.head.appendChild(style);

    document.body.appendChild(overlay);
  }, text);

  await page.waitForTimeout(duration);

  // Fade out animation
  await page.evaluate(() => {
    const overlay = document.getElementById('demo-annotation');
    if (overlay) {
      overlay.style.animation = 'slideOutUp 0.5s ease-in';
    }
  });

  await page.waitForTimeout(500);

  // Remove overlay
  await page.evaluate(() => {
    const overlay = document.getElementById('demo-annotation');
    if (overlay) {
      overlay.remove();
    }
  });
}

// Helper to highlight an element
async function highlightElement(page: any, selector: string, duration: number = 1500) {
  await page.evaluate((sel) => {
    const element = document.querySelector(sel);
    if (element) {
      const rect = element.getBoundingClientRect();

      // Create highlight overlay
      const highlight = document.createElement('div');
      highlight.id = 'demo-highlight';
      Object.assign(highlight.style, {
        position: 'fixed',
        top: `${rect.top - 5}px`,
        left: `${rect.left - 5}px`,
        width: `${rect.width + 10}px`,
        height: `${rect.height + 10}px`,
        border: '3px solid #667eea',
        borderRadius: '8px',
        pointerEvents: 'none',
        zIndex: '9999',
        boxShadow: '0 0 0 9999px rgba(0,0,0,0.5)',
        animation: 'pulse 1s ease-in-out infinite',
      });

      const style = document.createElement('style');
      style.textContent = `
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `;
      document.head.appendChild(style);

      document.body.appendChild(highlight);
    }
  }, selector);

  await page.waitForTimeout(duration);

  await page.evaluate(() => {
    const highlight = document.getElementById('demo-highlight');
    if (highlight) {
      highlight.remove();
    }
  });
}

test.describe("HTML report annotated demo", () => {
  test.use({
    viewport: { width: 1920, height: 1080 },
  });

  test("annotated: complete walkthrough with explanations", async ({ page }) => {
    test.setTimeout(120000); // 2 minutes for annotated demo
    // Navigate to report
    await page.goto("/index.html", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);

    // Introduction
    await showAnnotation(page, "🎯 ops-translate HTML Report Demo", 2000);
    await page.waitForTimeout(300);

    // Scroll to top and show header
    await page.evaluate(() => window.scrollTo(0, 0));
    await showAnnotation(page, "📊 Translation Status Overview", 1800);
    await page.waitForTimeout(300);

    // Highlight and explain summary cards
    await page.locator(".card").first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    await showAnnotation(page, "📋 Classification Cards<br/><small>Click to filter gaps by level</small>", 2500);
    await highlightElement(page, ".card[data-filter='BLOCKED']", 1500);
    await page.waitForTimeout(500);

    // Click BLOCKED filter
    await showAnnotation(page, "🎯 Filtering: Expert-Guided Components", 2000);
    await page.locator('.card[data-filter="BLOCKED"]').click();
    await page.waitForTimeout(1500);

    // Show filter indicator
    await highlightElement(page, "#filter-indicator", 1500);
    await showAnnotation(page, "✅ Filter Active<br/><small>Only Expert-Guided gaps shown</small>", 2500);
    await page.waitForTimeout(500);

    // Scroll through filtered results
    const blockedItems = page.locator('.gap-item[data-level="BLOCKED"]');
    if ((await blockedItems.count()) > 0) {
      await blockedItems.first().scrollIntoViewIfNeeded();
      await showAnnotation(page, "📝 Gap Details<br/><small>Migration guidance for each component</small>", 2500);
      await highlightElement(page, '.gap-item[data-level="BLOCKED"]', 1500);
    }
    await page.waitForTimeout(500);

    // Clear filter
    await showAnnotation(page, "🔄 Clearing Filter", 2000);
    await page.locator("#clear-filter").scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await page.locator("#clear-filter").click();
    await page.waitForTimeout(1500);

    // Click PARTIAL filter
    await page.locator(".card").first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await showAnnotation(page, "⚠️ Filtering: Partial Translation Components", 2000);
    await page.locator('.card[data-filter="PARTIAL"]').click();
    await page.waitForTimeout(1500);

    // Show partial gaps
    const partialItems = page.locator('.gap-item[data-level="PARTIAL"]');
    if ((await partialItems.count()) > 0) {
      await partialItems.first().scrollIntoViewIfNeeded();
      await showAnnotation(page, "🔧 Partial Components<br/><small>Require manual configuration</small>", 2500);
      await highlightElement(page, '.gap-item[data-level="PARTIAL"]', 1500);
    }
    await page.waitForTimeout(500);

    // Clear filter again
    await showAnnotation(page, "🔄 Show All Gaps", 2000);
    await page.locator("#clear-filter").scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await page.locator("#clear-filter").click();
    await page.waitForTimeout(1000);

    // Scroll to show source files section (optional - skip to save time)
    // await page.evaluate(() => {
    //   const heading = Array.from(document.querySelectorAll('h2'))
    //     .find(h => h.textContent?.includes('Source Files'));
    //   if (heading) {
    //     heading.scrollIntoView({ behavior: 'smooth', block: 'center' });
    //   }
    // });
    // await page.waitForTimeout(800);
    // await showAnnotation(page, "📂 Source Files Analyzed<br/><small>Original VMware automation scripts</small>", 2000);

    // Final message
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await showAnnotation(page, "✨ Interactive HTML Report<br/><small>Filter, review, and export migration insights</small>", 3000);

    await page.waitForTimeout(1000);
  });
});
