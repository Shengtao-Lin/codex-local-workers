"""Cross-file quote fixture with an independently checked rounding boundary."""

CONTRACT = (
    "quote(cart, discount_percent, destination) returns integer subtotal_cents, "
    "discount_cents, shipping_cents, tax_cents and total_cents, without changing cart. "
    "Resolve catalog prices and aggregate quantities; reject unknown SKUs and nonpositive "
    "quantities. Discount applies to merchandise, shipping policy uses the unrounded "
    "discounted merchandise, tax applies to discounted merchandise plus shipping. "
    "Preserve Decimal intermediate values; round each reported component half-up. "
    "total_cents is rounded once from the full unrounded payable amount, NOT a sum "
    "of the separately rounded reported components. Empty cart has zero shipping. "
    "The catalog, discount, shipping, tax and money helpers define supported values."
)

REFERENCE = """from shop.catalog import lookup
from shop.discounts import discount_amount
from shop.lines import normalize
from shop.money import cents
from shop.shipping import shipping_amount
from shop.tax import tax_amount
from shop.totals import payable


def quote(cart, discount_percent=0, destination="home"):
    items = normalize(cart)
    subtotal = sum((lookup(sku) * quantity for sku, quantity in items), start=lookup("ZERO"))
    discount = discount_amount(subtotal, discount_percent)
    shipping = shipping_amount(subtotal - discount, destination, bool(items))
    tax = tax_amount(subtotal - discount + shipping, destination)
    return {
        "subtotal_cents": cents(subtotal),
        "discount_cents": cents(discount),
        "shipping_cents": cents(shipping),
        "tax_cents": cents(tax),
        "total_cents": cents(payable(subtotal, discount, shipping, tax)),
    }
"""
HIDDEN = REFERENCE.replace(
    "cents(payable(subtotal, discount, shipping, tax))",
    "payable(cents(subtotal), cents(discount), cents(shipping), cents(tax))",
)
FILES = {
    "src/shop/__init__.py": "",
    "src/shop/quote.py": REFERENCE,
    "src/shop/catalog.py": """from decimal import Decimal

PRICES = {"ZERO": Decimal("0"), "PIN": Decimal("0.05"), "BOOK": Decimal("10.00")}


def lookup(sku):
    if sku not in PRICES:
        raise ValueError("unknown SKU")
    return PRICES[sku]
""",
    "src/shop/lines.py": """def normalize(cart):
    result = []
    for row in cart:
        quantity = row["quantity"]
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("invalid quantity")
        result.append((row["sku"], quantity))
    return result
""",
    "src/shop/discounts.py": """from decimal import Decimal


def discount_amount(subtotal, percent):
    value = Decimal(str(percent))
    if not value.is_finite() or not 0 <= value <= 100:
        raise ValueError("invalid discount")
    return subtotal * value / 100
""",
    "src/shop/shipping.py": """from decimal import Decimal


def shipping_amount(discounted_subtotal, destination, has_items):
    if destination not in {"home", "away"}:
        raise ValueError("invalid destination")
    if not has_items or destination == "home" or discounted_subtotal >= 20:
        return Decimal("0")
    return Decimal("2.50")
""",
    "src/shop/tax.py": """from decimal import Decimal


def tax_amount(taxable, destination):
    rate = {"home": Decimal("0.075"), "away": Decimal("0.10")}[destination]
    return taxable * rate
""",
    "src/shop/totals.py": """def payable(subtotal, discount, shipping, tax):
    return subtotal - discount + shipping + tax
""",
    "src/shop/money.py": """from decimal import Decimal, ROUND_HALF_UP


def cents(amount):
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
""",
}
PUBLIC_TESTS = """import pytest
from shop.quote import quote


def test_standard():
    cart = [{"sku": "BOOK", "quantity": 2}]
    assert quote(cart) == {"subtotal_cents": 2000, "discount_cents": 0, "shipping_cents": 0, "tax_cents": 150, "total_cents": 2150}
    assert cart == [{"sku": "BOOK", "quantity": 2}]


def test_empty_and_shipping():
    assert quote([])["total_cents"] == 0
    assert quote([{"sku": "BOOK", "quantity": 1}], destination="away")["total_cents"] == 1375


@pytest.mark.parametrize("cart", [[{"sku": "UNKNOWN", "quantity": 1}], [{"sku": "BOOK", "quantity": 0}]])
def test_invalid(cart):
    with pytest.raises(ValueError):
        quote(cart)
"""
BOUNDARY_TEST = """from shop.quote import quote


def test_round_total_once():
    # 0.05 - 0.005 + 0 + 0.003375 = 0.048375, rounded to 5 cents.
    result = quote([{"sku": "PIN", "quantity": 1}], discount_percent=10)
    assert result == {"subtotal_cents": 5, "discount_cents": 1, "shipping_cents": 0, "tax_cents": 0, "total_cents": 5}
"""
