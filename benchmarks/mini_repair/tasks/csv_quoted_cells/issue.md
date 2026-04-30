Issue: parsing a CSV line with a quoted comma splits the cell in the middle.

Observed behavior:
- names such as `"Ng, David"` are parsed as two fields

Expected behavior:
- quoted commas stay inside the field
