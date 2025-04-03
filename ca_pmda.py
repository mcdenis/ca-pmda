###########################################################################
## Export of Script Module: ca_pmda
## Language: Python
## Category: External Service
## Description: Client library for the CA Performance Management Data Aggregator data-driven API.
###########################################################################
class _deps:
    import abc
    import collections.abc
    import copy
    import dataclasses
    import itertools
    import sys
    import requests
    import typing
    import xml.etree.ElementTree


# Backport some features we need. To delete eventually.
#if _deps.sys.version_info < (3, 10):
#    import builtins as _builtins
#
#    # AttributeError.__init__ take a name and obj param..
#    def _AttributeError__init__(self,
#                                *args: object,
#                                name: _deps.typing.Optional[str]=None,
#                                obj: object=...):
#        self.name = name
#        self.obj = obj
#        super(AttributeError).__init__(*args)
#    AttributeError.__init__ = _AttributeError__init__
#
#    # isinstance accept a union type.
#    def isinstance(obj: object, class_info: _deps.typing.Any) -> bool:
#        if _deps.typing.get_origin(class_info) is _deps.typing.Union:
#            normalized_class_info = _deps.typing.get_args(class_info)
#        else:
#            normalized_class_info = class_info
#        return _builtins.isinstance(obj, normalized_class_info)


def _attribute_error(*args: object,
                    name: _deps.typing.Optional[str] = None,
                    obj: object = None) -> AttributeError:
    """
    Create an `AttributeError`.
    """

    if name:
        args2 = list(args)
        if len(args2) < 1:
           args2.append(name)
        else:
            args2[0] = f"{args2[0]} Attribute name: {name}."
    else:
        args2 = args
    
    if _deps.sys.version_info < (3, 10):
         return AttributeError(*args2)
    return AttributeError(*args2, name=name, obj=obj)


Scalar = _deps.typing.Union[str, int, float, bool]


_scalar_types = str, int, float, bool
"""
Tuple of types that are instance of `Scalar`.

## Intended Usage

```
if isinstance(obj, _scalar_types):
    ...
```

---

TODO Delete this when we no longer need to support below Python 3.10, cause
since 3.10, we can just pass the Scalar type directly to `isinstance`:
`isinstance(obj, Scalar)`.
"""


AttributeValue = _deps.typing.Union[Scalar, "DynamicModel"]


def _scalar_to_str(value: Scalar) -> str:
    # Important to test bool first cause bools are also ints.
    if isinstance(value, bool):
        str_val = str(value).lower()
    elif isinstance(value, (str, int, float)): # pyright: ignore[reportUnnecessaryIsInstance]
        str_val = str(value)
    else:
        raise TypeError("Value must be of type str, int, float or bool.")
    return str_val


class _Headers:
    """
    Defines common HTTP headers for internal usage. Text must be case folded.
    """

    accept = ("accept", "application/xml")
    content_type = ("content-type", "application/xml")


class PmdaInfrastructureError(Exception):
    """
    PM DA provided information that this module cannot understand. The problem
    may be a bug or misconfiguration in PM DA, or it may be that some
    conventions that this module takes for granted about the PM DA data-driven
    API are not respected. If said conventions are no longer applicable, then
    this module needs to be updated.
    """


@_deps.dataclasses.dataclass(frozen=True)
class IsA:
    name: str
    """
    Type name.
    """

    rootURL: str
    """
    URI of the service dedicated to the type.
    """


