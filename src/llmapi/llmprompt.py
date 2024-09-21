import os, json, copy

import yaml

from . import llmmodels

class LlmPrompt:

    _template_cache = {}

    def __init__(self, prompt_data, meta=None, filename=None, output=None, deltas=None):

        self.prompt_data = prompt_data
        
        if meta is None:
            meta = {}
        self.meta = meta
        self.filename = filename
        if self.filename is not None:
            self.barename = filename[:-len(".prompt")]
        else:
            self.barename = None
        self.output = output
        self.deltas = deltas
        
    @classmethod
    def from_template(cls, text, template):

        if template not in cls._template_cache:
            with open(template,'r') as f:
                cls._template_cache[template] = yaml.safe_load(f)

        template = cls._template_cache[template]
        prompt_data = {}

        for key in ['system', 'user']:
            prompt_data[key] = template[key].format(text=text)

        if 'meta' in template:
            prompt_meta = copy.deepcopy(template['meta'])
        else:
            prompt_meta = {}
                
        return LlmPrompt(prompt_data,meta=prompt_meta)

    def execute(self, keys={}, backend='locallama'):

        if backend is None or backend == 'localllama':
            llm = llmmodels.LocalLlama8B()
        elif backend == 'openai':
            if keys.openai_key is None:
                raise Exception("Trying to use OpenAI without API key set")
            llm=llmmodels.OpenAI(api_key=keys.openai_key)
        elif backend == 'copilot':
            if keys.copilot_key is None:
                raise Exception("Trying to use Copilot without key (cookie) set")
            llm=llmmodels.Copilot(key=keys.copilot_key)
        else:
            raise Exception("Unknown LLM backend requested")

        result = llm.run(self.prompt_data['system'],self.prompt_data['user'])
        if result.endswith("<|loop_detected|>"):
            print("ERROR: Llm model entered a loop. Try other options, e.g., run post-processing in smaller chunks.")
        
        self.output = result

        return result

    
    @classmethod    
    def serialize_prompt(cls, p):
        return "\n== System ==\n" + str(p['system']) + "\n== User ==\n" + str(p['user'])

    @classmethod
    def deserialize_prompt(cls, prompt_str):
        p = {}
        _, _, rest = prompt_str.partition("== System ==")
        p['system'], _, p['user'] = rest.partition("== User ==")
        p['system'] = p['system'].strip()
        p['user'] = p['user'].strip()
        return p
    
    @classmethod
    def read(cls, filename):

        with open(filename, 'r') as f:
            data_prompt = cls.deserialize_prompt(f.read())

        barename = filename[:-len(".prompt")]
            
        filename = barename + '.meta'
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                meta = json.load(f)
        else:
            meta = {}

        filename = barename + '.output'            
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                output = f.read()
        else:
            output = None

        filename = barename + '.deltas'            
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                deltas = json.load(f)
        else:
            deltas = None

        return Prompt(prompt_data, meta, filename=filename, output=output, deltas=deltas)

    def write(self, filename=None):

        if filename is None:
            filename = self.filename

        if filename is None:
            raise Exception("No filename provided")

        self.filename = filename
        self.barename = filename[:-len(".prompt")]
            
        with open(filename, 'w') as f:
            f.write(self.serialize_prompt(self.prompt_data))

        filename = self.barename+".meta"
        with open(filename, 'w') as f:
            json.dump(self.meta, f)

        if self.output is not None:
            filename = self.barename+".output"
            with open(filename, 'w') as f:
                f.write(self.output)

        if self.deltas is not None:
            filename = self.barename+".deltas"
            with open(filename, 'w') as f:
                json.dump(self.deltas)          
        
