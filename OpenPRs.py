import polars as pl

def convert_txt_to_dataframe(file_path, field_names, field_lengths):

    with open(file_path, "r") as file:
        lines = file.readlines()  # Read all lines from the text file

    data = []
    for line in lines:
        words = [word.ljust(length) for word, length in zip(line.split("\t"), field_lengths)]
        row_data = dict(zip(field_names, words))
        data.append(row_data)

    return pl.DataFrame(data)

# Example usage
file_path = "OpenPRs.txt"
field_names = ["ID", "Title", "Branch", "Status", "CreatedAt"]
field_lengths = [1000, 1500, 2000, 2000, 2000]

df = convert_txt_to_dataframe(file_path, field_names, field_lengths)
df.write_csv("OpenPRs.csv")    
print("Generated OpenPRs.csv successfully")
