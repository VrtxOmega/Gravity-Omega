import os

files = ['renderer/index.html', 'renderer/app.js', 'renderer/analyzer.js']

for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    
    # Just do a literal string replace of the known corrupted strings
    content = content.replace('<span class="omega-serif">Ic</span>', '<span class="omega-serif">Ω</span>')
    content = content.replace('Î©', 'Ω')
    
    # Try using re again
    import re
    content = re.sub(r'<span class="omega-serif">[^<]*</span>', '<span class="omega-serif">Ω</span>', content)

    with open(f, 'w', encoding='utf-8') as fp:
        fp.write(content)
    
    print(f"Fixed {f}")
