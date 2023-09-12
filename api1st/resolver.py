import yaml
import os
import logging
from urllib.parse import urlsplit, urljoin
from jsonpointer import resolve_pointer, JsonPointerException

logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

class Specification(object):
    def __init__(self, uri, data) -> None:
        self.uri:str = uri
        self.root = data
        self.resolved: bool = False
        self.dependencies: dict = {}
        self.is_json_schema: bool = False
        self.is_open_api: bool = False
        self.common_defs: dict = None
        # determine the schema type: json schema, openapi, etc
        try:
            # try as json schema
            self.common_defs = resolve_pointer(self.root, '/definitions')
            self.is_json_schema = True
        except JsonPointerException:
            try:
                # try as openapi
                self.common_defs = resolve_pointer(self.root, '/components/schemas')
                self.is_open_api = True
            except JsonPointerException:
                pass


    def to_common_definition(self, name: str) -> str:
        if self.is_json_schema:
            return f'#/definitions/{name}'
        elif self.is_open_api:
            return f'#/components/schemas/{name}'
        else:
            return name
    
    '''
    Find the type by relative name in the common definitions of this resource.
    This can be a pointer or simple type name. A pointer is converted to the expected
    path of this resource.
    '''
    def as_local_type(self, type: str) -> str | None:
        segments = type.split('/')
        ptr = segments[len(segments) - 1]
        if self.is_json_schema:
            return '/definitions/' + ptr
        elif self.is_open_api:
            return '/components/schemas/' + ptr
        else:
            return None

    def find(self, pointer) -> dict | None:
        try:
            return resolve_pointer(self.root, pointer)
        except:
            return None

    def add_shared_type(self, obj, pointer: str) -> str:
        segments = pointer.split('/')
        name = segments[len(segments) - 1]
        path = self.to_common_definition(name)
        #node = resolve_pointer(self.root, path)
        #node[name] = obj
        self.common_defs[name] = obj
        logger.info(f'Added shared type definition: {path}')
        return path

class SpecificationFile(Specification):
    def __init__(self, specification: str) -> None:
        fn = specification
        if not os.path.isabs(fn):
            fn = os.path.abspath(specification)
        with open(fn) as f:
            nodes =  yaml.safe_load(f)
        super().__init__('file://' + fn, nodes)

class SpecificationURL(Specification):
    # TODO
    pass

#
# URL resources have no dependencies (convention)
# local resources may have chained dependencies
#
class Resolver(object):
    def __init__(self, specifications: list=[]) -> None:
        #self.specification = specification
        self.specification_cache: dict = {}
        self.specifications: list = specifications

    #
    # recursively process a sub-tree
    #
    def visit(self, specification: Specification, node):
        if type(node) is dict:
            ref = False
            keys = list(node.keys())
            for key in keys:
                if key == '$ref':
                    self.resolve_reference(specification, node, node[key]);
                else:
                    self.visit(specification, node[key])

        elif type(node) is list:
            for item in node:
                self.visit(specification, item)

    def resolve_reference(self, specification: Specification, container: dict, reference: str):
        uri = urlsplit(reference)
        if uri.path == None or uri.path == '':
            # reference to an internal type
            logger.info(f'Internal reference: {reference}')
            node = resolve_pointer(specification.root, uri.fragment)
            if node == None:
                logger.error(f'Missing reference: {reference}')
            else:
                logger.info("Resolved reference: " + reference)
            return
        dependency: Specification = None
        if uri.scheme == 'http' or uri.scheme == 'https':
            # reference to type in external HTTP resource
            logger.info(f'External reference: {reference}')
            if str(uri) in self.specification_cache:
                logger.info("Specification has been previously processed: " + uri)
                return
            dependency = self.load(specification, str(uri))
            if not dependency.processed:
                logger.info(f'***** Processing specification: {dependency.uri} *****')
                self.visit(dependency, dependency.root)
                dependency.processed = True
                logger.info(f'***** Processed specification: {dependency.uri} *****')


        elif uri.scheme == 'file':
            # reference to type in external filesystem resource
            logger.info(f'Local reference: {reference}')
            if str(uri) in self.specification_cache:
                logger.info("Specification has been previously processed: " + uri)
                return
            dependency = self.load(specification, str(uri))
            if not dependency.processed:
                logger.info(f'***** Processing specification: {dependency.uri} *****')
                self.visit(dependency, dependency.root)
                dependency.processed = True
                logger.info(f'***** Processed specification: {dependency.uri} *****')

        elif uri.scheme == None or uri.scheme == '':
            #resource = urljoin(specification.uri, uri.path)
            resource = uri.path
            logger.info(f'Relative reference: {uri.fragment} [{resource}]')
            if resource in self.specification_cache:
                logger.info("Specification has been previously processed: " + uri)
                return
            dependency = self.load(specification, resource)
            if not dependency.resolved:
                logger.info(f'***** Processing specification: {dependency.uri} *****')
                self.visit(dependency, dependency.root)
                dependency.resolved = True
                logger.info(f'***** Processed specification: {dependency.uri} *****')

        else:
            raise Exception(f'No support for reference: {reference}')

        # inline the reference from the dependency
        node = dependency.find(uri.fragment)
        if node == None:
            logger.error(f'Missing reference: {reference}')
        else:
            del container['$ref']
            for key, value in node.items():
                container[key] = value
            self.check_for_shared(specification, dependency, node);
            logger.info(f'Resolved reference: {reference}')

    def load(self, specification: Specification, path: str) -> Specification:
        parts = urlsplit(specification.uri)
        if parts.scheme == 'file':
            f = urljoin(parts.path, path)
            spec: Specification = self.specification_cache.get(f)
            if spec == None:
                spec = SpecificationFile(f)
                self.specification_cache[f] = spec
            return spec
        elif parts.scheme == 'http' or parts.scheme == 'https':
            url = urljoin(specification.uri, path)
            spec: Specification = self.specification_cache.get(url)
            if spec == None:
                spec = SpecificationURL(url)
                self.specification_cache[url] = spec
            return spec
 
    def check_for_shared(self, specification: Specification, dependency: Specification, node: dict):
        if type(node) is list:
            for item in node:
                logger.info(f'Array element: {item}')
                self.check_for_shared(specification, dependency, item)
            return
        elif type(node) is dict:
            keys = node.keys()
            for key in keys:
                value = node[key]
                if '$ref' == key:
                    pointer = value[1:] if value.startswith('#') else value
                    shared = dependency.find(pointer)
                    if shared == None:
                        logger.error(f'Missing reference {pointer}  in{dependency.uri}')
                    else:
                        # add as a local type
                        ptr = specification.add_shared_type(shared, pointer)
                        # rewrite the reference to local type
                        node['$ref'] = ptr
                        logger.info(f'Promote reference from dependency to dependent:  {pointer}')
                        # recursively check deeper
                        self.check_for_shared(specification, dependency, shared)
                else:
                    self.check_for_shared(specification, dependency, value)


    #
    # load a specification and walk the nodes in the parse tree
    #
    def resolve(self) -> list:
        results: list = []
        for specification in self.specifications:
            logger.info("***** Processing resource: " + specification.uri + " *****");
            self.visit(specification, specification.root)
            results.append(specification)
            logger.info("***** Processed resource: " + specification.uri + " *****");
        return results

