# JSON Fixer with LLM

This repository contains a Python script that automatically fixes broken JSON files using an LLM (via the OpenAI API). The script is designed to help correct JSON syntax errors or even Python `SyntaxError`s that occur when a JSON file is mistakenly executed as a Python script.

---

## Features

- **JSON Validation:** Uses `jsonlint-php` (if available) to validate JSON files, with a fallback to Python's built-in JSON parser.
- **Python Syntax Check:** Simulates Python execution to detect syntax errors when JSON is accidentally run as Python.
- **LLM-powered Fixes:** Submits error messages and file content to the OpenAI API to obtain fix recommendations.
- **Flexible Fix Application:** Supports fixes in the form of regex patterns or full content replacement.
- **Iterative Process:** Repeatedly applies fixes until the JSON is valid or a maximum number of iterations is reached.

---

## Requirements

- **Python 3.12:** The script has been tested using Python 3.12.
- **OpenAI API Key:** Set your OpenAI API key in the environment variable `OPENAI_API_KEY`.
- **jsonlint-php (Optional):** For enhanced JSON validation, install [jsonlint-php](https://github.com/squizlabs/PHP_CodeSniffer) if desired. The script will fall back to Python's built-in JSON parser if `jsonlint-php` is not available.

---

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/json-fixer-llm.git
   cd json-fixer-llm
   ```

2. **Set Up Environment:**

   - Ensure you have Python 3.12 installed.
   - Set your OpenAI API key in your shell environment:

    ```bash
    export OPENAI_API_KEY="your_openai_api_key_here"
    ```

3. **Install Dependencies (if any):**

   If additional dependencies are needed (e.g., `jsonlint-php`), follow the respective installation instructions. For Python dependencies, consider using a virtual environment and `pip` for package management.

---

## Usage

Run the script from the command line by specifying the path to the broken JSON file:

```bash
python3.12 python.py <broken_json_file.json>
```

The script will:
- Check the JSON file for syntax errors.
- Attempt to compile the file as Python to catch any accidental execution errors.
- Send any error messages along with the file content to the OpenAI API for a fix suggestion.
- Apply the suggested fix (either via regex or a full replacement).
- Iterate until the JSON file is valid or the maximum iteration count is reached.

---

## How It Works

1. **Validation & Syntax Check:**
   The script first attempts to validate the JSON file using `jsonlint-php`. If this tool is unavailable, it falls back to Python’s built-in JSON parser. It also simulates a Python execution to catch `SyntaxError`s.

2. **LLM Interaction:**
   When errors are detected, the script constructs a prompt detailing the errors and the current file content. This prompt is sent to the OpenAI API to generate a fix suggestion in a structured JSON format.

3. **Applying Fixes:**
   The fix suggestion can either be a regex-based modification or a complete replacement of the JSON content. The script applies the fix accordingly and re-checks the JSON for validity.

4. **Iteration:**
   This process repeats for up to 10 iterations (by default) until a valid JSON is achieved or the maximum number of iterations is reached.

---

## Customization

- **Max Iterations:** You can adjust the maximum number of iterations by modifying the `max_iterations` parameter in the `fix_json_until_valid` function.
- **Fix Suggestion Format:** The script expects the LLM response in a specific JSON format. Feel free to modify the expected format and processing logic as needed.

---

## Contributing

Contributions are welcome! If you find issues or have suggestions for improvements, please open an issue or submit a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

