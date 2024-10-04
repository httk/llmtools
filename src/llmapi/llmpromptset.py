import os, logging

import yaml

from .llmprompt import LlmPrompt
from .texttools import split_markdown_by_headers, split_markdown_by_paragraph

class LlmPromptSet:

    def __init__(self, prompts):
        self.prompts = prompts

    @classmethod
    def from_template_dir(cls, text, template_dir, lang, opts):

        templates = []
        if lang:
            ext = "-" + lang+".yaml"
        else:
            ext = ".yaml"
        
        for filename in sorted(os.listdir(template_dir)):
            if filename.endswith(ext):
                with open(os.path.join(template_dir,filename)) as f:
                    template = yaml.safe_load(f)
                if 'meta' not in template:
                    logging.warning("llmpromptset: rejecting prompt because of missing meta: "+str(filename))
                    continue
                templates += [template]

        prompts = []
                
        for template in templates:
            if 'split' in template['meta']:
                split = template['meta']['split']
            elif hasattr(opts,'split'):
                split = opts.split
            else:
                split = "none"

            if split == "none":
                text_segments = [text]
            elif split == "paragraph":
                text_segments = split_markdown_by_paragraph(text)
            elif split == "headline":
                if 'split_headline_level' in template['meta']:
                    split_level = template['meta']['split_headline_level']
                elif hasattr(opts,'split_headline_level'):
                    split_level = opts.split_headline_level
                else:
                    split_level = 2
                text_segments = split_markdown_by_headers(text, split_level)

            for text_segment in text_segments:
                prompts += [LlmPrompt.from_template(text_segment, template=template)]

        return cls(prompts)
            
    def execute(self, opts={}, backend='locallama', separator=""):
        text = ""
        for prompt in self.prompts:
            text += prompt.execute(opts, backend) + separator

        return text
    





    
