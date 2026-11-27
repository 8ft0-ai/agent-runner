def parse_source(payload: bytes) -> dict[str, int]:
    """Decode the inventory format, one unique SKU and quantity per row."""
    items = {}
    for row in payload.decode("utf-8").splitlines():
        columns = row.split("|")
        if len(columns) != 2:
            raise ValueError("expected SKU|quantity")
        sku, quantity = columns
        if not sku or not sku.isascii() or not sku.isalnum() or sku in items:
            raise ValueError("invalid or duplicate SKU")
        if not quantity.isascii() or not quantity.isdecimal():
            raise ValueError("invalid quantity")
        items[sku] = int(quantity)
    return items
