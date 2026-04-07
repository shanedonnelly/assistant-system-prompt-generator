#!/usr/bin/env python3
"""
Assistant System Prompt Generator
Generates system prompts for AI assistants based on config/config.yaml and config/based_prompts.yaml.
"""

import os
import sys

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)

CONFIG_PATH = "config/config.yaml"
BASED_PROMPTS_PATH = "config/based_prompts.yaml"
OUTPUT_PATH = "output/system_prompt.txt"

SECTION_ORDER = [
    "base",
    "tone_and_formatting",
    "evenhandedness",
    "responding_to_mistakes_and_criticism",
    "security",
    "language",
    "web_search",
    "multimodal_capabilities",
    "product_information",
    "knowledge_cutoff",
]

REQUIRED_GLOBAL_FIELDS = ["assistant_name", "current_datetime", "prompt_size", "use_markdown_formatting"]


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def require_field(config, field_path):
    """Walk a dot-separated field path and error if missing."""
    keys = field_path.split(".")
    current = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            print(f"Error: Required field '{field_path}' is missing from config.yaml.")
            sys.exit(1)
        current = current[key]
    return current


def replace_variables(text, assistant_name, current_datetime):
    text = text.replace("{assistant_name}", assistant_name)
    text = text.replace("{current_datetime}", current_datetime)
    return text


def strip_blank_lines(text):
    """Remove blank lines from text, keeping only non-empty lines."""
    return "\n".join(line for line in text.splitlines() if line.strip())


def wrap_section(tag, content):
    return f"<{tag}>\n{strip_blank_lines(content)}\n</{tag}>"


def build_multimodal_section(section_cfg, assistant_name):
    capabilities = {
        "images": section_cfg["can_process_images"],
        "videos": section_cfg["can_process_videos"],
        "audio": section_cfg["can_process_audio"],
        "documents": section_cfg["can_process_documents"],
    }

    can = [k for k, v in capabilities.items() if v]
    cannot = [k for k, v in capabilities.items() if not v]

    parts = []
    if can:
        parts.append(f"{assistant_name} can receive and process {', '.join(can)}.")
    if cannot:
        parts.append(f"{assistant_name} cannot process {', '.join(cannot)}. If a user sends one of these, it should politely explain the limitation and suggest an alternative.")

    return " ".join(parts)


def build_section_content(section_name, bp, section_cfg, prompt_size, assistant_name):
    if section_name == "multimodal_capabilities":
        return build_multimodal_section(section_cfg, assistant_name)

    if section_name in ("product_information", "language"):
        intro = bp.get("intro", "")
        user_content = section_cfg.get("content", "").strip()
        if intro and user_content:
            return f"{intro}\n{user_content}"
        return user_content or intro

    if section_name == "knowledge_cutoff":
        cutoff_date = section_cfg["date"]
        text = bp[prompt_size]
        return text.replace("{cutoff_date}", cutoff_date)

    return bp[prompt_size]


def generate_prompt(config, based_prompts):
    global_cfg = config["global"]
    for field in REQUIRED_GLOBAL_FIELDS:
        require_field(config, f"global.{field}")

    assistant_name = global_cfg["assistant_name"]
    current_datetime = global_cfg["current_datetime"]
    prompt_size = global_cfg["prompt_size"]
    use_markdown = global_cfg["use_markdown_formatting"]

    if prompt_size not in ("small", "medium", "large"):
        print(f"Error: prompt_size must be 'small', 'medium', or 'large'. Got '{prompt_size}'.")
        sys.exit(1)

    sections_config = config["sections"]
    parts = []

    for section_name in SECTION_ORDER:
        section_cfg = sections_config.get(section_name, {})
        if not section_cfg.get("enabled", False):
            continue

        bp = based_prompts.get(section_name, {})
        content = build_section_content(section_name, bp, section_cfg, prompt_size, assistant_name)

        if section_name == "base" and use_markdown:
            content += f"\n{assistant_name} uses Markdown formatting."

        if content:
            content = replace_variables(content, assistant_name, current_datetime)
            parts.append(wrap_section(section_name, content))

    custom_sections = config.get("custom_sections") or []
    for cs in custom_sections:
        title = cs["title"].strip()
        content = cs["content"].strip()
        if content:
            content = replace_variables(content, assistant_name, current_datetime)
            tag = title.lower().replace(" ", "_").replace("-", "_")
            parts.append(wrap_section(tag, content))

    inner = "\n".join(parts)
    closing = f"{assistant_name} is now being connected with a person."
    return f"<assistant_behavior>\n{inner}\n</assistant_behavior>\n{closing}"


def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Config file not found at '{CONFIG_PATH}'.")
        print("Copy config/config.example.yaml to config/config.yaml and customize it.")
        sys.exit(1)

    if not os.path.exists(BASED_PROMPTS_PATH):
        print(f"Error: Based prompts file not found at '{BASED_PROMPTS_PATH}'.")
        sys.exit(1)

    config = load_yaml(CONFIG_PATH)
    based_prompts = load_yaml(BASED_PROMPTS_PATH)

    prompt = generate_prompt(config, based_prompts)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(prompt)

    word_count = len(prompt.split())
    char_count = len(prompt)
    token_count = char_count // 4  # Rough estimate: 1 token ~ 4 characters
    print(f"System prompt generated: {OUTPUT_PATH}")
    print(f"Size: {word_count} words / {char_count} characters / {token_count} tokens")


if __name__ == "__main__":
    main()
