#!/usr/bin/env python3

import os
import sys
import subprocess
import re
import json

from openai import OpenAI

# Make sure OPENAI_API_KEY is set in your environment:

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def strip_markdown_fences(text):
    """
    Removes leading and trailing ``` blocks (including ```json).
    Example:
    ```json
    {
      "replacement": "...",
      "explanation": "..."
    }
    ```
    Becomes:
    {
      "replacement": "...",
      "explanation": "..."
    }
    """
    # Trim whitespace
    text = text.strip()
    # Remove any leading triple backticks with optional language
    text = re.sub(r'^```[a-zA-Z0-9]*\n?', '', text)
    # Remove any trailing triple backticks
    text = re.sub(r'```$', '', text)
    return text.strip()


def run_jsonlint(file_path):
    """
    Runs jsonlint-php on the given file_path.
    Returns (is_valid, lint_output).
    """
    print("[Debug] Checking JSON validity with jsonlint-php fallback to Python...")
    try:
        proc = subprocess.Popen(
            ["jsonlint-php", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        stdout, _ = proc.communicate()
        stdout = stdout.strip()
        print("[Debug] jsonlint-php output:", stdout)

        if "Valid JSON" in stdout:
            return True, stdout
        else:
            return False, stdout

    except FileNotFoundError:
        # Fallback to Python's built-in check
        return check_json_via_python(file_path)


def check_json_via_python(file_path):
    """
    Fallback check if jsonlint-php is not installed.
    Returns (is_valid, error_message).
    """
    try:
        with open(file_path, "r") as f:
            data = json.load(f)  # Attempt parse
        return True, "Valid JSON (Python builtin)"
    except json.JSONDecodeError as e:
        msg = f"JSONDecodeError: {e.msg} at line {e.lineno}, column {e.colno}"
        print("[Debug] Python JSON parse error ->", msg)
        return False, msg


def simulate_python_execution(file_path):
    """
    Attempt to compile the file as Python to mimic a user accidentally running
    'python file.json'.
    Returns (bool, str).
    """
    print("[Debug] Checking for Python SyntaxError by compile()...")
    try:
        with open(file_path, "r") as f:
            content = f.read()
        compile(content, file_path, 'exec')
        print("[Debug] No Python syntax error.")
        return True, "No SyntaxError"
    except SyntaxError as e:
        error_output = (
            f"SyntaxError: {e.msg} at line {e.lineno}, col {e.offset}\n"
            f"Offending code: {e.text.strip() if e.text else ''}"
        )
        print("[Debug] Caught Python SyntaxError ->", error_output)
        return False, error_output


def call_openai_for_fix(error_output, current_content):
    """
    Calls the OpenAI API with the error message to get a suggested fix,
    using the client.chat.completions.create(...) structure.
    """
    prompt = f"""
We have a JSON file that might be invalid JSON or might have caused
a Python SyntaxError if someone tried to run it directly as Python code.

Error output:
---
{error_output}
---

The current content of the JSON file is:
---
{current_content}
---

Please provide a concise fix recommendation in JSON form. Example format:

{{
  "regex_pattern": "some pattern",
  "replacement": "some replacement",
  "explanation": "one line explanation"
}}

If you prefer to provide a direct updated JSON snippet, use:

{{
  "replacement": "...the entire corrected JSON...",
  "explanation": "some explanation"
}}

Return valid JSON with these keys. Do not wrap your answer with extra text.
"""

    print("[Debug] Sending prompt to OpenAI:\n", prompt)

    chat_completion = client.chat.completions.create(
        model="gpt-4o",  # Replace "gpt-4o" with a standard model if needed
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that fixes JSON syntax errors (or Python syntax errors) "
                    "when JSON is accidentally run as Python. "
                    "You must respond with a valid JSON containing the fix instructions. "
                    "Do not add extra keys."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    fix_suggestion = chat_completion.choices[0].message.content
    print("[Debug] Raw OpenAI response:\n", fix_suggestion)

    # Remove any markdown fences from the returned suggestion
    fix_suggestion_clean = strip_markdown_fences(fix_suggestion)
    print("[Debug] After stripping markdown fences:\n", fix_suggestion_clean)

    return fix_suggestion_clean


def apply_fix_to_file(fix_response, file_path):
    """
    Parse the fix_response as JSON. Then either apply a regex pattern
    or replace the entire file content with the 'replacement'.
    """
    print("[Debug] Applying fix to file...")

    try:
        fix_data = json.loads(fix_response)
    except json.JSONDecodeError:
        print("[!] OpenAI returned invalid JSON in the fix suggestion.")
        print("Full response:\n", fix_response)
        return False

    # Potential structures:
    # {
    #   "regex_pattern": "...",
    #   "replacement": "...",
    #   "explanation": "..."
    # }
    # OR
    # {
    #   "replacement": "...",
    #   "explanation": "..."
    # }

    if "regex_pattern" in fix_data and "replacement" in fix_data:
        pattern = fix_data["regex_pattern"]
        replacement = fix_data["replacement"]
        explanation = fix_data.get("explanation", "")
        print(f"[Debug] Regex pattern: {pattern}")
        print(f"[Debug] Replacement: {replacement}")
        print(f"[Debug] Explanation: {explanation}")

        with open(file_path, "r") as f:
            old_content = f.read()

        new_content = re.sub(pattern, replacement, old_content)
        if new_content != old_content:
            with open(file_path, "w") as f:
                f.write(new_content)
            print("[Debug] Regex fix applied successfully.")
            return True
        else:
            print("[!] Regex did not match anything in the file. No changes.")
            return False

    elif "replacement" in fix_data:
        replacement_text = fix_data["replacement"]
        explanation = fix_data.get("explanation", "")
        print(f"[Debug] Full replacement fix:")
        print(f"[Debug] Explanation: {explanation}")

        with open(file_path, "w") as f:
            f.write(replacement_text)
        print("[Debug] Replaced entire file content.")
        return True

    else:
        print("[!] The fix suggestion JSON does not have the required keys.")
        print("Full response:\n", fix_response)
        return False


def fix_json_until_valid(file_path, max_iterations=10):
    """
    Main loop:
      1) Check if the JSON is valid (via jsonlint-php or fallback).
      2) If not valid, also simulate a Python run to see if there's a SyntaxError.
      3) Send errors + file content to OpenAI for a fix suggestion.
      4) Apply the fix. Repeat until valid or out of iterations.
      5) When valid, print the final JSON content for reference.
    """
    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration} ---")

        is_valid, lint_output = run_jsonlint(file_path)
        if is_valid:
            print("[✓] JSON is valid. Script finished.")

            # Print final JSON content
            with open(file_path, "r") as f:
                final_content = f.read()
            print("\n[Final Fixed JSON Content]:\n", final_content)
            return

        # There's some error
        print("[Debug] JSON Lint Output:\n", lint_output)

        py_ok, py_error_output = simulate_python_execution(file_path)
        if not py_ok:
            print("[Debug] Python SyntaxError:\n", py_error_output)

        # Combine error summary
        error_summary = f"JSON Lint Output:\n{lint_output}"
        if not py_ok:
            error_summary += f"\n\nPython SyntaxError:\n{py_error_output}"

        # Read current content
        with open(file_path, "r") as f:
            current_content = f.read()

        # Ask OpenAI for fix
        fix_suggestion = call_openai_for_fix(error_summary, current_content)

        # Apply the fix
        changed = apply_fix_to_file(fix_suggestion, file_path)
        if not changed:
            print("[!] No fix was applied. Stopping to avoid infinite loop.")
            return

    print("[!] Reached maximum iterations. JSON may still be invalid.")
    # Optionally show the last state of the file
    with open(file_path, "r") as f:
        final_content = f.read()
    print("\n[Final File State After Max Iterations]:\n", final_content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_json_file>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    if not os.path.exists(json_file_path):
        print(f"[!] File not found: {json_file_path}")
        sys.exit(1)

    fix_json_until_valid(json_file_path)
