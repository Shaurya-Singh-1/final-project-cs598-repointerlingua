# Local Result Summary

| Agent | Solved | Total | Solve Rate | Patches Applied |
| :--- | ---: | ---: | ---: | ---: |
| react | 2 | 5 | 0.400 | 2 |
| bugstate | 5 | 5 | 1.000 | 5 |

## Per-task outcomes

| Task | Agent | Solved | Patch Applied |
| :--- | :--- | :---: | :---: |
| csv_quoted_cells | react | no | no |
| env_case_override | react | no | no |
| nested_config_merge | react | no | no |
| parse_iso_z_suffix | react | yes | yes |
| request_scheme_validation | react | yes | yes |
| csv_quoted_cells | bugstate | yes | yes |
| env_case_override | bugstate | yes | yes |
| nested_config_merge | bugstate | yes | yes |
| parse_iso_z_suffix | bugstate | yes | yes |
| request_scheme_validation | bugstate | yes | yes |

This local benchmark is a system-validation benchmark: it checks that the workspace-copy, evaluation, patching, and explicit-state machinery all work before larger GPU-backed runs.