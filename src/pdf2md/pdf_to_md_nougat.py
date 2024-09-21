#!venv.manual/bin/python3
# https://github.com/NielsRogge/Transformers-Tutorials/blob/master/Nougat/Inference_with_Nougat_to_read_scientific_PDFs.ipynb

import argparse, io, re
from pathlib import Path
from typing import Optional, List
from collections import defaultdict

import torch
from transformers import AutoProcessor, VisionEncoderDecoderModel
import fitz
from huggingface_hub import hf_hub_download
from PIL import Image
from transformers import StoppingCriteria, StoppingCriteriaList

#processor = AutoProcessor.from_pretrained("facebook/nougat-small")
#model = VisionEncoderDecoderModel.from_pretrained("facebook/nougat-small")
processor = AutoProcessor.from_pretrained("facebook/nougat-base")
model = VisionEncoderDecoderModel.from_pretrained("facebook/nougat-base")
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def rasterize_paper(
    pdf: Path,
    outpath: Optional[Path] = None,
    dpi: int = 96,
    return_pil=False,
    pages=None,
) -> Optional[List[io.BytesIO]]:
    """
    Rasterize a PDF file to PNG images.

    Args:
        pdf (Path): The path to the PDF file.
        outpath (Optional[Path], optional): The output directory. If None, the PIL images will be returned instead. Defaults to None.
        dpi (int, optional): The output DPI. Defaults to 96.
        return_pil (bool, optional): Whether to return the PIL images instead of writing them to disk. Defaults to False.
        pages (Optional[List[int]], optional): The pages to rasterize. If None, all pages will be rasterized. Defaults to None.

    Returns:
        Optional[List[io.BytesIO]]: The PIL images if `return_pil` is True, otherwise None.
    """

    pillow_images = []
    if outpath is None:
        return_pil = True
    try:
        if isinstance(pdf, (str, Path)):
            pdf = fitz.open(pdf)
        if pages is None:
            pages = range(len(pdf))
        for i in pages:
            page_bytes: bytes = pdf[i].get_pixmap(dpi=dpi).pil_tobytes(format="PNG")
            if return_pil:
                pillow_images.append(io.BytesIO(page_bytes))
            else:
                with (outpath / ("%02d.png" % (i + 1))).open("wb") as f:
                    f.write(page_bytes)
    except Exception:
        pass
    if return_pil:
        return pillow_images


class RunningVarTorch:
    def __init__(self, L=15, norm=False):
        self.values = None
        self.L = L
        self.norm = norm

    def push(self, x: torch.Tensor):
        assert x.dim() == 1
        if self.values is None:
            self.values = x[:, None]
        elif self.values.shape[1] < self.L:
            self.values = torch.cat((self.values, x[:, None]), 1)
        else:
            self.values = torch.cat((self.values[:, 1:], x[:, None]), 1)

    def variance(self):
        if self.values is None:
            return
        if self.norm:
            return torch.var(self.values, 1) / self.values.shape[1]
        else:
            return torch.var(self.values, 1)


class StoppingCriteriaScores(StoppingCriteria):
    def __init__(self, threshold: float = 0.015, window_size: int = 200):
        super().__init__()
        self.threshold = threshold
        self.vars = RunningVarTorch(norm=True)
        self.varvars = RunningVarTorch(L=window_size)
        self.stop_inds = defaultdict(int)
        self.stopped = defaultdict(bool)
        self.size = 0
        self.window_size = window_size

    @torch.no_grad()
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        last_scores = scores[-1]
        self.vars.push(last_scores.max(1)[0].float().cpu())
        self.varvars.push(self.vars.variance())
        self.size += 1
        if self.size < self.window_size:
            return False

        varvar = self.varvars.variance()
        for b in range(len(last_scores)):
            if varvar[b] < self.threshold:
                if self.stop_inds[b] > 0 and not self.stopped[b]:
                    self.stopped[b] = self.stop_inds[b] >= self.size
                else:
                    self.stop_inds[b] = int(
                        min(max(self.size, 1) * 1.15 + 150 + self.window_size, 4095)
                    )
            else:
                self.stop_inds[b] = 0
                self.stopped[b] = False
        return all(self.stopped.values()) and len(self.stopped) > 0

