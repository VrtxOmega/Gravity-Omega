import re

with open('renderer/index.html', 'rb') as f:
    c = f.read()

m = re.search(b'<span class="omega-serif">(.*?)</span>', c)
if m:
    val = m.group(1)
    print("MATCH:", val)
    print("HEX:", val.hex())
else:
    print("NO MATCH")
