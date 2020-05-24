import re
import traceback


def write_readme(template_file, dest_file, key_lookup=lambda key: None, skip_line_if_value_missing=True):
    try:
        print("INFO: updating {}".format(dest_file))
        with open(template_file, "r") as f:
            template_lines = f.readlines()

        result_lines = []
        for line in template_lines:
            line = _process_line(line, key_lookup, skip_line_if_value_missing)
            if line is not None:
                result_lines.append(line)

        with open(dest_file, "w") as dest_f:
            dest_f.write("".join(result_lines))

    except Exception as e:
        traceback.print_exc()
        print("ERROR: failed to generate readme")


def _process_line(line, key_lookup, skip_line_if_value_missing):
    all_keys = re.findall("{[^}]*}", line)  # finds anything like "{this}"
    for key in all_keys:
        key_text = key[1:len(key) - 1]  # remove brackets
        new_value = key_lookup(key_text)
        if new_value is not None:
            # XXX if you decide to replace a key with another key, you'll have issues here
            line = line.replace(key, str(new_value), 1)
        else:
            if skip_line_if_value_missing:
                return None
    return line
