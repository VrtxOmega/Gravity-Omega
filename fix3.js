const fs = require('fs');
const files = ['renderer/index.html', 'renderer/app.js', 'renderer/analyzer.js'];

files.forEach(f => {
    let content = fs.readFileSync(f, 'utf8');
    
    // Explicitly replace the exact string
    content = content.replace(/<span class="omega-serif">Ic<\/span>/g, '<span class="omega-serif">Ω</span>');
    // Also use the wildcard just in case
    content = content.replace(/<span class="omega-serif">.*?<\/span>/g, '<span class="omega-serif">Ω</span>');
    
    fs.writeFileSync(f, content, 'utf8');
    console.log(f + ' fixed via node');
});