@_deps.typing.no_type_check
class DynamicModel:
    """
    ## Get

    Get value as a string or a DynamicModel if value is complex.

    ## Set

    Set the value from a scalar (str, int, float and bool) or a DynamicModel. If
    the value is a scalar, it is implicitly converted to a str and getting it
    afterward will always get a str.

    ## Delete


    ## Implementation Note
    
    Changes are always stored to the underlying XML document. Accessing an
    attribute always reads the underlying document.
    
    TODO Implement special attribute (e.g. version, IsAlso) access with Python
    Descriptors (one Descriptor per property.)
    """
    
    def __init__(self, doc: _deps.xml.etree.ElementTree.Element) -> None:
        """
        For module-internal use. When you need to create a new object to pass to
        a Create or an Update operation, use the module's `dynamic_model`
        function instead, which abstracts away the document.
        """

        self.__dict__["__document__"] = doc
        self.__document__: _deps.xml.etree.ElementTree.Element
    

    def __dir__(self) -> _deps.collections.abc.Iterable[str]:
        return _deps.itertools.chain(# Statically defined attributes
                                     super().__dir__(),
                                     # Attributes in document
                                     tuple(e.tag for e in self.__document__),
                                     # Other attributes we added through
                                     # __getattr__ and __setattr__
                                     ("version",))


    def __getattr__(self, name: str) -> _deps.typing.Any:
        # Special case: version is an attribute on the root.
        if name == "version":
            return self.__document__.get("version")
        # 
        if name == "IsAlso":
            return tuple(IsA(e.attrib["name"], e.attrib["rootURL"]) for e in self.__document__.findall("./IsAlso/IsA"))

        # Get attribute element 
        element = self.__document__.find(name)
        if element is None:
            raise _attribute_error("Attribute not found.", name=name, obj=self)
        if "version" in element.attrib:
            # Attribute element is a resource.
            return DynamicModel(element)
        # Attribute element contains a scalar.
        return element.text
        
    
    def __setattr__(self, name: str, value: AttributeValue) -> None:
        # Special case: version is an attribute on the root.
        if name == "version":
            if not isinstance(value, str):
                raise TypeError("Version must be a string.")
            self.__document__.set("version", value)
            return
        # 
        if name == "IsAlso":
            raise _attribute_error("This special attribute cannot be set.",
                                   name=name,
                                   obj=self)
        
        # Get element with attribute
        old_element = self.__document__.find(name)
        if old_element is not None:
            self.__document__.remove(old_element)
        
        if isinstance(value, _scalar_types):
            # Get value as string.
            val_str = _scalar_to_str(value) 
            # Create element.
            new_element = _deps.xml.etree.ElementTree.SubElement(self.__document__, name)
            # Put the two together.
            new_element.text = val_str
        elif isinstance(value, DynamicModel): # pyright: ignore[reportUnnecessaryIsInstance]
            if name != value.__document__.tag:
                raise TypeError(f"Value of complex type {value.__document__.tag} not appropriate for property {name}.")
            self.__document__.append(value.__document__)
        else:
            raise TypeError("Can only set attribute to a scalar or a DynamicModel.")
    

    def __delattr__(self, name: str) -> None:
        # TODO handle special attributes like version and IsAlso.
        element = self.__document__.find(name)
        if element is None:
            raise _attribute_error("Attribute not found.", name=name, obj=self)
        self.__document__.remove(element)


    # Two instances are equal if the underlying document is the same instance.
    # This is necessary to ensure that consecutive access to the same complex
    # property gets a value that appears to be identical, even if the
    # DynamicModel instance is different (because they are not cached.) I.e.:
    # ```
    # model.complex_prop == model.complex_prop
    # ```

    def __eq__(self, value: object) -> bool:
        if isinstance(value, DynamicModel):
            return value.__document__ == self.__document__
        return False
    

    def __hash__(self) -> int:
        return hash(self.__document__)
    

    def __str__(self) -> str:
        type_name = self.__document__.tag
        if hasattr(self, "ID"):
            return f"<{type_name} with ID {self.ID}>"
        return f"<{type_name}>"


def dynamic_model(_type: str, version: str, **attributes: AttributeValue) -> DynamicModel:
    """
    Create a `DynamicModel` from Python dict. Useful for Create or Update
    operation where user must pass a (potentially partial) resource from scratch.
    """

    element = _deps.xml.etree.ElementTree.Element(_type)
    model = DynamicModel(element)
    model.version = version
    for k, v in attributes.items():
        setattr(model, k, v)
    return model


def dump_dynamic_model(dynamic_model: DynamicModel) -> str:
    """
    Convert the specified `DynamicModel` to a human-readable string.

    This function should be used for debugging only. Currently, it outputs the
    data in pretty XML. This might change in the future.
    """
    
    doc = _deps.copy.deepcopy(dynamic_model.__document__)
    _deps.xml.etree.ElementTree.indent(doc)
    return _deps.xml.etree.ElementTree.tostring(doc, "unicode")


ComparisonOp = _deps.typing.Literal["LESS",
                                    "LESS_OR_EQUAL",
                                    "GREATER",
                                    "GREATER_OR_EQUAL",
                                    "EQUAL", "CONTAINS",
                                    "STARTS_WITH",
                                    "ENDS_WITH",
                                    "REGEX",
                                    "IS_NULL"]
