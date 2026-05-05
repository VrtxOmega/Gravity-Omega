const { createWorker } = require('tesseract.js');
const fs = require('fs');
const path = require('path');
const { app } = require('electron');

class OCRHandler {
    constructor() {
        this.worker = null;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;

        try {
            this.worker = await createWorker('eng');
            await this.worker.load();
            await this.worker.loadLanguage('eng');
            await this.worker.initialize('eng');
            this.initialized = true;
            console.log('[OCR] Tesseract.js initialized successfully');
        } catch (error) {
            console.error('[OCR] Failed to initialize Tesseract.js:', error);
            throw error;
        }
    }

    async extractTextFromImage(imagePath) {
        if (!this.initialized) {
            await this.initialize();
        }

        try {
            const result = await this.worker.recognize(imagePath);
            return result.data.text;
        } catch (error) {
            console.error('[OCR] Text extraction failed:', error);
            throw error;
        }
    }

    async extractTextFromBuffer(imageBuffer, filename) {
        if (!this.initialized) {
            await this.initialize();
        }

        try {
            // Save buffer to temp file
            const tempDir = app.getPath('temp');
            const tempPath = path.join(tempDir, `ocr_temp_${Date.now()}_${filename}`);
            
            // Ensure the buffer is in the correct format
            if (typeof imageBuffer === 'string' && imageBuffer.startsWith('data:')) {
                // Handle base64 data URL
                const base64Data = imageBuffer.split(',')[1];
                const buffer = Buffer.from(base64Data, 'base64');
                await fs.promises.writeFile(tempPath, buffer);
            } else if (Buffer.isBuffer(imageBuffer)) {
                // Handle raw buffer
                await fs.promises.writeFile(tempPath, imageBuffer);
            } else {
                throw new Error('Invalid image buffer format');
            }

            // Perform OCR
            const result = await this.worker.recognize(tempPath);
            
            // Clean up temp file
            await fs.promises.unlink(tempPath);
            
            return result.data.text;
        } catch (error) {
            console.error('[OCR] Text extraction from buffer failed:', error);
            throw error;
        }
    }

    async terminate() {
        if (this.worker) {
            await this.worker.terminate();
            this.worker = null;
            this.initialized = false;
        }
    }
}

module.exports = { OCRHandler };