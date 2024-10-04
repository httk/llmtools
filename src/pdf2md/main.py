#!/usr/bin/env python3
"""
Convert pdf to md
"""
import re, argparse, logging, os, sys, tomllib

from llmapi import LlmPrompt, LlmPromptSet

from ._version import __version__
from .convert import convert_pdf2md
from llmapi import ExceptionWrapper, split_markdown_by_headers
 
arguments = [
    {
        'names': ['--version'],
        'action': 'version',
        'version': '%(prog)s '+ __version__
    },
    {
        'names': ['filename'],
        'help': 'The file name of the document to process.',
        'type': str,
    },
    {
        'names': ['-d', '--debug'],
        'help': 'Produce full tracebacks on error',
        'action': 'store_true',
        'default': False
    },
    {
        'names': ['-v', '--verbose'],
        'help': 'Increase verbosity of output',
        'dest': 'verbosity',
        'action': 'count',
        'default': 3
    },
    {
        'names': ['-q', '--quiet'],
        'help': 'Decrease verbosity of output',
        'action': 'count',
        'default': 0
    },
    {
        'names': ['-l', '--lang'],
        'help': 'Language the document is written in.',
        'choices': ['en', 'sv'],
        'default': 'en',
        'type': str,
    },
    {
        'names': ['-p', '--postprocess'],
        'help': 'Run a postprocessing step using a LLM. It is recommended not to do this unless necessary, because it has a tendency to "improve" on the original, e.g., by fixing grammar and spelling errors present in the original.',
        'action': 'store_true',
        'default': False
    },
    {
        'names': ['-s', '--split'],
        'help': 'Let the LLM process the whole document (none) or split it on paragraphs or headlines.',
        'choices' : ['none', 'paragraph','headline'],
        'default': 'none',
        'type': str,
    },
    {
        'names': ['-L', '--split-headline-level'],
        'help': 'Split LLM input at the selected header level (0 = all text at once, 1 = level one headings, 2 = level two headings, etc).',
        'default': 2,
        'type': int,
    },        
    {
        'names': ['-t', '--translate'],
        'help': 'Translate the output to the selected language.',
        'choices': ['en', 'sv'],
        'type': str,
    },
    {
        'names': ['-r', '--range'],
        'help': 'Page number or range of pages to extract (e.g., 5 or 5-7)',
        'type': str,
    },
    {
        'names': ['-o', '--outfile'],
        'help': 'Markdown filename to write.',
        'type': str,
    },
    {
        'names': ['-x', '--extract-backend'],
        'help': 'The PDF text extraction backend to use.',
        'choices': ['nougat','pdfminer','mupdf'],
        'default': 'nougat',
        'type': str,
    },
    {
        'names': ['--openai-key'],
        'help': "API Token for OpenAPI",
        'type': str,
    },
    {
        'names': ['-m', '--translate-model'],
        'help': 'The LLM backend to use for translation.',
        'choices': ['localllama', 'openai', 'copilot'],
        'default': 'localllama',
        'type': str,
    },
]

def main():
    for i in range(len(sys.argv)-1):
        if sys.argv[i] == '--config' or sys.argv[i] == '-c':
            config_filename = sys.argv[i+1]
    else:
        if "LLMTOOLS_CONFIG" in os.environ:
            config_filename = os.environ["LLMTOOLS_CONFIG"]
        elif 'XDG_CONFIG_HOME' in os.environ:
            config_filename = os.path.join(os.environ["XDG_CONFIG_HOME"],'proof/proof.conf')
        else:
            config_filename = os.path.expanduser('~/.llmtools/llmtools.conf')

    if os.path.exists(config_filename):
        with open(config_filename, 'rb') as f:
            config = tomllib.load(f)
    else:
        config = {}

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for arg in arguments:
        names = arg.pop('names')
        parser.add_argument(*names, **arg)
    parser.set_defaults(**config)
    args = parser.parse_args()

    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    args.log_level = log_levels[max(min(len(log_levels) - 1, args.verbosity-args.quiet),0)]

    # Configure logging
    logging.basicConfig(format='pdf2md %(levelname)s: %(message)s',level=args.log_level)
    logging.debug("invoked with: "+str(args))

    # Turn on tracebacks, etc., if verbosity is max *or* the debug flag is given
    args.debug = args.debug or args.log_level <= logging.DEBUG
    ExceptionWrapper.debug = args.debug

    try:

        logging.info("Pdf2md "+__version__+" started")

        filename = args.filename
        filename_bare, filename_ext = os.path.splitext(filename)
        if args.outfile is None:
            args.outfile = filename_bare + '.md'

        # Parse page range
        try:
            if args.range is not None:
                if '-' in args.range:
                    args.page_range = [int(args.range.partition('-')[0])-1,int(args.range.partition('-')[2])-1]
                else:
                    args.page_range = [int(args.range)-1]
            else:
                args.page_range = None
        except Exception as e:
            raise ExceptionWrapper("Could not parse page range.", e) from e

        text = convert_pdf2md(filename, args.page_range, backend=args.extract_backend)

        print("== Extracted markdown")
        print(text)
        print("=====================")
        
        prompts_dir = os.path.join(os.path.dirname(__file__),"..","prompts","pdf2md")

        if args.postprocess:
            promptset = LlmPromptSet.from_template_dir(text, os.path.join(prompts_dir,"postprocess"), args.lang, args)
            text = promptset.execute(args, backend=args.translate_model)
                    
        if args.translate is not None:
            promptset = LlmPromptSet.from_template_dir(text, os.path.join(prompts_dir,"translate"), args.translate, args)
            text = promptset.execute(args, backend=args.translate_model)
                    
        with open(args.outfile, 'w') as f:
            f.write(str(text))

        logging.info(f"Output written to {args.outfile}")

    except Exception as e:
        if args.debug:
            raise
        else:
            print(e)
            return 1

if __name__ == "__main__":
    main()
