# Inventory Architecture

## Module Shape

The inventory module follows the existing clean architecture conventions:

- `domain`: inventory enums and domain vocabulary
- `application`: services/use cases and business rules
- `infrastructure`: SQLAlchemy models and repositories
- `presentation`: FastAPI schemas and thin routers

Routers do not contain SQL or posting logic. Services validate relationships, permissions, scope, status transitions, and stock rules.

## Immutable Ledger

`inventory_movements` is append-only and is the source of truth for warehouse history. Posting creates ledger movements. Cancelling a posted document creates reversal movements with opposite quantity deltas and keeps the original movements unchanged.

## Stock Balances

`inventory_stock_balances` stores current stock for efficient queries by:

- organization
- item
- warehouse
- optional location
- optional lot
- optional serial

Balances are updated in the same transaction as movements. They are rebuildable from the movement ledger.

## Posting Transaction

Document posting is atomic through the Unit of Work:

1. Validate document status and header.
2. Validate line items, lots, serial readiness, locations, and warehouse access.
3. Create movement rows.
4. Update stock balances.
5. Mark the document as posted.
6. Write audit and outbox records.

If any step fails, the service rolls back the transaction. A failed post must not leave partial movements or balances.

## Reversal

Cancelling a posted document requires a reason. The system creates movement rows with opposite quantity deltas and `movement_kind = reversal`. Original movements remain unchanged.

## Site And Warehouse Scope

Permissions answer what a user may do. Scope answers where the user may do it.

The scope model is:

- `user_site_access`
- `user_warehouse_access`

Superusers are unrestricted. Other users see only warehouses assigned directly or through assigned sites. API responses for warehouse stock and documents are filtered on the backend.

## Deferred Scope

Sprint 5 intentionally does not implement purchasing, suppliers, BOM, manufacturing orders, CNC jobs, production consumption, assembly, accounting valuation, invoices, or financial accounting.
