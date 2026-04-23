const fs = require('fs');
let c = fs.readFileSync('renderer/index.html', 'utf8');
let m = c.match(/<span class="omega-serif">(.*?)<\/span>/);
if (m) {
    console.log("Matched content:", m[1]);
    for (let i = 0; i < m[1].length; i++) {
        console.log(m[1].charCodeAt(i).toString(16));
    }
}