"""
From: http://<da-host>:8581/typecatalog/basefilterselect.xsd
"""


class Expression(_deps.abc.ABC):
    @_deps.abc.abstractmethod
    def __toxml__(self) -> _deps.xml.etree.ElementTree.Element:
        raise NotImplementedError


@_deps.dataclasses.dataclass(frozen=True)
class AttributeComparison(Expression):
    prop_name: str
    """
    Fully qualified property name. Eg. `ManageableDevice.SystemName`.
    """
    
    operator: ComparisonOp
    prop_value: Scalar
    ignoreCase: bool = False

    def __toxml__(self) ->_deps.xml.etree.ElementTree.Element:
        e = _deps.xml.etree.ElementTree.Element(self.prop_name,
                                                type=self.operator)
        if self.ignoreCase:
            e.set("ignoreCase", "true")
        e.text = _scalar_to_str(self.prop_value)
        return e
    

class _Operator(Expression):

    operands: _deps.collections.abc.Sequence[Expression]


    def __init__(self,
                 *operands: Expression) -> None:
        self.operands = operands


    def __toxml__(self):
        e = _deps.xml.etree.ElementTree.Element(type(self).__name__)
        for o in self.operands:
            e.append(o.__toxml__())
        return e
    

class Not(_Operator):

    # Override __init__ to limit argument count to one.
    def __init__(self, operand: Expression) -> None:
        super().__init__(operand)


class And(_Operator):
    pass


class Or(_Operator):
    pass
    

# region Filter Modeling

def _filter_select(filter: Expression) -> str:
    """
    Create a filter for the `filtered_get_list` operation.

    TODO support the `Select element.
    """
    
    root = _deps.xml.etree.ElementTree.Element(
        "FilterSelect",
        {
            "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation": "filter.xsd"
        }
    )
    filter_e = _deps.xml.etree.ElementTree.SubElement(root, "Filter")
    filter_e.append(filter.__toxml__())
    return _deps.xml.etree.ElementTree.tostring(root, encoding="unicode")

# end region Filter Modeling


class DynamicClient:
    """
    General client application for any PM DA data-driven Web service.

    Every operation method has a `service_uri` parameter that indicates the
    service that the client should query. Examples of service URI:
    
    * `profiles`
    * `profiles/snmpv3`
    * `devices`
    * `devices/manageable`.
    """

    
    def __init__(self,
                 host_name: str,
                 protocol: _deps.typing.Literal["http", "https"],
                 session: _deps.requests.Session) -> None:
            self.host_name = host_name
            self.protocol = protocol
            self.session = session


    def _create_url(self, service_uri: str, op_uri: str) -> str:
         return f"{self.protocol}://{self.host_name}:8581/rest/{service_uri}/{op_uri}"
    

    @staticmethod
    def _parse_xml_response_data(response: _deps.requests.Response) -> _deps.xml.etree.ElementTree.Element:
        response_content_type = response.headers[_Headers.content_type[0]].casefold()
        expected_content_type = _Headers.content_type[1]
        if response_content_type != expected_content_type \
                and not response_content_type.startswith(expected_content_type + ";"):
            raise PmdaInfrastructureError(f"CA PM DA client requested XML, but got {response_content_type} instead.")
        return _deps.xml.etree.ElementTree.fromstring(response.content)


    # region Web Service Operations
    
    def filtered_get_list(self,
                          service_uri: str,
                          filter: Expression) -> _deps.collections.abc.Iterator[DynamicModel]:
        """
        
        """
        
        url = self._create_url(service_uri, "filtered")
        headers = dict[str, str]((_Headers.accept, _Headers.content_type))
        data = _filter_select(filter)

        response = self.session.post(url, data=data, headers=headers)
        response.raise_for_status() # TODO handle some errors like ca_spectrum?

        document = self._parse_xml_response_data(response)
        return (DynamicModel(child) for child in document)
    

    def update(self,
               service_uri: str,
               resource_id: str,
               updated: DynamicModel):
        url = self._create_url(service_uri, "") + "/" + resource_id
        headers = dict[str, str]((_Headers.content_type,))
        data = _deps.xml.etree.ElementTree.tostring(updated.__document__)

        response = self.session.put(url, data=data, headers=headers)
        response.raise_for_status() # TODO handle some error like ca_spectrum?

        # TODO if returns data, then add _Headers.accept and return return
        # mapped result.
    
    # end region
