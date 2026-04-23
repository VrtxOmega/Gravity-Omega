import sys
import os

files = [
    'c:/Veritas_Lab/gravity-omega-v2/renderer/index.html',
    'c:/Veritas_Lab/gravity-omega-v2/renderer/app.js',
    'c:/Veritas_Lab/gravity-omega-v2/renderer/analyzer.js'
]

for filepath in files:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Avoid double replacing
        content = content.replace('<span class="omega-serif">Ω</span>', 'Ω')
        content = content.replace('Ω', '<span class="omega-serif">Ω</span>')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Replaced in {filepath}")
