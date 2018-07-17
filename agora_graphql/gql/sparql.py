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
from agora.engine.plan import AGP
from graphql import parse
from graphql.language.ast import Field
from shortuuid import uuid

from agora_graphql.misc import match

__author__ = 'Fernando Serena'


def identify_property(parent_type, p, fountain):
    parent_props = fountain.get_type(parent_type)['properties']
    try:
        return match(p, parent_props).pop()
    except IndexError:
        pass


def identify_parent_type(selection, fountain):
    cand_parent_types = list(match(selection, fountain.types))
    field_names = [f.name.value for f in selection.selection_set.selections if isinstance(f, Field)]

    for t in cand_parent_types:
        if all([identify_property(t, p, fountain) for p in field_names]):
            return t


def process_selection(fountain, selection, parent_var=None, parent_type=None, parent_prop=None, root_mode=True):
    var = None
    ty = None
    prop = None

    try:
        if not parent_type:
            ty = identify_parent_type(selection, fountain)
            if ty:
                if not parent_var:
                    var = '?v' + str(uuid())
                else:
                    var = parent_var
                tp = '{} {} {}'.format(var, 'a', ty)
                yield tp

            if not root_mode and not parent_prop:
                prop = list(match(selection, fountain.properties)).pop()
                if prop:
                    if not parent_var:
                        parent_var = '?v' + str(uuid())
                    var = '?v' + str(uuid())
                    tp = '{} {} {}'.format(parent_var, prop, var)
                    yield tp

        if parent_type or parent_prop:
            if parent_type:
                prop = list(match(selection, fountain.get_type(parent_type)['properties'])).pop()
            else:
                parent_range = fountain.get_property(parent_prop)['range']
                cand_props = reduce(lambda x, y: x.union(set(fountain.get_type(y)['properties'])), parent_range, set())
                prop = list(match(selection, cand_props)).pop()
            if prop:
                var = '?v' + str(uuid())
                tp = '{} {} {}'.format(parent_var, prop, var)
                yield tp

        if not root_mode and selection.selection_set:
            for s in selection.selection_set.selections:
                for tp in process_selection(fountain, s, parent_var=var, parent_type=ty, parent_prop=prop):
                    yield tp
    except IndexError:
        pass


def sparql_from_graphql(fountain, gql_query, root_mode=False):
    ast = parse(gql_query)
    tps = []
    for d in ast.definitions:
        if d.operation == 'query':
            var = '?v' + str(uuid())
            for s in d.selection_set.selections:
                tps.extend(list(process_selection(fountain, s, parent_var=var, root_mode=root_mode)))

    agp = AGP(set(tps), prefixes=fountain.prefixes)
    query = 'SELECT DISTINCT * WHERE {}'.format(agp)
    return query
