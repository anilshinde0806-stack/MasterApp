import re

with open('core/templates/jobcard/jobcardEntry.html', 'r', encoding='utf-8') as f:
    content = f.read()
    style_blocks = re.findall(r'<style>(.*?)</style>', content, re.DOTALL)
    
    for i, block in enumerate(style_blocks):
        print(f"Checking Style Block {i+1}")
        # Check for missing semicolons before closing brace
        # This is a bit tricky with nested media queries
        lines = block.split('\n')
        for j, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            if line.endswith('{') or line.endswith('}') or line.endswith(';') or line.startswith('@') or line.startswith('/*'):
                continue
            # If it looks like a property but doesn't end with ;
            if ':' in line and not line.endswith(';'):
                 print(f"Possible missing semicolon at line {j+1} in block {i+1}: {line}")

        # Check for // comments in CSS
        if '//' in block:
            print(f"Found illegal '//' comment in CSS block {i+1}")
