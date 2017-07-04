#!/usr/bin/env python3

import yaml
import json
from argparse import ArgumentParser
import re

def parse_field(value, field_type, config):
    if field_type in config['types']:
        return value # todo
    elif field_type == 'number':
        return float(value)
    else:
        return value

def main():

    parser = ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--config", default = "config.yml")

    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = yaml.load(f)

    regexes = []

    for (id, line_type) in config['line_types'].items():
        compiled = re.compile(line_type['regex'])
        regexes.append( (compiled, id) )

    matches = []

    with open(args.file, "r") as f:
        line_counter = 0
        for line in f:
            line_counter += 1

            for regex, line_type_id in regexes:
                match = regex.match(line)
                if match is None:
                    continue
                

                fields = match.groupdict()

                for (field_id, field_type) in config['line_types'][line_type_id]['fields'].items():
                    if fields[field_id] == None:
                        continue

                    fields[field_id] = parse_field(fields[field_id], field_type, config)

                match_data = {
                        "line": line_counter,
                        "type": line_type_id,
                        "fields": fields,
                }
                matches.append(match_data)

    print(json.dumps(matches, indent=2))

if __name__ == '__main__':
    main()
