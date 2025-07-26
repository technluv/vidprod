#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Create fixtures directory
const fixturesDir = path.join(__dirname, 'videos');
if (!fs.existsSync(fixturesDir)) {
  fs.mkdirSync(fixturesDir, { recursive: true });
}

// Generate test video files of different sizes
const generateTestFile = (filename, sizeInMB) => {
  const filePath = path.join(fixturesDir, filename);
  const sizeInBytes = sizeInMB * 1024 * 1024;
  
  // Create a buffer with video-like data pattern
  const buffer = Buffer.alloc(sizeInBytes);
  
  // Add some basic MP4 header bytes (simplified)
  const mp4Header = Buffer.from([
    0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70, // ftyp box
    0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
    0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
    0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31
  ]);
  
  mp4Header.copy(buffer);
  
  // Fill rest with video-like data
  for (let i = mp4Header.length; i < sizeInBytes; i += 4) {
    buffer.writeUInt32BE(Math.floor(Math.random() * 0xFFFFFFFF), i);
  }
  
  fs.writeFileSync(filePath, buffer);
  console.log(`Created ${filename} (${sizeInMB}MB)`);
};

// Generate test files
console.log('Generating test video files...');

// Small files (< 5MB)
generateTestFile('sample-small.mp4', 1);
generateTestFile('test-video.mp4', 2);
generateTestFile('test1.mp4', 1);
generateTestFile('test2.mp4', 1);
generateTestFile('test3.mp4', 1);

// Medium files (5-50MB)
generateTestFile('sample-medium.mp4', 25);
generateTestFile('chunked-test.mp4', 30);
generateTestFile('progress-test.mp4', 20);
generateTestFile('resume-test.mp4', 35);

// Large files (> 50MB)
generateTestFile('sample-large.mp4', 100);
generateTestFile('large-video.mp4', 150);

// Generate concurrent test files
for (let i = 0; i < 10; i++) {
  generateTestFile(`test-${i}.mp4`, 2);
  generateTestFile(`rapid-${i}.mp4`, 1);
  generateTestFile(`concurrent-${i}.mp4`, 3);
}

// Performance test files
for (let i = 0; i < 20; i++) {
  generateTestFile(`perf-${i}.mp4`, 1);
  generateTestFile(`memory-${i}.mp4`, 0.5);
}

// Stress test files
generateTestFile('refresh-test.mp4', 10);
for (let i = 0; i < 9; i++) {
  generateTestFile(`fail-test-${i}.mp4`, 2);
}

// Mixed size files
generateTestFile('small-1.mp4', 1);
generateTestFile('small-2.mp4', 1);
generateTestFile('medium-1.mp4', 50);
generateTestFile('medium-2.mp4', 50);
generateTestFile('large-1.mp4', 200);

// Create an invalid file for testing
const invalidFilePath = path.join(fixturesDir, '../invalid-file.txt');
fs.writeFileSync(invalidFilePath, 'This is not a video file');
console.log('Created invalid-file.txt');

console.log('\\nTest video generation complete!');
console.log(`Total files created: ${fs.readdirSync(fixturesDir).length + 1}`);

// Calculate total size
const totalSize = fs.readdirSync(fixturesDir)
  .map(file => fs.statSync(path.join(fixturesDir, file)).size)
  .reduce((a, b) => a + b, 0);

console.log(`Total size: ${(totalSize / 1024 / 1024).toFixed(2)}MB`);