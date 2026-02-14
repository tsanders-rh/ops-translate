import { test } from "@playwright/test";

/**
 * Screenshot capture for README and documentation.
 *
 * Captures key sections of the HTML report for showcasing in the GitHub repo.
 * Screenshots are saved to media/screenshots/
 *
 * Usage: npx playwright test tests/playwright/screenshots.spec.ts --config=playwright-demo.config.ts
 */

test.describe("HTML report screenshots for documentation", () => {
  test.use({
    viewport: { width: 2560, height: 1440 },
    deviceScaleFactor: 1,
  });

  test("capture report screenshots", async ({ page }) => {
    // Navigate to report
    await page.goto("/index.html", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);

    // 1. Executive Summary Tab
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({
      path: "media/screenshots/executive-summary.png",
      fullPage: false,
    });
    console.log("✓ Captured: executive-summary.png");

    // 2. Architecture Tab - Overview
    await page.locator('[data-tab="architecture"]').click();
    await page.waitForTimeout(800);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({
      path: "media/screenshots/architecture-overview.png",
      fullPage: false,
    });
    console.log("✓ Captured: architecture-overview.png");

    // 3. Architecture Tab - Classification Cards
    await page.locator(".card").first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    // Take a clip of just the cards section
    const cardsSection = page.locator(".summary-cards");
    await cardsSection.screenshot({
      path: "media/screenshots/classification-cards.png",
    });
    console.log("✓ Captured: classification-cards.png");

    // 4. Gap Analysis Section
    const firstGapItem = page.locator(".gap-item").first();
    if (await firstGapItem.isVisible()) {
      await firstGapItem.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: "media/screenshots/gap-analysis.png",
        fullPage: false,
      });
      console.log("✓ Captured: gap-analysis.png");
    }

    // 5. Filtered View (PARTIAL components)
    await page.locator(".card").first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await page.locator('.card[data-filter="PARTIAL"]').click();
    await page.waitForTimeout(800);

    // Scroll to show filter indicator and filtered results
    const filterIndicator = page.locator("#filter-indicator");
    await filterIndicator.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: "media/screenshots/filtered-view.png",
      fullPage: false,
    });
    console.log("✓ Captured: filtered-view.png");

    // Clear filter
    await page.locator("#clear-filter").click();
    await page.waitForTimeout(500);

    // 6. Implementation Tab
    await page.locator('[data-tab="implementation"]').click();
    await page.waitForTimeout(800);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({
      path: "media/screenshots/implementation-guide.png",
      fullPage: false,
    });
    console.log("✓ Captured: implementation-guide.png");

    // 7. Decision Interview Tab - Overview
    await page.locator('[data-tab="decisions"]').click();
    await page.waitForTimeout(800);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({
      path: "media/screenshots/decision-interview-overview.png",
      fullPage: false,
    });
    console.log("✓ Captured: decision-interview-overview.png");

    // 8. Decision Interview - Question Pack
    const questionPack = page.locator(".question-pack").first();
    if (await questionPack.isVisible()) {
      await questionPack.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      // Take screenshot of the question pack area
      await page.screenshot({
        path: "media/screenshots/decision-interview-questions.png",
        fullPage: false,
      });
      console.log("✓ Captured: decision-interview-questions.png");
    }

    // 9. Full page screenshot of Executive tab (for overview)
    await page.locator('[data-tab="executive"]').click();
    await page.waitForTimeout(800);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({
      path: "media/screenshots/full-report-executive.png",
      fullPage: true,
    });
    console.log("✓ Captured: full-report-executive.png (full page)");

    console.log("\n✨ All screenshots captured to media/screenshots/\n");
  });
});
