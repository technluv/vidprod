// @ts-check
const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs').promises;

test.describe('Concurrent Upload Stress Tests', () => {
  test.describe.configure({ mode: 'parallel' });

  test('should handle 10 concurrent uploads', async ({ page }) => {
    await page.goto('/');
    
    // Generate test files
    const files = [];
    for (let i = 0; i < 10; i++) {
      files.push(path.join(__dirname, '../../fixtures/videos/', `test-${i}.mp4`));
    }
    
    // Upload all files at once
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(files);
    
    // Monitor upload progress
    await expect(page.locator('#queueStatus')).toBeVisible();
    await expect(page.locator('#pendingCount')).toContainText('10');
    
    // Wait for all uploads to complete (with timeout)
    await expect(page.locator('#completedCount')).toContainText('10', { timeout: 60000 });
    
    // Verify no failures
    await expect(page.locator('#failedCount')).toContainText('0');
  });

  test('should handle rapid sequential uploads', async ({ page }) => {
    await page.goto('/');
    
    // Upload files rapidly one after another
    for (let i = 0; i < 5; i++) {
      const filePath = path.join(__dirname, '../../fixtures/videos/', `rapid-${i}.mp4`);
      
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.click('#browseButton');
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(filePath);
      
      // Don't wait for completion, immediately upload next
      await page.waitForTimeout(100);
    }
    
    // Verify all uploads are queued
    await expect(page.locator('.progress-item')).toHaveCount(5);
  });

  test('should maintain performance with large queue', async ({ page }) => {
    await page.goto('/');
    
    const startTime = Date.now();
    
    // Upload 20 files
    const files = Array.from({ length: 20 }, (_, i) => 
      path.join(__dirname, '../../fixtures/videos/', `perf-${i}.mp4`)
    );
    
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(files);
    
    // Measure time to queue all files
    await expect(page.locator('#pendingCount')).toContainText('20');
    const queueTime = Date.now() - startTime;
    
    // Queue time should be under 2 seconds
    expect(queueTime).toBeLessThan(2000);
    
    // UI should remain responsive
    await page.click('#browseButton');
    await expect(page.locator('#fileInput')).toBeEnabled();
  });

  test('should handle mixed file sizes concurrently', async ({ page }) => {
    await page.goto('/');
    
    const files = [
      path.join(__dirname, '../../fixtures/videos/small-1.mp4'),  // 1MB
      path.join(__dirname, '../../fixtures/videos/medium-1.mp4'), // 50MB
      path.join(__dirname, '../../fixtures/videos/large-1.mp4'),  // 200MB
      path.join(__dirname, '../../fixtures/videos/small-2.mp4'),  // 1MB
      path.join(__dirname, '../../fixtures/videos/medium-2.mp4'), // 50MB
    ];
    
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(files);
    
    // Verify proper queue management
    await expect(page.locator('#uploadingCount')).not.toContainText('5');
    
    // Should respect concurrent upload limit
    const uploadingCount = await page.locator('#uploadingCount').textContent();
    expect(parseInt(uploadingCount)).toBeLessThanOrEqual(3); // Max 3 concurrent
  });

  test('should recover from partial failures', async ({ page }) => {
    await page.goto('/');
    
    let uploadCount = 0;
    await page.route('**/api/upload', route => {
      uploadCount++;
      // Fail every 3rd upload
      if (uploadCount % 3 === 0) {
        route.abort('failed');
      } else {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ status: 'completed' })
        });
      }
    });
    
    // Upload 9 files
    const files = Array.from({ length: 9 }, (_, i) => 
      path.join(__dirname, '../../fixtures/videos/', `fail-test-${i}.mp4`)
    );
    
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(files);
    
    // Wait for uploads to process
    await page.waitForTimeout(5000);
    
    // Should have 6 successes and 3 failures
    await expect(page.locator('#completedCount')).toContainText('6');
    await expect(page.locator('#failedCount')).toContainText('3');
  });
});

test.describe('Memory and Resource Tests', () => {
  test('should not leak memory during long upload sessions', async ({ page }) => {
    await page.goto('/');
    
    // Monitor memory usage
    const initialMemory = await page.evaluate(() => {
      if (performance.memory) {
        return performance.memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Perform many uploads
    for (let i = 0; i < 20; i++) {
      const filePath = path.join(__dirname, '../../fixtures/videos/', `memory-${i}.mp4`);
      
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.click('#browseButton');
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(filePath);
      
      await page.waitForTimeout(500);
    }
    
    // Check memory after uploads
    const finalMemory = await page.evaluate(() => {
      if (performance.memory) {
        return performance.memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Memory increase should be reasonable (less than 50MB)
    const memoryIncrease = finalMemory - initialMemory;
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
  });

  test('should handle browser refresh during uploads', async ({ page }) => {
    await page.goto('/');
    
    // Start upload
    const filePath = path.join(__dirname, '../../fixtures/videos/refresh-test.mp4');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Wait for upload to start
    await expect(page.locator('.progress-item')).toBeVisible();
    
    // Refresh page
    await page.reload();
    
    // Check if upload state is recovered or properly cleaned up
    await expect(page.locator('.upload-area')).toBeVisible();
    
    // Should either resume or show as failed
    const hasResume = await page.locator('.resume-button').count();
    const hasFailed = await page.locator('#failedCount').textContent();
    
    expect(hasResume > 0 || parseInt(hasFailed) > 0).toBeTruthy();
  });
});