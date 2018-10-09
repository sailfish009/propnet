# TODO: remove typing
from typing import *

import numpy as np
from monty.json import MSONable

from propnet import ureg
from propnet.core.symbols import Symbol
from propnet.core.provenance import ProvenanceElement
from propnet.symbols import DEFAULT_SYMBOLS
from uncertainties import unumpy


class Quantity(MSONable):
    """
    Class storing the value of a property.

    Constructed by the user to assign values to abstract Symbol types.
    Represents the fact that a given Quantity has a given value. They
    are added to the PropertyNetwork graph in the context of Material
    objects that store collections of Quantity objects representing
    that a given material has those properties.

    Attributes:
        symbol_type: (Symbol) the type of information that is represented
            by the associated value.
        value: (id) the value associated with this symbol.
        tags: (list<str>) tags associated with the material, e.g.
            perovskites or ferroelectrics
    """

    def __init__(self,
                 symbol_type: Union[str, Symbol],
                 value: Any,
                 tags: Optional[List[str]]=None,
                 provenance=None):
        """
        Parses inputs for constructing a Property object.

        Args:
            symbol_type (Symbol): pointer to an existing PropertyMetadata
                object or String giving the name of a SymbolType object,
                identifies the type of data stored in the property.
            value (id): value of the property.
            tags (list<str>): list of strings storing metadata from
                Quantity evaluation.
            provenance (ProvenanceElement): provenance associated with the
                object (e. g. inputs, model, see ProvenanceElement)
        """

        if isinstance(symbol_type, str):
            if symbol_type not in DEFAULT_SYMBOLS.keys():
                raise ValueError("Quantity type {} not recognized".format(symbol_type))
            symbol_type = DEFAULT_SYMBOLS[symbol_type]

        if type(value) == float or type(value) == int:
            value = ureg.Quantity(value, symbol_type.units)
        elif type(value) == ureg.Quantity:
            value = value.to(symbol_type.units)

        self._symbol_type = symbol_type
        self._value = value
        self._tags = tags
        self._provenance = provenance

    @property
    def value(self):
        """
        Returns:
            (id): value of the Quantity
        """
        return self._value

    @property
    def symbol(self):
        """
        Returns:
            (Symbol): Symbol of the Quantity
        """
        return self._symbol_type

    @property
    def tags(self):
        """
        Returns:
            (list<str>): tags of the Quantity
        """
        return self._tags

    @property
    def provenance(self):
        """
        Returns:
            (id): time of creation of the Quantity
        """
        return self._provenance

    def is_symbol_in_provenance(self, symbol):
        """
        Method for determining if symbol is in the provenance of quantity

        Args:
            symbol (Symbol or str): symbol type to test

        Returns:
            (bool) whether or not the symbol is in the quantity provenance

        """
        if self.provenance is None:
            return False
        else:
            return symbol in self.provenance.all_symbols

    def __hash__(self):
        return hash(self.symbol.name)

    def __eq__(self, other):
        if not isinstance(other, Quantity) \
                or self.symbol != other.symbol \
                or self.symbol.category != other.symbol.category:
            return False
        return self.value == other.value

    def __str__(self):
        return "<{}, {}, {}>".format(self.symbol.name, self.value, self.tags)

    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        return bool(self.value)

    # TODO: lazily implemented, fix to be a bit more robust
    def as_dict(self):
        if isinstance(self.value, ureg.Quantity):
            value = self.value.magnitude
            units = self.value.units
        else:
            value = self.value
            units = None
        return {"symbol_type": self._symbol_type.name,
                "value": value,
                "provenance": self._provenance,
                "units": units.format_babel() if units else None,
                "@module": "propnet.core.quantity",
                "@class": "Quantity"}


def weighted_mean(quantities):
    """
    Function to retrieve weighted mean

    Args:
        quantities ([Quantity]): list of quantities

    Returns:
        weighted mean
    """
    # can't run this twice yet ...
    # TODO: remove
    if hasattr(quantities[0].value, "std_dev"):
        return quantities

    input_symbol = quantities[0].symbol
    if input_symbol.category == 'object':
        # TODO: can't average 'objects', highlights a weakness in Quantity class
        # would be fixed by changing this class design ...
        return quantities

    if not all(input_symbol == q.symbol for q in quantities):
        raise ValueError("Can only calculate a weighted mean if all quantities "
                         "refer to the same symbol.")

    # TODO: an actual weighted mean; just a simple mean at present
    # TODO: support propagation of uncertainties (this will only work once at present)

    # TODO: test this with units, not magnitudes ... remember units may not be canonical units(?)
    if isinstance(quantities[0].value, list):
        # hack to get arrays working for now
        vals = [q.value for q in quantities]
    else:
        vals = [q.value.magnitude for q in quantities]

    new_magnitude = np.mean(vals, axis=0)
    std_dev = np.std(vals, axis=0)
    new_value = unumpy.uarray(new_magnitude, std_dev)

    new_tags = set()
    new_provenance = ProvenanceElement(model='aggregation', inputs=[])
    for quantity in quantities:
        if quantity.tags:
            for tag in quantity.tags:
                new_tags.add(tag)
        new_provenance.inputs.append(quantity)

    new_quantity = Quantity(symbol_type=input_symbol,
                            value=new_value,
                            tags=list(new_tags),
                            provenance=new_provenance)

    return new_quantity
