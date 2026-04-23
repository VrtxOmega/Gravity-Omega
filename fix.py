import sys

files = ['renderer/index.html', 'renderer/app.js', 'renderer/analyzer.js']

for f in files:
    with open(f, 'rb') as fp:
        content_bytes = fp.read()
    
    # Let's try decoding as cp1252 or utf-8
    try:
        content = content_bytes.decode('utf-8')
    except:
        content = content_bytes.decode('cp1252')
        
    import re
    # We will replace <span class="omega-serif">...</span> with <span class="omega-serif">Ω</span>
    new_content = re.sub(r'<span class="omega-serif">.*?</span>', '<span class="omega-serif">Ω</span>', content)
    
    with open(f, 'w', encoding='utf-8') as fp:
        fp.write(new_content)
    
    print(f + ' fixed via python')
