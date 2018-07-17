"""
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  Copyright (C) 2018 Fernando Serena.
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

            http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
"""
import logging
import re

from agora import Wrapper
from agora.engine.plan.agp import extend_uri
from agora_wot.blocks.td import TD

__author__ = 'Fernando Serena'

log = logging.getLogger('agora.gql.schema')


def name(prefixed_name):
    return prefixed_name.split(':')[1]


def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return ''.join(map(lambda x: x.title(), s1.split('_')))


def title(prefixed_name):
    return convert(name(prefixed_name))


def attr_type(fountain, p, all_type_names):
    p_dict = fountain.get_property(p)
    p_range = p_dict['range']
    if p_dict['type'] == 'data':
        value_type = p_range[0]
        if value_type.startswith('xsd'):
            value_type = title(value_type)
        else:
            value_type = 'String'
        return value_type

    filtered_range = filter(lambda x: fountain.get_type(x)['sub'] not in p_range, p_range)
    if filtered_range:
        return '[{}]'.format(all_type_names[filtered_range[0]])


def serialize_type(fountain, t, all_type_names):
    t_dict = fountain.get_type(t)
    t_props = t_dict['properties']

    res = 'type {} '.format(all_type_names[t])
    attr_lines = ['\t{}: {}'.format(name(p), attr_type(fountain, p, all_type_names)) for p in t_props]
    attr_lines_str = '\n'.join(attr_lines)
    res += '{\n%s\n}' % attr_lines_str
    return res


def query_args(args):
    args = ', '.join(['{}: String'.format(arg.lstrip('$')) for arg in args])
    return '({})'.format(args) if args else ''


def serialize_queries(types, args):
    type_names = filter(lambda x: ':' not in x, types)
    query_lines = ['\t{}{}: [{}]'.format(t, query_args(args[types[t]]), t) for t in type_names]
    return 'type Query {\n%s\n}' % '\n'.join(query_lines)


def create_gql_schema(gateway):
    log.info('Building GraphQL schema from Agora...')
    fountain = Wrapper(gateway.agora.fountain)

    types = filter(lambda x: fountain.get_type(x)['properties'], sorted(fountain.types))
    all_type_names = {}
    for t in types:
        t_title = title(t)
        if t_title in all_type_names:
            t_title = ''.join(map(lambda x: x.title(), t.split(':')))

        all_type_names[t] = t_title
        all_type_names[t_title] = t

    types_str = '\n'.join(filter(lambda x: x, [serialize_type(fountain, t, all_type_names) for t in types]))
    t_params = {}
    prefixes = gateway.agora.fountain.prefixes
    for t in types:
        t_uri = extend_uri(t, prefixes)
        t_ted = gateway.discover("""SELECT * WHERE { [] a <%s>}""" % t_uri, strict=True, lazy=False)
        params = set()
        for root in t_ted.ecosystem.roots:
            if isinstance(root, TD):
                td_vars = filter(lambda x: x != '$item' and x != '$parent', root.vars)
                params.update(set(td_vars))

        t_params[t] = params

    query_str = serialize_queries(all_type_names, t_params)
    schema_str = "schema {\n\tquery: Query\n}"

    res = '\n'.join([types_str, query_str, schema_str])

    return res
