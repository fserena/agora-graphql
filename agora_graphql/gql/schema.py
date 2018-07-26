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


def transform_term(t):
    return t if t.isupper() else t.title()


def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]*)', r'\1_\2', name)
    return ''.join(map(lambda x: transform_term(x), s1.split('_')))


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

    super_range = filter(lambda x: not set.intersection(set(fountain.get_type(x)['super']), set(p_range)), p_range)
    if super_range:
        if len(super_range) > 1:
            range_type_name = 'Union' + '_'.join(map(lambda x: title(x), sorted(super_range)))
            return '[{}]'.format(range_type_name)
        else:
            concrete_range = filter(lambda x: not set.intersection(set(fountain.get_type(x)['sub']), set(p_range)),
                                    p_range)

            range_type_name = super_range[0]
            gql_type = all_type_names[range_type_name]
            if len(concrete_range) > 1:
                interface = 'I' + gql_type
                gql_type = interface

            return '[{}]'.format(gql_type)


def get_abstract_types(fountain):
    properties = fountain.properties
    for p in properties:
        p_dict = fountain.get_property(p)
        p_range = p_dict['range']
        if p_dict['type'] == 'object':
            super_range = filter(lambda x: not set.intersection(set(fountain.get_type(x)['super']), set(p_range)),
                                 p_range)
            if super_range:
                if len(super_range) > 1:
                    yield (p, {'type': 'Union', 'of': super_range})
                else:
                    concrete_range = filter(
                        lambda x: not set.intersection(set(fountain.get_type(x)['sub']), set(p_range)),
                        p_range)

                    if len(concrete_range) > 1:
                        yield (
                            p, {'type': 'Interface', 'for': concrete_range, 'base': super_range[0]})


def serialize_type(fountain, t, all_type_names, abstract_types):
    t_dict = fountain.get_type(t)
    t_props = t_dict['properties']

    abstract_refs = set.intersection(set(abstract_types.keys()), set(t_dict['refs']))
    implements = [abstract_types[p]['base'] for p in abstract_refs if
                  abstract_types[p]['type'] == 'Interface']

    attr_lines = ['\t{}: {}'.format(name(p), attr_type(fountain, p, all_type_names)) for p in t_props]
    attr_lines_str = '\n'.join(attr_lines)

    res = ''

    if t in implements:
        res += 'interface {} '.format('I' + all_type_names[t])
        res += '{\n%s\n}\n' % attr_lines_str

    res += 'type {} '.format(all_type_names[t])
    if implements:
        implements = ['I' + all_type_names[i] for i in implements]
        res += 'implements ' + ', '.join(implements) + ' '

    res += '{\n%s\n}' % attr_lines_str
    return res


def query_args(args):
    args = ', '.join(['{}: String'.format(arg.lstrip('$')) for arg in args])
    return '({})'.format(args) if args else ''


def serialize_queries(type_args):
    query_lines = ['\t{}{}: [{}]'.format(t, query_args(args), t) for t, args in type_args.items()]
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

    t_params = {}
    prefixes = gateway.agora.fountain.prefixes
    for t in types:
        t_uri = extend_uri(t, prefixes)
        t_ted = gateway.discover("""SELECT * WHERE { [] a <%s>}""" % t_uri, strict=True, lazy=False)
        if t_ted.ecosystem.roots:
            params = set()
            for root in t_ted.ecosystem.roots:
                if isinstance(root, TD):
                    root_vars = t_ted.ecosystem.root_vars(root)
                    td_vars = filter(lambda x: x != '$item' and x != '$parent', root_vars)
                    params.update(set(td_vars))

            t_params[all_type_names[t]] = params

    abstract_types = dict(get_abstract_types(fountain))
    for abstract in abstract_types.values():
        if abstract['type'] == 'Union':
            union_type_names = map(lambda x: title(x), sorted(abstract['of']))
            union_name = 'Union' + '_'.join(union_type_names)
            all_type_names[union_name] = union_type_names

    types_str = '\n'.join(
        filter(lambda x: x, [serialize_type(fountain, t, all_type_names, abstract_types) for t in types]))
    query_str = serialize_queries(t_params)
    schema_str = "schema {\n\tquery: Query\n}"

    unions_dict = {k: v for k, v in all_type_names.items() if k.startswith('Union')}
    unions = ['union {}= {}'.format(u, '|'.join(union_types)) for u, union_types in unions_dict.items()]
    unions_str = '\n'.join(unions)

    res = '\n'.join([types_str, unions_str, query_str, schema_str])

    return res
