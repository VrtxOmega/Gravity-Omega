const fs = require('fs');

const reporterHtml = fs.readFileSync('c:/Veritas_Lab/veritas_reporter/veritas_reporter/templates/index.html', 'utf8');
const styleMatch = reporterHtml.match(/<style>([\s\S]*?)<\/style>/);

if (styleMatch) {
    let styles = styleMatch[1];
    
    // Strip global rule that might break the IDE
    styles = styles.replace(/\*,\*::before,\*::after\{box-sizing:border-box;margin:0;padding:0\}/g, '');
    styles = styles.replace(/html,body\{height:100%\}/g, '');
    styles = styles.replace(/body\{[^\}]+\}/g, '');
    styles = styles.replace(/::-webkit-scrollbar[^\}]+\}/g, '');
    styles = styles.replace(/button\{[^\}]+\}/g, '');

    // Add prefix to ID selectors so they are scoped to our analyzer
    styles = '\n\n/* ── VERITAS REPORTER VIEW ── */\n' + styles;
    
    // Append standard marked.js markdown styles
    styles += `
/* ── RAW MARKDOWN VIEWER ── */
#markdown-viewer {
  padding: 40px;
  max-width: 900px;
  margin: 0 auto;
  font-family: 'Share Tech Mono', 'JetBrains Mono', Consolas, monospace;
  font-size: 14px;
  line-height: 1.7;
  color: var(--white, #F5EDD6);
  background: var(--black, #0A0A0C);
  overflow-y: auto;
  height: 100%;
}
#markdown-viewer h1, #markdown-viewer h2, #markdown-viewer h3, 
#markdown-viewer h4, #markdown-viewer h5, #markdown-viewer h6 {
  color: var(--gold, #D4AF37);
  font-family: 'Rajdhani', sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  margin-top: 2em;
  margin-bottom: 1em;
  letter-spacing: 2px;
}
#markdown-viewer h1 { font-size: 2em; border-bottom: 1px solid var(--gold-border, #2a1f08); padding-bottom: 0.5em; }
#markdown-viewer h2 { font-size: 1.5em; }
#markdown-viewer a { color: var(--gold-bright, #F0C040); text-decoration: none; }
#markdown-viewer a:hover { text-decoration: underline; }
#markdown-viewer p { margin-bottom: 1.5em; }
#markdown-viewer ul, #markdown-viewer ol { margin-bottom: 1.5em; padding-left: 2em; }
#markdown-viewer li { margin-bottom: 0.5em; }
#markdown-viewer blockquote {
  border-left: 3px solid var(--gold, #D4AF37);
  background: var(--black2, #13131a);
  padding: 10px 20px;
  margin: 1.5em 0;
  color: var(--gold-dim, #8B6B20);
  font-style: italic;
}
#markdown-viewer hr {
  border: 0;
  border-bottom: 1px solid var(--gold, #D4AF37);
  opacity: 0.5;
  margin: 2em 0;
}
#markdown-viewer code {
  font-family: 'JetBrains Mono', monospace;
  background: rgba(201,168,76, 0.1);
  padding: 2px 4px;
  color: var(--gold, #D4AF37);
}
#markdown-viewer pre {
  background: var(--black2, #13131a);
  border: 1px solid var(--gold-border, #2a1f08);
  padding: 15px;
  overflow-x: auto;
  margin-bottom: 1.5em;
}
#markdown-viewer pre code {
  background: transparent;
  padding: 0;
  color: #c8c8b4;
}
`;

    fs.appendFileSync('c:/Veritas_Lab/gravity-omega-v2/renderer/styles/omega.css', styles);
    console.log('Styles updated.');
} else {
    console.error('Could not parse styles');
}
