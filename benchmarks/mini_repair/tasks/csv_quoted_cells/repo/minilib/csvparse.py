def parse_csv_line(line):
    return [part.strip() for part in line.split(",")]