def do_page(page_image):

    pixel_values = processor(images=page_image, return_tensors="pt").pixel_values

    outputs = model.generate(
        pixel_values.to(device),
        min_length=1,
        max_length=3584,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
        output_scores=True,
        stopping_criteria=StoppingCriteriaList([StoppingCriteriaScores()]),
    )

    generated = processor.batch_decode(outputs[0], skip_special_tokens=True)[0]

    return generated

def fix_headlines(text):
    pattern = r'(?m)(^\s*$\n)(\s*\*\*(.*?)\*\*\s*)($\n^\s*$)'

    def replace_if_short(match):
        content = match.group(3).strip()
        if len(content) < 200:
            return f'## {content}\n'
        else:
            return match.group(0)

    replaced_text = re.sub(pattern, replace_if_short, text)
    
    return replaced_text


def fix_headlines(text):

    pattern = r'(?m)^\s*\*\*(.*?)\*\*\s*$'

    def replace_if_short(match):
        content = match.group(1).strip()
        if len(content) < 200:
            return f"\n## {content}\n"
        else:
            return match.group(0)

    replaced_text = re.sub(pattern, replace_if_short, text)
    
    return replaced_text


def parse_pdf(filename, page_range = None, latex_delimiters=False):
    images = rasterize_paper(pdf=Path(filename), return_pil=True)

    loc = 0
    all_text = ""
    #page_locs = {}
    for page, image in enumerate(images):
        print("Converting page",page+1,"of",len(images))
        if page_range is not None:
            if isinstance(page_range,int):
                if page != page_range:
                    continue
            elif len(page_range) == 1:
                print("============= PAGE:",page,page_range[0])
                if page != page_range[0]:
                    continue
            elif len(page_range) == 2:
                if page < page_range[0] or page > page_range[1]:
                    continue
            else:
                raise Exception("Cannot interprete format of page_range: "+str(page_range))
        page_image = Image.open(image)
        text = do_page(page_image)
        #text = re.sub('####* Abstract', '## Abstract', text)
        if text[0] == "#":
            all_text += "\n\n"
        #    loc += 2
        elif text[0] == ".":
            all_text += "\n"
        #    loc += 1
        else:
            all_text += " "
        #    loc += 1
        #text = processor.post_process_generation(text, fix_markdown=True).strip()
        #loc += len(text)
        #page_locs[loc]= page
        all_text += text
        
    #return all_text, {'page_locs':page_locs}
    all_text = processor.post_process_generation(all_text, fix_markdown=True).strip()

    # Small Nougat tends to be confused about the abstract heading typically being small
    # findal = re.sub('####* Abstract', '## Abstract', final)

    # Patch odd reading errors
    all_text = re.sub(r'^.*\\bar{\\bar{\\bar{\\bar{.*$','',all_text,flags=re.MULTILINE)
    # Turn "fake"-headlines via otherwise empty lines in bold into headers
    all_text = fix_headlines(all_text)
    # Remove headline numbering
    all_text = re.sub(r'^(#+) [0-9]+(\.[0-9]+)*\.? (.*)$', r'\g<1> \g<3>', all_text, flags=re.MULTILINE)
    # Newlines for display equations
    all_text = re.sub(r'(?<=\.)(?=\\\[)','\n', all_text)
    all_text = re.sub(r'(?<=\\\])(?=\.)','\n', all_text)
    if latex_delimiters:
        # Use LaTeX display equations
        all_text = re.sub(r'\\\[|\\\]','$$', all_text)
        # Use LaTex inline equations
        all_text = re.sub(r'\\\(|\\\)','$', all_text)

    return all_text, {}

def main(args):
    text = parse_pdf(args.filename)
    print(text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert file.")
    parser.add_argument("filename", help="The file name to process")
    parser.add_argument("-o", "--output", help="The output filename (defaults to <filename_base>.md")
    args = parser.parse_args()

    main(args)
