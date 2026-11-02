from dataclasses import dataclass, field


@dataclass
class VariableSymbol:
    name: str
    type_name: str
    mutable: bool


@dataclass
class FunctionSymbol:
    name: str
    parameter_types: list[str]
    result_type: str
    assigns_field: bool = False


@dataclass
class FieldSymbol:
    name: str
    index: int
    type_name: str
    mutable: bool


@dataclass
class StructSymbol:
    name: str
    fields: list[FieldSymbol] = field(default_factory=list)
    member_functions: dict[str, FunctionSymbol] = field(default_factory=dict)

    def get_field(self, name: str) -> FieldSymbol | None:
        for field_symbol in self.fields:
            if field_symbol.name == name:
                return field_symbol
        return None


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.variables: dict[str, VariableSymbol] = {}

    def declare(self, symbol: VariableSymbol) -> bool:
        if symbol.name in self.variables:
            return False

        self.variables[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> VariableSymbol | None:
        scope = self

        while scope is not None:
            symbol = scope.variables.get(name)

            if symbol is not None:
                return symbol

            scope = scope.parent

        return None


class SymbolTable:
    def __init__(self):
        self.global_scope = Scope()

        self.functions: dict[str, FunctionSymbol] = {}
        self.structures: dict[str, StructSymbol] = {}

    def get_function(self, name: str) -> FunctionSymbol | None:
        return self.functions.get(name)

    def get_structure(self, name: str) -> StructSymbol | None:
        return self.structures.get(name)
