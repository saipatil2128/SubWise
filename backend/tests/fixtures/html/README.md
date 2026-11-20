# Synthetic test fixtures — NOT real provider data

Every file here is a hand-written page that imitates the *structure* of a pricing page so the
extractor and validation rules can be tested offline. Plan names follow the provider vocabulary,
but every price (₹111, ₹222, ...) is made up and deliberately unrealistic. These files are loaded
only by tests through a mock HTTP transport; the application never reads them.
