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
import traceback
from threading import Lock

from agora.engine.plan.agp import extend_uri
from graphql import GraphQLNonNull, GraphQLList, GraphQLScalarType, GraphQLObjectType, GraphQLInterfaceType, \
    GraphQLUnionType
from graphql.language.ast import InlineFragment
from rdflib import URIRef, BNode, Graph, RDF

from agora_graphql.gql.data import data_graph
from agora_graphql.misc import match

__author__ = 'Fernando Serena'

_lock = Lock()

log = logging.getLogger('agora.gql.middleware')


def load_resource(info, uri):
    uri = URIRef(uri)
    try:
        g, headers = info.context['load_fn'](uri)
    except Exception:
        traceback.print_exc()
        g = Graph()

    return g


def uri_lock(elm, info):
    with _lock:
        if elm not in info.context['locks']:
            info.context['locks'][elm] = Lock()
        return info.context['locks'][elm]


def objects(cache, info, elm, predicate):
    lock = uri_lock(elm, info)
    elm_key = elm.toPython() if not isinstance(elm, basestring) else elm
    pred_key = predicate.toPython()
    with lock:
        if elm_key not in cache:
            cache[elm_key] = {'_g': load_resource(info, elm)}
        if pred_key not in cache[elm_key]:
            if elm.startswith('_'):
                elm = BNode(elm)
            else:
                elm = URIRef(elm)

            res = map(lambda o: o.toPython(), cache[elm_key]['_g'].objects(elm, URIRef(predicate)))
            cache[elm_key][pred_key] = res[:]

        elif cache is not None:
            res = cache[elm_key][pred_key][:]

        return res


class AgoraMiddleware(object):
    def __init__(self, gateway, data_gw_cache=None, **settings):
        self.gateway = gateway
        self.data_gw_cache = data_gw_cache
        self.settings = settings.copy()

    def loader(self, dg):
        def wrapper(uri):
            if uri:
                if self.gateway.data_cache is not None:
                    g = self.gateway.data_cache.create(gid=uri, loader=dg.loader, format='text/turtle')
                else:
                    g = dg.loader(uri, format='text/turtle')

                return g
            else:
                traceback.print_stack()

        return wrapper

    def __check_matching_inline(self, info, types_n3):
        inline_fragments = filter(lambda s: isinstance(s, InlineFragment),
                                  reduce(lambda x, y: x + y.selection_set.selections, info.field_asts,
                                         []))
        inline_types = map(lambda i: i.type_condition.name.value, inline_fragments)
        if not inline_types:
            raise ValueError()
        for it in inline_types:
            if match(it, types_n3):
                return info.schema.get_type(it)

    def resolve_type(self, item, info):
        lock = uri_lock(item, info)
        with lock:
            if item not in self.data_gw_cache:
                self.data_gw_cache[item] = {'_g': load_resource(info, item)}
            if 'type' not in self.data_gw_cache[item]:
                g = self.data_gw_cache[item]['_g']
                types = g.objects(URIRef(item), RDF.type)
                types_n3 = set(map(lambda t: t.n3(g.namespace_manager), types))

                res_type = None
                if isinstance(info.return_type.of_type, GraphQLInterfaceType):
                    interface_type = info.return_type.of_type.name
                    corresponding_type = interface_type.lstrip('I')
                    matching_types = set(match(corresponding_type, types_n3))
                    if matching_types:
                        try:
                            res_type = self.__check_matching_inline(info, types_n3)
                        except ValueError:
                            res_type = info.schema.get_type(corresponding_type)

                else:
                    union_types_dict = {x.name: x for x in info.return_type.of_type.types}
                    matching_types = filter(lambda (_, m): m,
                                            {t: match(t, types_n3) for t in union_types_dict.keys()}.items())

                    if matching_types:
                        try:
                            res_type = self.__check_matching_inline(info, types_n3)
                        except ValueError:
                            pass

                self.data_gw_cache[item]['type'] = res_type

        return self.data_gw_cache[item]['type']

    def __filter_abstract_seed(self, seed, info):
        type = self.resolve_type(seed, info)
        return type is not None

    def resolve(self, next, root, info, **args):
        if info.context['introspection']:
            return next(root, info, **args)

        fountain = info.context['fountain']

        try:

            non_nullable = isinstance(info.return_type, GraphQLNonNull)
            return_type = info.return_type.of_type if non_nullable else info.return_type

            if info.field_name == '_uri':
                return root

            if isinstance(return_type, GraphQLList):
                if not root:
                    data_graph_kwargs = args.copy()
                    data_graph_kwargs.update(self.settings)
                    dg = data_graph(info.context['query'], self.gateway, data_gw_cache=self.data_gw_cache,
                                    **data_graph_kwargs)
                    info.context['load_fn'] = self.loader(dg)
                    info.context['locks'] = {}
                    seeds = dg.roots
                else:
                    seeds = []
                    for parent_ty in match(info.parent_type.name, fountain.types):
                        try:
                            alias_prop = list(match(info.field_name, fountain.get_type(parent_ty)['properties'])).pop()
                            prop_uri = extend_uri(alias_prop, fountain.prefixes)
                            seeds = objects(self.data_gw_cache, info, root, prop_uri)
                            break
                        except IndexError:
                            pass

                if isinstance(info.return_type.of_type, GraphQLInterfaceType) or isinstance(info.return_type.of_type,
                                                                                            GraphQLUnionType):
                    seeds = filter(lambda x: self.__filter_abstract_seed(x, info), seeds)

                if seeds or non_nullable:
                    return seeds

            elif isinstance(return_type, GraphQLScalarType):
                if root:
                    for parent_ty in match(info.parent_type.name, fountain.types):
                        try:
                            alias_prop = list(match(info.field_name, fountain.get_type(parent_ty)['properties'])).pop()
                            prop_uri = URIRef(extend_uri(alias_prop, fountain.prefixes))
                            try:
                                value = objects(self.data_gw_cache, info, root, prop_uri).pop()

                                return value
                            except IndexError as e:
                                if non_nullable:
                                    raise Exception(e.message)
                        except IndexError:
                            pass

            elif isinstance(return_type, GraphQLObjectType):
                if root:
                    for parent_ty in match(info.parent_type.name, fountain.types):
                        try:
                            alias_prop = list(match(info.field_name, fountain.get_type(parent_ty)['properties'])).pop()
                            prop_uri = URIRef(extend_uri(alias_prop, fountain.prefixes))
                            try:
                                uri = objects(self.data_gw_cache, info, root, prop_uri).pop()
                                if uri:
                                    return uri
                            except IndexError as e:
                                if non_nullable:
                                    raise Exception(e.message)
                        except IndexError:
                            pass

        except Exception as e:
            traceback.print_exc()
            raise e
