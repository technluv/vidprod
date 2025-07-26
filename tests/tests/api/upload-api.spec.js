// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const axios = require('axios');

const API_URL = process.env.API_URL || 'http://localhost:8000/api';

test.describe('Upload API Tests', () => {
  let authToken;

  test.beforeAll(async () => {
    // Get auth token if needed
    try {
      const response = await axios.post(`${API_URL}/auth/login`, {
        email: process.env.TEST_USER_EMAIL,
        password: process.env.TEST_USER_PASSWORD
      });
      authToken = response.data.token;
    } catch (error) {
      console.log('No auth required or failed to authenticate');
    }
  });

  test('should accept video upload via multipart form', async ({ request }) => {
    const filePath = path.join(__dirname, '../../fixtures/videos/test-api.mp4');
    const fileBuffer = fs.readFileSync(filePath);
    
    const response = await request.post(`${API_URL}/upload`, {
      multipart: {
        file: {
          name: 'test-api.mp4',
          mimeType: 'video/mp4',
          buffer: fileBuffer
        },
        metadata: JSON.stringify({
          title: 'Test Video',
          description: 'API test video'
        })
      },
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('processing');
  });

  test('should validate file size limits', async ({ request }) => {
    // Create a large buffer (over limit)
    const largeBuffer = Buffer.alloc(200 * 1024 * 1024); // 200MB
    
    const response = await request.post(`${API_URL}/upload`, {
      multipart: {
        file: {
          name: 'large-file.mp4',
          mimeType: 'video/mp4',
          buffer: largeBuffer
        }
      },
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    expect(response.status()).toBe(413); // Payload Too Large
    const error = await response.json();
    expect(error.message).toContain('File size exceeds limit');
  });

  test('should reject invalid file types', async ({ request }) => {
    const response = await request.post(`${API_URL}/upload`, {
      multipart: {
        file: {
          name: 'document.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from('PDF content')
        }
      },
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    expect(response.status()).toBe(400);
    const error = await response.json();
    expect(error.message).toContain('Invalid file type');
  });

  test('should support chunked upload', async ({ request }) => {
    const filePath = path.join(__dirname, '../../fixtures/videos/chunked-test.mp4');
    const fileBuffer = fs.readFileSync(filePath);
    const chunkSize = 5 * 1024 * 1024; // 5MB chunks
    const totalChunks = Math.ceil(fileBuffer.length / chunkSize);
    
    // Initialize chunked upload
    const initResponse = await request.post(`${API_URL}/upload/init`, {
      data: {
        filename: 'chunked-test.mp4',
        fileSize: fileBuffer.length,
        chunkSize: chunkSize,
        totalChunks: totalChunks
      },
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    expect(initResponse.ok()).toBeTruthy();
    const { uploadId } = await initResponse.json();

    // Upload chunks
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, fileBuffer.length);
      const chunk = fileBuffer.slice(start, end);

      const chunkResponse = await request.post(`${API_URL}/upload/chunk`, {
        multipart: {
          chunk: {
            name: `chunk-${i}`,
            mimeType: 'application/octet-stream',
            buffer: chunk
          },
          uploadId: uploadId,
          chunkIndex: i.toString(),
          totalChunks: totalChunks.toString()
        },
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      });

      expect(chunkResponse.ok()).toBeTruthy();
    }

    // Complete upload
    const completeResponse = await request.post(`${API_URL}/upload/complete`, {
      data: { uploadId },
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    expect(completeResponse.ok()).toBeTruthy();
    const result = await completeResponse.json();
    expect(result.status).toBe('processing');
  });

  test('should return upload progress', async ({ request }) => {
    // Start an upload
    const filePath = path.join(__dirname, '../../fixtures/videos/progress-test.mp4');
    const fileBuffer = fs.readFileSync(filePath);
    
    const uploadResponse = await request.post(`${API_URL}/upload`, {
      multipart: {
        file: {
          name: 'progress-test.mp4',
          mimeType: 'video/mp4',
          buffer: fileBuffer
        }
      },
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    const { id } = await uploadResponse.json();

    // Check progress
    const progressResponse = await request.get(`${API_URL}/upload/${id}/progress`, {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
    });

    expect(progressResponse.ok()).toBeTruthy();
    const progress = await progressResponse.json();
    expect(progress).toHaveProperty('percentage');
    expect(progress).toHaveProperty('status');
    expect(progress.percentage).toBeGreaterThanOrEqual(0);
    expect(progress.percentage).toBeLessThanOrEqual(100);
  });

  test('should handle concurrent uploads from same user', async ({ request }) => {
    const uploadPromises = [];
    
    for (let i = 0; i < 5; i++) {
      const filePath = path.join(__dirname, '../../fixtures/videos/', `concurrent-${i}.mp4`);
      const fileBuffer = fs.readFileSync(filePath);
      
      const promise = request.post(`${API_URL}/upload`, {
        multipart: {
          file: {
            name: `concurrent-${i}.mp4`,
            mimeType: 'video/mp4',
            buffer: fileBuffer
          }
        },
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      });
      
      uploadPromises.push(promise);
    }

    const responses = await Promise.all(uploadPromises);
    
    // All uploads should succeed
    responses.forEach(response => {
      expect(response.ok()).toBeTruthy();
    });

    // Each should have unique ID
    const ids = await Promise.all(responses.map(r => r.json().then(d => d.id)));
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(5);
  });

  test('should support resume after interruption', async ({ request }) => {
    const filePath = path.join(__dirname, '../../fixtures/videos/resume-test.mp4');
    const fileBuffer = fs.readFileSync(filePath);
    const chunkSize = 5 * 1024 * 1024;
    const totalChunks = Math.ceil(fileBuffer.length / chunkSize);
    
    // Initialize upload
    const initResponse = await request.post(`${API_URL}/upload/init`, {
      data: {
        filename: 'resume-test.mp4',
        fileSize: fileBuffer.length,
        chunkSize: chunkSize,
        totalChunks: totalChunks
      }
    });

    const { uploadId } = await initResponse.json();

    // Upload first 2 chunks
    for (let i = 0; i < 2; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, fileBuffer.length);
      const chunk = fileBuffer.slice(start, end);

      await request.post(`${API_URL}/upload/chunk`, {
        multipart: {
          chunk: {
            name: `chunk-${i}`,
            mimeType: 'application/octet-stream',
            buffer: chunk
          },
          uploadId: uploadId,
          chunkIndex: i.toString()
        }
      });
    }

    // Check resume status
    const resumeResponse = await request.get(`${API_URL}/upload/${uploadId}/resume`);
    expect(resumeResponse.ok()).toBeTruthy();
    
    const resumeData = await resumeResponse.json();
    expect(resumeData.uploadedChunks).toEqual([0, 1]);
    expect(resumeData.nextChunk).toBe(2);

    // Resume from chunk 2
    for (let i = 2; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, fileBuffer.length);
      const chunk = fileBuffer.slice(start, end);

      const chunkResponse = await request.post(`${API_URL}/upload/chunk`, {
        multipart: {
          chunk: {
            name: `chunk-${i}`,
            mimeType: 'application/octet-stream',
            buffer: chunk
          },
          uploadId: uploadId,
          chunkIndex: i.toString()
        }
      });

      expect(chunkResponse.ok()).toBeTruthy();
    }

    // Complete upload
    const completeResponse = await request.post(`${API_URL}/upload/complete`, {
      data: { uploadId }
    });

    expect(completeResponse.ok()).toBeTruthy();
  });

  test('should handle rate limiting gracefully', async ({ request }) => {
    const requests = [];
    
    // Send 20 requests rapidly
    for (let i = 0; i < 20; i++) {
      const promise = request.post(`${API_URL}/upload`, {
        multipart: {
          file: {
            name: `rate-limit-${i}.mp4`,
            mimeType: 'video/mp4',
            buffer: Buffer.from('small video content')
          }
        }
      });
      requests.push(promise);
    }

    const responses = await Promise.all(requests);
    
    // Some requests should be rate limited
    const rateLimited = responses.filter(r => r.status() === 429);
    expect(rateLimited.length).toBeGreaterThan(0);

    // Rate limit response should include retry-after header
    if (rateLimited.length > 0) {
      const retryAfter = rateLimited[0].headers()['retry-after'];
      expect(retryAfter).toBeTruthy();
    }
  });
});