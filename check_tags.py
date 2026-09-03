from html.parser import HTMLParser

class TagBalancer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
        self.self_closing = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.self_closing:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.self_closing:
            return
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}> at {self.getpos()}")
            return
        last_tag, pos = self.stack.pop()
        if last_tag != tag:
            self.errors.append(f"Mismatched tag: expected </{last_tag}> (from {pos}), found </{tag}> at {self.getpos()}")

    def check_final(self):
        while self.stack:
            tag, pos = self.stack.pop()
            self.errors.append(f"Unclosed tag <{tag}> at {pos}")

with open('core/templates/jobcard/jobcardEntry.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    content = ""
    line_map = []
    for i, line in enumerate(lines):
        # Remove django tags but keep length for mapping (simple approach: replace with spaces)
        import re
        processed_line = re.sub(r'\{%.*?%\}', lambda m: ' ' * len(m.group()), line, flags=re.DOTALL)
        processed_line = re.sub(r'\{\{.*?\}\}', lambda m: ' ' * len(m.group()), processed_line, flags=re.DOTALL)
        content += processed_line
        for _ in range(len(processed_line)):
            line_map.append(i + 1)
    
    parser = TagBalancer()
    parser.feed(content)
    parser.check_final()
    
    if parser.errors:
        for error in parser.errors:
            print(error)
    else:
        print("All HTML tags are balanced!")
