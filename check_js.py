import re

with open('core/templates/jobcard/jobcardEntry.html', 'r', encoding='utf-8') as f:
    content = f.read()
    script_blocks = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    
    for i, block in enumerate(script_blocks):
        print(f"Checking Script Block {i+1}")
        # Check for obvious syntax errors like unclosed braces or brackets
        # But wait, Django tags might make this hard.
        
        # Count braces
        open_braces = block.count('{')
        close_braces = block.count('}')
        if open_braces != close_braces:
             print(f"Braces mismatch in block {i+1}: {open_braces} open, {close_braces} close")

        open_brackets = block.count('[')
        close_brackets = block.count(']')
        if open_brackets != close_brackets:
             print(f"Brackets mismatch in block {i+1}: {open_brackets} open, {close_brackets} close")

        open_parens = block.count('(')
        close_parens = block.count(')')
        if open_parens != close_parens:
             print(f"Parentheses mismatch in block {i+1}: {open_parens} open, {close_parens} close")
