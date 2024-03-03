import os
from dotenv import load_dotenv

def modify_file(input_file, output_file, string_to_add):
  with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
    for line in f_in:
      # Remove trailing newline character if present
      line = line.rstrip('\n')
      # Add the string and a newline character
      modified_line = line + string_to_add + '\n'
      f_out.write(modified_line)

# pat = os.environ["TOKEN"]
# if not pat:
#   raise RuntimeError("TOKEN env var is not set")

load_dotenv()
pat = os.getenv("TOKEN")

# Example usage
input_file = "my_commands.sh"
output_file = "my_commandsss.sh"
string_to_add = f" {pat}"

modify_file(input_file, output_file, string_to_add)

print(f"Successfully modified {input_file} and saved the result to {output_file}")
