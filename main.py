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

# Sections enabled by default when not explicitly configured
DEFAULT_ENABLED = {"base", "tone_and_formatting", "evenhandedness", "responding_to_mistakes_and_criticism", "security"}

# Logical order of sections in the generated prompt
SECTION_ORDER = [
    "base",
    "tone_and_formatting",
    "evenhandedness",
    "responding_to_mistakes_and_criticism",
    "security",
    "web_search",
    "multimodal_capabilities",
    "product_information",
    "knowledge_cutoff",
]


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def replace_variables(text, assistant_name, current_datetime):
    text = text.replace("{assistant_name}", assistant_name)
    text = text.replace("{current_datetime}", current_datetime)
    return text


def wrap_section(tag, content):
    return f"<{tag}>\n{content.strip()}\n</{tag}>"


def build_multimodal_section(bp, section_cfg, prompt_size):
    parts = []

    intro = bp.get("intro", "")
    if intro:
        parts.append(intro)

    capabilities = [
        ("can_process_images", "images"),
        ("can_process_videos", "videos"),
        ("can_process_audio", "audio"),
        ("can_process_documents", "documents"),
    ]

    for cap_key, _ in capabilities:
        cap_value = section_cfg.get(cap_key, False)
        cap_texts = bp.get(cap_key, {})
        key = "true" if cap_value else "false"
        text = cap_texts.get(key, "")
        if text:
            parts.append(text)

    return "\n\n".join(parts)


def build_section_content(section_name, bp, section_cfg, prompt_size):
    if section_name == "multimodal_capabilities":
        return build_multimodal_section(bp, section_cfg, prompt_size)

    if section_name == "product_information":
        intro = bp.get("intro", "")
        user_content = section_cfg.get("content", "").strip()
        if intro and user_content:
            return f"{intro}\n\n{user_content}"
        return user_content or intro

    if section_name == "knowledge_cutoff":
        cutoff_date = section_cfg.get("date", "")
        text = bp.get(prompt_size) or bp.get("medium", "")
        return text.replace("{cutoff_date}", cutoff_date)

    # Standard pre-written sections with size variants
    return bp.get(prompt_size) or bp.get("medium", "")


def generate_prompt(config, based_prompts):
    global_cfg = config.get("global", {}) or {}
    assistant_name = (global_cfg.get("assistant_name") or "AI Assistant").strip() or "AI Assistant"
    current_datetime = global_cfg.get("current_datetime") or "{{CURRENT_DATETIME}}"
    prompt_size = global_cfg.get("prompt_size") or "medium"

    if prompt_size not in ("small", "medium", "large"):
        print(f"Warning: unknown prompt_size '{prompt_size}', falling back to 'medium'.")
        prompt_size = "medium"

    sections_config = config.get("sections", {}) or {}
    parts = []

    for section_name in SECTION_ORDER:
        section_cfg = sections_config.get(section_name, {}) or {}
        enabled = section_cfg.get("enabled")
        if enabled is None:
            enabled = section_name in DEFAULT_ENABLED
        if not enabled:
            continue

        bp = based_prompts.get(section_name, {}) or {}
        content = build_section_content(section_name, bp, section_cfg, prompt_size)

        if content:
            content = replace_variables(content, assistant_name, current_datetime)
            parts.append(wrap_section(section_name, content))

    # Custom sections
    custom_sections = config.get("custom_sections") or []
    for cs in custom_sections:
        title = (cs.get("title") or "custom").strip()
        content = (cs.get("content") or "").strip()
        if content:
            content = replace_variables(content, assistant_name, current_datetime)
            tag = title.lower().replace(" ", "_").replace("-", "_")
            parts.append(wrap_section(tag, content))

    inner = "\n\n".join(parts)
    return wrap_section("assistant_behavior", "\n" + inner + "\n")


def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Config file not found at '{CONFIG_PATH}'.")
        print("Copy config/config.yaml.example to config/config.yaml and customize it.")
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
    print(f"System prompt generated: {OUTPUT_PATH}")
    print(f"Size: {word_count} words / {char_count} characters")


if __name__ == "__main__":
    main()
