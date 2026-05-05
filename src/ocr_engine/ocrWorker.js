const { createWorker } = require('tesseract.js');

class OCREngine {
  constructor() {
    this.worker = null;
  }

  async init(lang = 'eng') {
    if (!this.worker) {
      this.worker = await createWorker({
        logger: m => console.log('[OCR]', m.progress.toFixed(2), '%'),
      });
      await this.worker.load();
      await this.worker.loadLanguage(lang);
      await this.worker.initialize(lang);
    }
  }

  async extract(imagePath) {
    if (!this.worker) await this.init();

    try {
      const { data: { text } } = await this.worker.recognize(imagePath);
      return text.trim();
    } catch (err) {
      console.error('[OCR] Extraction failed:', err.message);
      return '';
    }
  }

  async destroy() {
    if (this.worker) {
      await this.worker.terminate();
      this.worker = null;
    }
  }
}

module.exports = OCREngine;