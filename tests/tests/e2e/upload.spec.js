// @ts-check
const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

test.describe('Video Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should display upload interface correctly', async ({ page }) => {
    // Check main elements
    await expect(page.locator('h1')).toContainText('VidProd');
    await expect(page.locator('.upload-area')).toBeVisible();
    await expect(page.locator('#browseButton')).toBeVisible();
    await expect(page.locator('#browseButton')).toContainText('Browse Files');
    
    // Check supported formats message
    await expect(page.locator('.upload-area p')).toContainText('Supported formats: MP4, MOV, AVI, MKV, WebM');
  });

  test('should handle file selection via browse button', async ({ page }) => {
    // Create test file
    const fileName = 'test-video.mp4';
    const filePath = path.join(__dirname, '../../fixtures/videos/', fileName);
    
    // Set up file chooser
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Verify file is selected
    await expect(page.locator('#uploadProgress')).toBeVisible();
    await expect(page.locator('.file-name')).toContainText(fileName);
  });

  test('should handle drag and drop upload', async ({ page }) => {
    const fileName = 'test-video.mp4';
    const filePath = path.join(__dirname, '../../fixtures/videos/', fileName);
    
    // Create DataTransfer and dispatch drag events
    await page.locator('.upload-area').dispatchEvent('drop', {
      dataTransfer: {
        files: [filePath],
        types: ['Files'],
        effectAllowed: 'all'
      }
    });
    
    // Verify upload started
    await expect(page.locator('#uploadProgress')).toBeVisible();
    await expect(page.locator('.file-name')).toContainText(fileName);
  });

  test('should show upload progress', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/videos/test-video.mp4');
    
    // Mock slow upload to see progress
    await page.route('**/api/upload', async route => {
      // Simulate slow upload
      await page.waitForTimeout(1000);
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ 
          id: '123', 
          status: 'completed',
          url: '/videos/123.mp4' 
        })
      });
    });
    
    // Upload file
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Check progress elements
    await expect(page.locator('.progress-bar')).toBeVisible();
    await expect(page.locator('.progress-percent')).toBeVisible();
    await expect(page.locator('.cancel-button')).toBeVisible();
  });

  test('should handle multiple file uploads', async ({ page }) => {
    const files = [
      path.join(__dirname, '../../fixtures/videos/test1.mp4'),
      path.join(__dirname, '../../fixtures/videos/test2.mp4'),
      path.join(__dirname, '../../fixtures/videos/test3.mp4')
    ];
    
    // Upload multiple files
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(files);
    
    // Check queue status
    await expect(page.locator('#queueStatus')).toBeVisible();
    await expect(page.locator('#pendingCount')).toContainText('3');
    
    // Verify all files appear
    for (let i = 0; i < files.length; i++) {
      await expect(page.locator('.progress-item').nth(i)).toBeVisible();
    }
  });

  test('should validate file types', async ({ page }) => {
    const invalidFile = path.join(__dirname, '../../fixtures/invalid-file.txt');
    
    // Try to upload invalid file
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(invalidFile);
    
    // Check for error message
    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('Invalid file type');
  });

  test('should handle upload cancellation', async ({ page }) => {
    const filePath = path.join(__dirname, '../../fixtures/videos/large-video.mp4');
    
    // Start upload
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Wait for upload to start
    await expect(page.locator('.progress-item')).toBeVisible();
    
    // Cancel upload
    await page.click('.cancel-button');
    
    // Verify cancellation
    await expect(page.locator('.progress-item')).not.toBeVisible();
    await expect(page.locator('#failedCount')).toContainText('1');
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Mock network error
    await page.route('**/api/upload', route => {
      route.abort('failed');
    });
    
    // Try to upload
    const filePath = path.join(__dirname, '../../fixtures/videos/test-video.mp4');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Check error handling
    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('Upload failed');
    await expect(page.locator('#failedCount')).toContainText('1');
  });

  test('should display completed uploads', async ({ page }) => {
    // Mock successful upload
    await page.route('**/api/upload', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          id: '123',
          status: 'completed',
          url: '/videos/123.mp4',
          thumbnail: '/thumbnails/123.jpg'
        })
      });
    });
    
    // Upload file
    const filePath = path.join(__dirname, '../../fixtures/videos/test-video.mp4');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Wait for completion
    await expect(page.locator('#completedUploads')).toBeVisible();
    await expect(page.locator('#completedCount')).toContainText('1');
    await expect(page.locator('.completed-item')).toBeVisible();
  });

  test('should handle chunked upload for large files', async ({ page }) => {
    const largeFilePath = path.join(__dirname, '../../fixtures/videos/large-video.mp4');
    
    let chunkCount = 0;
    await page.route('**/api/upload/chunk', route => {
      chunkCount++;
      route.fulfill({
        status: 200,
        body: JSON.stringify({ 
          chunk: chunkCount,
          received: true 
        })
      });
    });
    
    // Upload large file
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(largeFilePath);
    
    // Verify chunked upload
    await page.waitForTimeout(2000); // Wait for chunks
    expect(chunkCount).toBeGreaterThan(1);
  });
});

test.describe('Upload Progress Tracking', () => {
  test('should calculate and display upload speed', async ({ page }) => {
    await page.goto('/');
    
    // Mock slow upload
    await page.route('**/api/upload', async route => {
      await page.waitForTimeout(2000);
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ status: 'completed' })
      });
    });
    
    // Upload file
    const filePath = path.join(__dirname, '../../fixtures/videos/test-video.mp4');
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    
    // Check speed display
    await expect(page.locator('.progress-speed')).toBeVisible();
    await expect(page.locator('.progress-speed')).toContainText(/\d+(\.\d+)?\s*(KB|MB)\/s/);
  });

  test('should update queue statistics in real-time', async ({ page }) => {
    await page.goto('/');
    
    const files = [
      path.join(__dirname, '../../fixtures/videos/test1.mp4'),
      path.join(__dirname, '../../fixtures/videos/test2.mp4')
    ];
    
    // Upload multiple files
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('#browseButton');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(files);
    
    // Check initial state
    await expect(page.locator('#pendingCount')).toContainText('2');
    await expect(page.locator('#uploadingCount')).toContainText('0');
    
    // Wait for upload to start
    await page.waitForTimeout(500);
    await expect(page.locator('#uploadingCount')).not.toContainText('0');
  });
});

test.describe('Accessibility', () => {
  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');
    
    // Tab to browse button
    await page.keyboard.press('Tab');
    await expect(page.locator('#browseButton')).toBeFocused();
    
    // Activate with Enter
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.keyboard.press('Enter');
    const fileChooser = await fileChooserPromise;
    expect(fileChooser).toBeTruthy();
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/');
    
    // Check ARIA labels
    await expect(page.locator('.upload-area')).toHaveAttribute('role', 'button');
    await expect(page.locator('.upload-area')).toHaveAttribute('aria-label', /upload/i);
    await expect(page.locator('.cancel-button')).toHaveAttribute('aria-label', 'Cancel upload');
  });

  test('should announce upload status to screen readers', async ({ page }) => {
    await page.goto('/');
    
    // Check for live regions
    await expect(page.locator('[aria-live="polite"]')).toBeAttached();
    await expect(page.locator('[role="status"]')).toBeAttached();
  });
});