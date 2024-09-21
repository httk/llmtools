# llmtools
Tools for working with large language models

## Getting started

The `bin/...` commands are set up to automatically use a Python virtual environment in `venv` if it exist.
Hence, if you do not have all prerequisites already installed and available in your environment, you can set up an environment to use with llmtools like this:

```bash

  python3 -m venv venv
  venv/bin/pip3 install pymupdf python-Levenshtein nltk torch torchvision torchaudio openai sydney-py
  venv/bin/pip3 install git+https://github.com/huggingface/transformers.git  

```

To use the locallama backend, you also need access to llama.cpp and a suitable model file.
Download and compile llama.cpp for your platform.
Then setup a subdirectory as follows:

```bash
 
  mkdir llama.cpp
  cd llama.cpp
  ln -s <path to your llama-cli> llama-cli
  mkdir models
  cd models
  ln -s <path to your 8B llama model> lama-8B.gguf

```
(Or, you can also just clone the llama.cpp repo here and organize it accordinglt)

