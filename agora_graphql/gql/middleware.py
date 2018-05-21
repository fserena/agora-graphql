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
import traceback

from agora.engine.plan.agp import extend_uri
from graphql import GraphQLNonNull, GraphQLList, GraphQLScalarType, GraphQLObjectType
from rdflib import URIRef, BNode
from agora_graphql.gql.data import data_graph
from agora_graphql.misc import match

__author__ = 'Fernando Serena'


def load_resource(info, uri):
    uri = URIRef(uri)
    if URIRef(uri) not in list(info.context['graph'].contexts()):
        try:
            g, headers = info.context['load_fn'](uri)
        except Exception:
            pass
        info.context['graph'].get_context(uri).__iadd__(g)
    return info.context['graph']


def objects(info, elm, predicate):
    if elm.startswith('_'):
        elm = BNode(elm)
    else:
        elm = URIRef(elm)
        load_resource(info, elm)

    return map(lambda o: o.toPython(), info.context['graph'].objects(elm, URIRef(predicate)))


class AgoraMiddleware(object):
    def __init__(self, gateway):
        self.gateway = gateway

    def loader(self, dg):
        def wrapper(uri):
            if uri:
                if self.gateway.data_cache is not None:
                    return self.gateway.data_cache.create(gid=uri, loader=dg.loader, format='text/turtle')
                else:
                    return dg.loader(uri, format='text/turtle')
            else:
                traceback.print_stack()

        return wrapper

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
                    dg = data_graph(info.context['query'], self.gateway, **args)
                    info.context['load_fn'] = self.loader(dg)
                    seeds = dg.roots
                else:
                    seeds = []
                    for parent_ty in match(info.parent_type.name, fountain.types):
                        try:
                            alias_prop = list(match(info.field_name, fountain.get_type(parent_ty)['properties'])).pop()
                            prop_uri = extend_uri(alias_prop, fountain.prefixes)
                            seeds = objects(info, root, prop_uri)

                            break
                        except IndexError:
                            pass

                if seeds or non_nullable:
                    return seeds

            elif isinstance(return_type, GraphQLScalarType):
                if root:
                    for parent_ty in match(info.parent_type.name, fountain.types):
                        try:
                            alias_prop = list(match(info.field_name, fountain.get_type(parent_ty)['properties'])).pop()
                            prop_uri = URIRef(extend_uri(alias_prop, fountain.prefixes))
                            try:
                                value = objects(info, root, prop_uri).pop()

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
                                uri = objects(info, root, prop_uri).pop()
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
