import subprocess, sys, threading, os, asyncio, collections

from .texttools import get_partially_repeating_pattern

class LocalLlama8B():
    def __init__(self, model_path='llama.cpp/models/lama-8B.gguf', seed=42, gpu_layers=35, context_window=65535):
        self.model_path = model_path
        self.seed = seed
        self.gpu_layers = gpu_layers
        self.context_window = context_window
        self.base_command = [
            "./llama.cpp/llama-cli",
            "-m", self.model_path,
            "-e",
            "-fa",
            "--mirostat","2",
            "-n","-2",
            #"--repeat-penalty","1.0",
            "-r", "<|eot_id|>",
            "-s", str(self.seed),
            "--temp", str(0.2),
            "--top-p", str(0.2),
            "-ngl", str(self.gpu_layers),
            "-c", str(self.context_window),
            "-f", "/dev/stdin"
        ]

    def _read_stream(self, stream, handler):
        while True:
            chunk = stream.read(1024)  # Read in chunks of 1024 bytes
            if not chunk:
                break
            sys.stderr.write(chunk)
            sys.stderr.flush()
            handler(chunk)
        stream.close()
                    
    def run(self, system, user, opts=None):

        # llama.cpp now seems to warn about a double BOS token
        #prompt = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        prompt = "<|start_header_id|>system<|end_header_id|>\n"
        prompt += system + "\n"
        prompt += "<|start_header><header_id|>user<|end_header_id|>\n"
        prompt += user + "\n"
        prompt += "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

        try:
            process = subprocess.Popen(self.base_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stop_event = threading.Event()

            # Send the prompt to stdin and immediately close stdin since no more input is expected
            process.stdin.write(prompt)
            process.stdin.close()

            all_output = []
            recent_lines = collections.deque(maxlen=30)
            empty = 0
            buff = ""

            # Function to append to all_output list
            def append_output(data):
                nonlocal empty, recent_lines, all_output, buff

                buff += data

                # If buff is long and has no line breaks, check for max 100 character long repeats in the last 500 characters:
                if "\n" not in buff and len(buff) > 500:
                    pattern = get_partially_repeating_pattern(buff[-500:],100)
                    if pattern:
                        all_output.append(buff)
                        buff = ""
                        stop_event.set()
                        raise Exception("Loop detected")

                while "\n" in buff:
                    line, buff = buff.split("\n",1)
                
                    # Only dump output after an empty line saying 'assistant'.
                    if len(all_output) > 0:
                        all_output.append(line+"\n")
                    if line.strip() == 'assistant':
                        all_output.append("")
                        
                    recent_lines.append(line.strip())
                    counts = collections.Counter(recent_lines).items()
                    if len([k for k,v in counts if v==1]) == 0:
                        stop_event.set()
                        raise Exception("Loop detected")

             # Function to print stderr output to stderr
            def print_stderr(data):
                sys.stderr.write(data)
                sys.stderr.flush()

            # Thread to handle stdout
            stdout_thread = threading.Thread(target=self._read_stream, args=(process.stdout, append_output))
            stdout_thread.start()

            # Thread to handle stderr
            stderr_thread = threading.Thread(target=self._read_stream, args=(process.stderr, print_stderr))
            stderr_thread.start()

            # Wait for the subprocess to complete
            while stdout_thread.is_alive():
                stdout_thread.join(timeout=1)
                if stop_event.is_set():
                    process.terminate()
                    stdout_thread.join()
                    stderr_thread.join()
                    sys.stderr.flush()
                    print("WARNING: stopped LLM process due to loop detection.")
                    if len(all_output) > 0:
                        all_output.append(buff)
                    all_output.append("<|loop_detected|>")
                    break
            else:
                stderr_thread.join()
                process.wait()
                sys.stderr.flush()
                if len(all_output) > 0:
                    all_output.append(buff)

                # Check if there was an error
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args, output=None, stderr=None)

            all_output = ''.join(all_output)

            if all_output.endswith('<|eot_id|>'):
                all_output = all_output[:-len('<|eot_id|>')]

            # Make sure a final new paragraph is printed to separate the LLM output from forthcoming log messages.
            sys.stderr.write("\n\n")
                
            return all_output
        
        except subprocess.CalledProcessError as e:
            print(f"Error running llama.cpp: {e}", file=sys.stderr)
            return None

class OpenAI():
    def __init__(self, api_key, model="gpt-4o", max_tokens=None):
        import openai
        self.openai = openai
        self.client = self.openai.OpenAI(api_key = api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = 0.2
        self.top_p = 0.2

    def run(self, system, user, opts=None):
        messages = [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user}
        ]

        text_response = None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p
            )
            text_response = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error querying OpenAI API: {e}", file=sys.stderr)
            return None

        print("Response:",text_response)
        return text_response


class Copilot:
    def __init__(self, key, style="precise"):
        os.environ["BING_COOKIES"] = key
        from sydney import SydneyClient
        self.sydney = SydneyClient(style=style)

    def run(self, system, user, opts=None):
        response = asyncio.run(self.sydney.compose("Act this way:\n"+system + "\n\nPlease answer:\n" + user))
        return response
