import re
import logging
from typing import Optional


class VersionPatternDetector:
    @staticmethod
    def is_dot_number_string(text: str) -> bool:
        return bool(re.match(r"^[\d.]+$", text))

    @staticmethod
    def is_dash_number_string(text: str) -> bool:
        return bool(re.match(r"^[\d-]+$", text))

    @staticmethod
    def is_semantic_version(version: str) -> bool:
        semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        return bool(re.match(semver_pattern, version))

    @staticmethod
    def has_build_metadata(version: str) -> bool:
        return bool(re.search(r"\+[0-9a-zA-Z-]", version))

    @staticmethod
    def has_pre_release(version: str) -> bool:
        return bool(re.search(r"-(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)", version))

    @staticmethod
    def get_segment_pattern(segment: str) -> str:
        return f"{len(segment)}Num"

    @staticmethod
    def standardize_dev_stage(text: str) -> str:
        # Special handling for version prefixes
        if len(text) == 1 and text.lower() in ["v", "r"]:
            return text

        dev_stages = {
            "preview": "preview",
            "beta": "beta",
            "rc": "rc",
            "alpha": "alpha",
            "dev": "dev",
            "snapshot": "snapshot",
            "milestone": "milestone",
            "release": "release",
            "final": "final",
            "stable": "stable",
            "latest": "latest",
            "patch": "patch",
            "build": "build",
            "hotfix": "hotfix",
            "candidate": "candidate",
            "test": "test",
            "unstable": "unstable",
            "master": "master",
            "pre": "pre",
            "x64": "x64",
            "esr": "esr",
            "lts": "lts",
            "longterm": "longterm",
            "extended": "extended",
            "unsupported": "unsupported",
            "rel":  "rel",
            "git": "git",
            "rev":  "rev",
            "major": "major",
            "minor": "minor",
        }
        text_lower = text.lower()

        # Check for exact matches first
        if text_lower in dev_stages:
            return dev_stages[text_lower]

        # Then check for partial matches
        for stage in dev_stages:
            if stage in text_lower:
                return dev_stages[stage]

        # If no match found, return the length-based pattern
        return f"{len(text)}Letter"

    @staticmethod
    def get_version_pattern_name(version: str) -> str:
        # Split version into segments by separators while preserving the separators
        segments = re.split(r"([. _()-])", version)
        if not segments:
            return "unknown"

        # Process segments to identify numbers, letters, and separators
        pattern_parts = []
        for seg in segments:
            if seg in [".", "-", "_", " ", "(", ")"]:  # Handle separators
                pattern_parts.append(
                    "Dash"
                    if seg == "-"
                    else (
                        "Dot"
                        if seg == "."
                        else (
                            "Underscore"
                            if seg == "_"
                            else (
                                "Space"
                                if seg == " "
                                else ("OpenBrac" if seg == "(" else "CloseBrac")
                            )
                        )
                    )
                )
            elif seg.strip():  # Handle non-empty segments
                # Split segment into letter and number parts
                parts = re.findall(r"[A-Za-z]+|\d+", seg)
                for part in parts:
                    if part.isdigit():
                        pattern_parts.append(f"{len(part)}Num")
                    elif part.isalpha():
                        pattern_parts.append(
                            f"{len(part)}Letter"
                            if len(part) == 1
                            else VersionPatternDetector.standardize_dev_stage(part)
                        )

        # Handle numeric versions with separators and letter suffixes
        segments = re.split(
            r"([. _()-]|(?<=[0-9])(?=[a-zA-Z])|(?<=[a-zA-Z])(?=[0-9]))", version
        )
        if not segments:
            return "unknown"

        # Process segments to identify numbers, letters, and separators
        pattern_parts = []
        for i, seg in enumerate(segments):
            if seg in [".", "-", "_", " ", "(", ")"]:
                if seg == " ":
                    pattern_parts.append("Space")
                elif seg == "(":
                    pattern_parts.append("OpenBrac")
                elif seg == ")":
                    pattern_parts.append("CloseBrac")
                else:
                    pattern_parts.append(
                        "Dot"
                        if seg == "."
                        else ("Dash" if seg == "-" else "Underscore")
                    )
            elif seg.isdigit():
                pattern_parts.append(f"{len(seg)}Num")
            elif seg.isalpha():
                pattern_parts.append(VersionPatternDetector.standardize_dev_stage(seg))

        # Combine all parts
        if not pattern_parts:
            return "unknown"

        return "".join(pattern_parts)

    @staticmethod
    def determine_version_pattern(version: str, url_ext: Optional[str] = None) -> str:
        try:
            if not version:
                logging.debug("Empty version string received")
                return "unknown"

            logging.debug(f"Analyzing version pattern: {version}")

            # Remove 'v' or 'r' prefix if present
            if version.startswith(("v", "r")):
                version = version[1:]

            # Get the descriptive pattern name
            pattern_name = VersionPatternDetector.get_version_pattern_name(version)

            if pattern_name != "unknown":
                logging.debug(
                    f"Detected version pattern: {pattern_name} for version: {version}"
                )
                return pattern_name

            logging.debug(f"No specific pattern matched for version: {version}")
            return "unknown"

        except Exception as e:
            logging.error(
                f"Error in determine_version_pattern for version '{version}': {str(e)}"
            )
            return "unknown"
