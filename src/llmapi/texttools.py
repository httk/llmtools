import re

def get_repeating_pattern(s):
    i = (s+s).find(s, 1, -1)
    return None if i == -1 else s[:i]

def get_partially_repeating_pattern(s, max_pattern_length=None):
    n = len(s)
    if max_pattern_length is None or max_pattern_length > n // 2:
        max_pattern_length = n // 2

    for i in range(1, max_pattern_length + 1):
        pattern = s[:i]
        multiplier = (n + i - 1) // i
        repeated_pattern = pattern * multiplier
        if s in repeated_pattern:
            return pattern
    return None

def split_markdown_by_headers(markdown_text, level=1):
    header_regex = rf'(^#{{1,{level}}}\s.*?$)'

    sections = re.split(header_regex, markdown_text, flags=re.MULTILINE)

    combined_sections = []
    for i in range(1, len(sections), 2):
        header = sections[i]
        content = sections[i+1] if i+1 < len(sections) else ''
        combined_sections.append(header + content)

    if sections[0].strip():
        combined_sections.insert(0, sections[0])

    return combined_sections

def split_markdown_by_paragraph(markdown_text):
    return markdown_text.split("\n\n")
    
