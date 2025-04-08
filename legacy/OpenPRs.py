from pathlib import Path
from typing import List, Dict, Any
import polars as pl
from dataclasses import dataclass

@dataclass
class FieldConfig:
    names: List[str]
    lengths: List[int]

    def __post_init__(self):
        if len(self.names) != len(self.lengths):
            raise ValueError("Number of field names must match field lengths")
        if not all(length > 0 for length in self.lengths):
            raise ValueError("Field lengths must be positive")

class TextToDataFrame:
    def __init__(self, field_config: FieldConfig):
        self.config = field_config

    def process_line(self, line: str) -> Dict[str, str]:
        try:
            values = line.strip().split("\t")
            if len(values) != len(self.config.names):
                raise ValueError(f"Expected {len(self.config.names)} fields, got {len(values)}")
            return {
                name: value.ljust(length)
                for name, length, value in zip(self.config.names, self.config.lengths, values)
            }
        except Exception as e:
            raise ValueError(f"Error processing line: {line.strip()}\nError: {str(e)}")

    def convert(self, input_path: Path, output_path: Path) -> None:
        try:
            with open(input_path, "r", encoding="utf-8") as file:
                data = [self.process_line(line) for line in file if line.strip()]
            
            if not data:
                raise ValueError("No data found in input file")

            df = pl.DataFrame(data)
            df.write_csv(output_path)
            print(f"Successfully generated {output_path}")

        except Exception as e:
            raise RuntimeError(f"Failed to process {input_path}: {str(e)}")

def main():
    config = FieldConfig(
        names=["ID", "Title", "Branch", "Status", "CreatedAt"],
        lengths=[1000, 1500, 2000, 2000, 2000]
    )
    
    converter = TextToDataFrame(config)
    converter.convert(
        input_path=Path("data/OpenPRs.txt"),
        output_path=Path("data/OpenPRs.csv")
    )

if __name__ == "__main__":
    main()