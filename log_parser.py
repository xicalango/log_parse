#!/usr/bin/env python3

import yaml
import json
from argparse import ArgumentParser
import re
from datetime import datetime, timedelta

class LogParser:
    def __init__(self, config, args):
        self.config = config
        self.line_types = self.config['line_types']
        self.regexes = self.__extractRegexes()
        self.args = args
        self.__checkArgs()

    def __checkArgs(self):
        for arg in self.config['args']:
            if arg['name'] not in self.args:
                if arg['default'] is None:
                    raise Exception("required arg: " + arg)
                else:
                    self.args[arg['name']] = arg['default']

    def __extractRegexes(self):
        regexes = []

        for (id, line_type) in self.line_types.items():
            compiled = re.compile(line_type['regex'])
            regexes.append( (compiled, id) )

        return regexes
    
    def parse(self, handle, flat = False):
        matches = []
        line_counter = 0
        
        if flat:
            line_name = "__line__"
            type_name = "__type__"
        else:
            line_name = "line"
            type_name = "type"


        for line in handle:
            line_counter += 1

            for regex, line_type_id in self.regexes:
                match = regex.match(line)
                if match is None:
                    continue
                

                fields = match.groupdict()

                if 'fields' in self.line_types[line_type_id]:
                    for (field_id, field_type) in self.line_types[line_type_id]['fields'].items():
                        if fields[field_id] == None:
                            continue

                        fields[field_id] = self.parse_field(fields[field_id], field_type)

                match_data = {
                        line_name: line_counter,
                        type_name: line_type_id,
                }

                if flat:
                    match_data.update(fields)
                else:
                    match_data["fields"] = fields

                matches.append(match_data)

        return matches
        
    def parse_field(self, value, field_type):
        if "::" in field_type:
            actual_type, sub_type = field_type.split("::")
            return self.parse_special(value, self.config['types'][actual_type], sub_type = sub_type)
        elif field_type in self.config['types']:
            return self.parse_special(value, self.config['types'][field_type])
        elif field_type == 'number':
            return float(value)
        else:
            return value

    # todo: fix
    def parse_special(self, value, type_config, sub_type = None):
        if type_config['type'] == "timedelta":
            for fmt in type_config['formats']:
                if sub_type is not None and fmt['name'] != sub_type:
                    continue
                try:
                    if fmt['parser'] == 'float':
                        return self.normalize(timedelta(seconds = float(value)), fmt)
                    elif fmt['parser'] == 'datetime':
                        return self.normalize(datetime.strptime(value, fmt['format']) - datetime(1900, 1, 1), fmt)
                except ValueError as e:
                    #print("Can't parse with {}, because {}".format(fmt['parser'], e))
                    pass

            raise Exception("no parser found for: '{}' {} {}".format(value, type_config, sub_type))

        elif type_config['type'] == "number":
            for fmt in type_config['formats']: 
                if sub_type is not None and fmt['name'] != sub_type:
                    continue
                try:
                    return self.normalize(float(value), fmt)
                except ValueError:
                    pass

    def normalize(self, value, fmt):
        if 'normalize' not in fmt:
            return value
        
        eval_lambda = eval("lambda value, args: " + fmt['normalize'])
        return eval_lambda(value, self.args)

class TimeDeltaEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        return json.JSONEncoder.default(self, obj)


def main():

    parser = ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--config", '-c', default = "config.yml")
    parser.add_argument("--flatten", '-f', action = 'store_true')
    parser.add_argument("kvs", nargs='*', type=lambda x: x.split('=', 1))

    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = yaml.load(f)

    log_parser = LogParser(config, dict(args.kvs))

    matches = []

    with open(args.file, "r") as f:
        matches = log_parser.parse(f, flat = args.flatten)

    print(json.dumps(matches, indent=2, cls=TimeDeltaEncoder))

if __name__ == '__main__':
    main()
