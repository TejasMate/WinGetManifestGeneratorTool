import subprocess
import os
import concurrent.futures
import polars as pl
import logging
from pathlib import Path
from typing import Set, List, Tuple, Optional
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class ProcessingConfig:
    local_repo: str = "winget-pkgs"
    output_file: str = "data/filenames.csv"
    file_pattern: str = "*.installer.yaml"

class YAMLProcessor:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.manifests_dir = Path(config.local_repo) / "manifests"
        self.unique_rows: Set[Tuple[str, ...]] = set()
        self.max_dots = 0

    def run_command(self, command: str, cwd: Optional[str] = None) -> int:
        logging.info(f"Executing command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                check=True
            )
            return 0
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed: {e.stderr}")
            return e.returncode
        except Exception as e:
            logging.error(f"Error executing command: {e}")
            return 1

    def get_yaml_files(self) -> List[Path]:
        return list(self.manifests_dir.rglob(self.config.file_pattern))

    def process_yaml_file(self, file_path: Path) -> None:
        name = file_path.stem.replace('.installer', '')
        parts = name.split('.')
        
        if len(set(parts)) == 1:
            return
            
        # Ensure we have enough elements, pad with empty strings if needed
        padded_parts = parts[:self.max_dots + 1] + [''] * (self.max_dots + 1 - len(parts))
        row = tuple(padded_parts[:self.max_dots + 1])
        self.unique_rows.add(row)

    def calculate_max_dots(self, files: List[Path]) -> None:
        self.max_dots = max(
            file_path.stem.replace('.installer', '').count('.')
            for file_path in files
        )

    def create_dataframe(self) -> pl.DataFrame:
        if not self.unique_rows:
            return pl.DataFrame()

        column_names = [f"column_{i}" for i in range(self.max_dots + 1)]
        data_dict = {name: [] for name in column_names}
        
        for row in self.unique_rows:
            for i, value in enumerate(row):
                data_dict[column_names[i]].append(value)
                
        return pl.DataFrame(data_dict)

    def write_csv(self) -> None:
        output_path = Path(self.config.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df = self.create_dataframe()
        if not df.is_empty():
            df.write_csv(output_path)
            logging.info(f"Data written to {output_path}")
        else:
            logging.warning("No data to write")

    def process_files(self) -> None:
        yaml_files = self.get_yaml_files()
        if not yaml_files:
            logging.warning("No YAML files found")
            return

        self.calculate_max_dots(yaml_files)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.process_yaml_file, file_path)
                for file_path in yaml_files
            ]
            concurrent.futures.wait(futures)
            
            for future in futures:
                if future.exception():
                    logging.error(f"Error processing file: {future.exception()}")

def main():
    config = ProcessingConfig()
    processor = YAMLProcessor(config)
    processor.process_files()
    processor.write_csv()
    logging.info("Processing completed successfully")

if __name__ == '__main__':
    main()