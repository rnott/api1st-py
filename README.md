# schema-resoolver-py
This is a Work In Progress and not yet suitable for production use.

An API First approach describes a software development strategy that prioritizes APIs at the start of the process. In this approach, APIs are treated as building blocks and are developed before other code. The goal is to design products around APIs so that they are easily accessible and reusable.

The API-first approach focuses on consistency, reusability, and quality to improve adoption, developer ease, and compatibility and allows businesses to deliver applications that can operate in any channel and scale as more channels are added.

A typical use case is to define an API using a standardized specification language such as OpenAPI, then use tooling to authomatically generate code corresponding to the service model types and interface defined by the API specification. Code can be generated in one or more programming languages and/or frameworkds to support multiple clients in addition to the service implemenation. 

## The Problem
Specification languages are often built on top of JSON and JSON Schema and make use of [JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901) to support modularity and re-use. Unfortunatley, a number of code generators and associated tooling do not support importing an external reference. This limits the use of JSON Pointer to only internal references (e.g. within in the same resource). In this context, it is impossible to share a definition between multiple APIs, for example a common definition of an address. This defeats the notition of re-use at a specification level.


## A Solution
One approach to solve this problem involves inlining all references, both internal and external, with the end result being there are no JSON Pointer ferencences present in the output. This works in terms of definition modularization but has implications downstream in the toolchain: the code generator will create a unique types for what is logically the same definition because any notition of sharing was removed by inlining those definitions.

A better approach is to only resolve external references, leaving internal references as is. This can be done in such a way that external references are either imported inline or as a shared definition, depending on their use in the referenced resource. After transformation, the specification is self-contained but allows sharing of definitions internally.

## Definition Languages

### Supported
* [OpenAPI](https://www.openapis.org/)
* [JSON Schema](https://json-schema.org/)

### Under Consideration
* [Avro](https://avro.apache.org/)
* [AsyncAPI](https://www.asyncapi.com/)
* [GraphQL](https://graphql.org/)

## Practices

## Related Tools
* [OpenAPU Code Generator](https://github.com/OpenAPITools/openapi-generator) - OpenAPI Generator allows generation of API client libraries (SDK generation), server stubs, documentation and configuration automatically given an OpenAPI Spec (v2, v3) for a wide range of programming languages and frameworks
* [JSON Schema](https://json-schema.org/implementations.html#code-generation) - official listing of programming language specific code generators


