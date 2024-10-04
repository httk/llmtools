#!/usr/bin/env python3
"""
Proofread a student work
"""
import os, re, argparse, logging, os

from llmapi import LlmPrompt

from ._version import __version__
from llmapi import ExceptionWrapper, split_markdown_by_headers

arguments = [
    {
        'names': ['--version'],
        'action': 'version',
        'version': '%(prog)s '+ __version__
    },
    {
        'names': ['-f', '--filename'],
        'help': 'The file name of the document to process (omit to read from stdin)',
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
        'help': 'Choose language.',
        'choices': ['en', 'sv'],
        'default': 'en',
        'type': str,
    },
    {
        'names': ['-p', '--operations'],
        'help': 'A name of a set of operations to apply, or (if contains at least one "/" character) path to a directory of LLM operations to apply.',
        'default': 'review',
        'type': str,
    },
    {
        'names': ['-o', '--outfile'],
        'help': 'Markdown filename to write.',
        'type': str,
    },    
]

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for arg in arguments:
        names = arg.pop('names')
        parser.add_argument(*names, **arg)
    args = parser.parse_args()

    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    args.log_level = log_levels[max(min(len(log_levels) - 1, args.verbosity-args.quiet),0)]

    # Configure logging
    logging.basicConfig(format='correctly %(levelname)s: %(message)s',level=args.log_level)
    logging.debug("invoked with: "+str(args))

    # Turn on tracebacks, etc., if verbosity is max *or* the debug flag is given
    args.debug = args.debug or args.log_level <= logging.DEBUG
    ExceptionWrapper.debug = args.debug

    try:

        logging.info(__version__+" started")

        filename = args.filename
        filename_bare, filename_ext = os.path.splitext(filename)
        if args.outfile is None:
            args.outfile = filename_bare + '.md'

        # Parse page range
        try:
            if args.pages is not None:
                if '-' in args.pages:
                    args.page_range = [int(args.pages.partition('-')[0])-1,int(args.pages.partition('-')[2])-1]
                else:
                    args.page_range = [int(args.pages)-1]
            else:
                args.page_range = None
        except Exception as e:
            raise ExceptionWrapper("Could not parse page range.", e) from e

        if filename_ext == '.pdf':
            text = pdf2md.convert(filename, args.page_range, backend=args.extract_backend)
        elif filename_ext == '.md':
            with open(filename, 'r') as f:
                text = f.read()
            
        print("========")
        print(text)

        with open(args.outfile, 'w') as f:
            f.write(str(text))

        p = proofly.instantiate_prompt(text, "correctly_translate.yaml")
        result = proofly.execute_prompt(p, args, backend=args.translate_model)

        print("========")
        print(result)
            
        logging.info(f"Raw text written to {args.outfile}")

    except Exception as e:
        if args.debug:
            raise
        else:
            print(e)
            return 1

if __name__ == "__main__":
    main()

                
