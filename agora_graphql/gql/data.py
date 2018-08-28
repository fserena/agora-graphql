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

from agora import Agora, Planner
from agora.collector.execution import parse_rdf
from agora.collector.http import http_get, RDF_MIMES
from rdflib import Graph, ConjunctiveGraph

from agora_graphql.gql.sparql import sparql_from_graphql

__author__ = 'Fernando Serena'


def roots_gen(gen):
    for c, s, p, o in gen:
        yield s.toPython()


class DataGraph(object):
    def __init__(self, gql_query, gateway, **kwargs):
        pass

    @property
    def roots(self):
        gen = self.__data_gw.fragment(self.__sparql_query,
                                      scholar=self.__scholar,
                                      follow_cycles=self.__follow_cycles,
                                      **self.__kg_params)['generator']
        return roots_gen(gen)

    @property
    def loader(self):
        def wrapper(uri, format):
            result = self.__data_gw.loader(uri, format)
            if result is None and self.__data_gw.loader != http_get:
                for fmt in sorted(RDF_MIMES.keys(), key=lambda x: x != format):
                    result = http_get(uri, format=fmt)
                    if result is not None and not isinstance(result, bool):
                        content, headers = result
                        if not isinstance(content, Graph):
                            g = ConjunctiveGraph()
                            parse_rdf(g, content, fmt, headers)
                            result = g, headers
                        break
            return result

        return wrapper

    def __new__(cls, *args, **kwargs):
        dg = super(DataGraph, cls).__new__(cls)
        dg.__gql_query = args[0]
        dg.__gateway = args[1]
        dg.__agora = Agora(auto=False)
        dg.__agora.planner = Planner(dg.__gateway.agora.fountain)
        dg.__sparql_query = sparql_from_graphql(dg.__agora.fountain, dg.__gql_query, root_mode=True)
        data_gw_cache = kwargs.get('data_gw_cache', None)

        if data_gw_cache is None or dg.__gql_query not in data_gw_cache:
            data_gw = dg.__gateway.data(dg.__sparql_query, serverless=True, static_fountain=True,
                                        server_name=kwargs.get('server_name', None), port=kwargs.get('port', None),
                                        base=kwargs.get('base', 'store'))
        else:
            data_gw = data_gw_cache[dg.__gql_query]

        if 'server_name' in kwargs:
            del kwargs['server_name']
        if 'port' in kwargs:
            del kwargs['port']

        dg.__data_gw = data_gw

        if data_gw_cache is not None:
            data_gw_cache[dg.__gql_query] = data_gw

        if 'data_gw_cache' in kwargs:
            del kwargs['data_gw_cache']
        if 'scholar' in kwargs:
            dg.__scholar = bool(kwargs['scholar'])
            del kwargs['scholar']
        else:
            dg.__scholar = False

        if 'follow_cycles' in kwargs:
            dg.__follow_cycles = kwargs['follow_cycles']
            del kwargs['follow_cycles']
        else:
            dg.__follow_cycles = True

        dg.__kg_params = kwargs

        return dg


def data_graph(gql_query, gateway, **kwargs):
    return DataGraph(gql_query, gateway, **kwargs)
